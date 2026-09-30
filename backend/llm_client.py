"""
backend/llm_client.py
Cloud LLM Decision Engine for SEVA AI (Vernacular Digital Assistance Kiosk).

Enforces:
  1. Zero-markdown, strictly typed JSON contract:
     { "thought": str, "action": str, "selector": str, "value": str, "feedback": str }
     Allowed actions: ["navigate", "click", "fill", "scroll", "wait", "finish"]
  2. Dual-Model Cloud Routing:
     - Primary: Gemini 2.5 Flash via direct HTTPS REST endpoint (or google-genai).
     - Secondary fallback: OpenRouter Qwen 2.5 7B (qwen/qwen-2.5-7b-instruct:free) using credentials in vdak-vm/.env.
  3. Safe Fallback Engine:
     - 8-second timeout guard.
     - Rate-limit (429), authentication (401/403), and network error handling without crashing daemon.
     - Deterministic local e-governance fallback database for Maharashtra citizen workflows
       (Income Certificate, Niradhar Pension, 7/12 Satbara, Ration card, Caste, Farmer/MahaDBT)
       in Marathi (mr), Hindi (hi), and English (en).
  4. Context Pruning:
     - Rolling scratchpad retaining citizen goal and the last 3 step deltas.
"""

import json
import logging
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

from dotenv import load_dotenv

try:
    from backend.models import LLMDecision
except ImportError:
    try:
        from models import LLMDecision
    except ImportError:
        LLMDecision = None

try:
    from backend.browser_sandbox import PORTAL_TEMPLATES
except ImportError:
    try:
        from browser_sandbox import PORTAL_TEMPLATES
    except ImportError:
        PORTAL_TEMPLATES = {}


# Ensure Windows stdout/stderr supports Devanagari Unicode (Marathi/Hindi)
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment configurations across possible project locations
_base_dir = Path(__file__).resolve().parent.parent
load_dotenv(_base_dir / ".env")
load_dotenv(_base_dir / "vdak-vm" / ".env")
load_dotenv(_base_dir / "vdak-host" / ".env")

logger = logging.getLogger("seva.llm")

# Valid actions in contract
VALID_ACTIONS: Set[str] = {"navigate", "click", "fill", "scroll", "wait", "finish"}

# Default configuration from env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_REST_BASE = os.getenv(
    "GEMINI_REST_BASE",
    "https://generativelanguage.googleapis.com/v1beta/models"
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct:free")
_raw_or_base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_BASE_URL = (
    _raw_or_base if _raw_or_base.endswith("/chat/completions")
    else f"{_raw_or_base.rstrip('/')}/chat/completions"
)

API_TIMEOUT_SEC = 8.0

SYSTEM_PROMPT = """You are SEVA AI, an autonomous vernacular kiosk agent guiding rural citizens through Indian public service portals.
Your task is to observe the current page elements and choose the SINGLE NEXT immediate primitive action.

You MUST respond ONLY with a raw JSON object conforming to this exact schema (no markdown, no backticks):
{
  "thought": "Reasoning for the selected action in English",
  "action": "navigate" | "click" | "fill" | "scroll" | "wait" | "finish",
  "selector": "CSS selector or text anchor for element, or empty if not applicable",
  "value": "Input text or destination URL, or empty if not applicable",
  "feedback": "Spoken feedback for the citizen in their chosen language"
}

Rule 1: Never guess multi-step sequences. Return only the single immediate next action.
Rule 2: If the portal asks for OTP, password, or biometric, return action="wait" with feedback instructing citizen.
Rule 3: If target task is accomplished or confirmation receipt is reached, return action="finish".
Rule 4: Allowed actions are ONLY: navigate, click, fill, scroll, wait, finish.
"""

# Local Deterministic Knowledge Base for Maharashtra E-Governance Workflows (PRD FR-3.3)
GOVERNANCE_SERVICES: Dict[str, Dict[str, Any]] = {
    "income": {
        "keywords": ["उत्पन्न", "दाखला", "आय", "income", "certificate", "tahsildar", "तहसीलदार"],
        "name_mr": "उत्पन्नाचा दाखला",
        "name_hi": "आय प्रमाण पत्र",
        "name_en": "Income Certificate",
        "steps": [
            {
                "thought": "Citizen requested Income Certificate. Navigating to e-district Revenue portal.",
                "action": "navigate",
                "selector": "",
                "value": "http://127.0.0.1:8000/portal/income",
                "feedback": {
                    "mr": "उत्पन्नाच्या दाखल्याचे पोर्टल उघडत आहे, कृपया प्रतीक्षा करा...",
                    "hi": "आय प्रमाण पत्र पोर्टल खोला जा रहा है, कृपया प्रतीक्षा करें...",
                    "en": "Opening Income Certificate portal, please wait..."
                }
            },
            {
                "thought": "Entering citizen full name into Applicant Name field.",
                "action": "fill",
                "selector": "#applicant_name",
                "value": "रविंद्र तुकाराम पाटील",
                "feedback": {
                    "mr": "अर्जदाराचे पूर्ण नाव प्रविष्ट केले आहे.",
                    "hi": "आवेदक का पूरा नाम दर्ज कर दिया गया है.",
                    "en": "Applicant full name has been filled."
                }
            },
            {
                "thought": "Entering annual income value into Annual Income field.",
                "action": "fill",
                "selector": "#annual_income",
                "value": "60000",
                "feedback": {
                    "mr": "वार्षिक उत्पन्न साठ हजार रुपये नोंदवले आहे.",
                    "hi": "वार्षिक आय साठ हजार रुपये दर्ज की गई है.",
                    "en": "Annual income of sixty thousand rupees entered."
                }
            },
            {
                "thought": "Selecting Taluka Tahsil office from jurisdiction dropdown.",
                "action": "click",
                "selector": "#jurisdiction_select",
                "value": "",
                "feedback": {
                    "mr": "तालुका महसूल कार्यालय निवडत आहे.",
                    "hi": "तहसील राजस्व कार्यालय का चयन किया जा रहा है.",
                    "en": "Selecting Tehsil revenue office."
                }
            },
            {
                "thought": "Clicking verify and submit button to generate certificate token.",
                "action": "click",
                "selector": "#submit_btn",
                "value": "",
                "feedback": {
                    "mr": "उत्पन्नाच्या दाखल्याचा अर्ज सादर करत आहे.",
                    "hi": "आय प्रमाण पत्र आवेदन जमा किया जा रहा है.",
                    "en": "Submitting Income Certificate application."
                }
            },
            {
                "thought": "Application successfully submitted with tracking ID. Completing task.",
                "action": "finish",
                "selector": "",
                "value": "",
                "feedback": {
                    "mr": "तुमचा उत्पन्नाचा दाखला अर्ज यशस्वीपणे सादर झाला आहे. पावती तयार केली आहे.",
                    "hi": "आपका आय प्रमाण पत्र आवेदन सफलतापूर्वक जमा हो गया है. रसीद तैयार है.",
                    "en": "Your Income Certificate application has been submitted successfully. Receipt generated."
                }
            }
        ]
    },
    "pension": {
        "keywords": ["निराधार", "पेन्शन", "संजय गांधी", "वृद्धापकाळ", "वृद्धावस्था", "पेंशन", "niradhar", "pension", "destitute"],
        "name_mr": "संजय गांधी निराधार योजना",
        "name_hi": "संजय गांधी निराधार पेंशन",
        "name_en": "Niradhar Pension Scheme",
        "steps": [
            {
                "thought": "Citizen requested Niradhar Pension. Navigating to Social Justice portal.",
                "action": "navigate",
                "selector": "",
                "value": "http://127.0.0.1:8000/portal/niradhar",
                "feedback": {
                    "mr": "संजय गांधी निराधार योजनेचे पोर्टल उघडत आहे...",
                    "hi": "संजय गांधी निराधार योजना पोर्टल खोला जा रहा है...",
                    "en": "Navigating to Niradhar Pension Scheme portal..."
                }
            },
            {
                "thought": "Filling beneficiary identity details.",
                "action": "fill",
                "selector": "#beneficiary_name",
                "value": "शांताबाई रामचंद्र पाटील",
                "feedback": {
                    "mr": "लाभार्थ्याचे नाव नोंदवले आहे.",
                    "hi": "लाभार्थी का नाम दर्ज किया गया है.",
                    "en": "Beneficiary name recorded."
                }
            },
            {
                "thought": "Selecting pension category: Niradhar Destitute Senior.",
                "action": "click",
                "selector": "#category_btn",
                "value": "",
                "feedback": {
                    "mr": "निराधार योजना वर्गवारी निवडत आहे.",
                    "hi": "निराधार योजना श्रेणी का चयन किया जा रहा है.",
                    "en": "Selecting Niradhar Pension category."
                }
            },
            {
                "thought": "Submitting pension verification request.",
                "action": "click",
                "selector": "#submit_pension",
                "value": "",
                "feedback": {
                    "mr": "पेन्शन अर्ज पडताळणीसाठी सादर केला आहे.",
                    "hi": "पेंशन आवेदन सत्यापन के लिए जमा किया गया है.",
                    "en": "Submitting pension application for verification."
                }
            },
            {
                "thought": "Pension request acknowledged by portal.",
                "action": "finish",
                "selector": "",
                "value": "",
                "feedback": {
                    "mr": "निराधार पेन्शन नोंदणी पूर्ण झाली आहे.",
                    "hi": "निराधार पेंशन पंजीकरण पूरा हो गया है.",
                    "en": "Niradhar pension registration complete."
                }
            }
        ]
    },
    "satbara": {
        "keywords": ["सातबारा", "7/12", "७/१२", "satbara", "जमीन", "खसरा", "खतौनी", "फेरफार", "bhulekh", "भूलेख", "land", "नक्शा"],
        "name_mr": "७/१२ सातबारा उतारा",
        "name_hi": "भूलेख ७/१२ खसरा खतौनी",
        "name_en": "7/12 Satbara Land Record",
        "steps": [
            {
                "thought": "Citizen requested 7/12 land records. Navigating to Mahabhulekh portal.",
                "action": "navigate",
                "selector": "",
                "value": "http://127.0.0.1:8000/portal/satbara",
                "feedback": {
                    "mr": "महाभूलेख सातबारा पोर्टल उघडत आहे...",
                    "hi": "महाभूलेख ७/१२ पोर्टल खोला जा रहा है...",
                    "en": "Navigating to Mahabhulekh Land Records portal..."
                }
            },
            {
                "thought": "Entering district and taluka jurisdiction.",
                "action": "fill",
                "selector": "#district_input",
                "value": "पुणे",
                "feedback": {
                    "mr": "जिल्हा आणि तालुका निवडला आहे.",
                    "hi": "जिला और तहसील का चयन किया गया है.",
                    "en": "District and Tehsil selected."
                }
            },
            {
                "thought": "Entering survey / Gat number for 7/12 extract.",
                "action": "fill",
                "selector": "#survey_no",
                "value": "42/1",
                "feedback": {
                    "mr": "गट क्रमांक ४२/१ प्रविष्ट केला आहे.",
                    "hi": "खसरा संख्या ४२/१ दर्ज की गई है.",
                    "en": "Survey number 42/1 entered."
                }
            },
            {
                "thought": "Fetching digitally signed 7/12 extract.",
                "action": "click",
                "selector": "#fetch_extract",
                "value": "",
                "feedback": {
                    "mr": "डिजिटल स्वाक्षरीचा सातबारा उतारा डाऊनलोड करत आहे.",
                    "hi": "डिजिटल हस्ताक्षरित ७/१२ खसरा डाउनलोड किया जा रहा है.",
                    "en": "Fetching digitally signed 7/12 extract."
                }
            },
            {
                "thought": "7/12 record retrieved successfully.",
                "action": "finish",
                "selector": "",
                "value": "",
                "feedback": {
                    "mr": "तुमचा सातबारा उतारा स्क्रीनवर उपलब्ध झाला आहे.",
                    "hi": "आपका ७/१२ खसरा स्क्रीन पर उपलब्ध है.",
                    "en": "Your 7/12 record is now displayed on screen."
                }
            }
        ]
    },
    "ration": {
        "keywords": ["रेशन", "कार्ड", "राशन", "राशन कार्ड", "रेशन कार्ड", "ration", "subsidy", "aepds", "अन्नधान्य"],
        "name_mr": "सार्वजनिक वितरण रेशन कार्ड",
        "name_hi": "खाद्य आपूर्ति राशन कार्ड",
        "name_en": "Public Distribution Ration Card",
        "steps": [
            {
                "thought": "Citizen requested Ration Card services. Navigating to AePDS portal.",
                "action": "navigate",
                "selector": "",
                "value": "http://127.0.0.1:8000/portal/ration",
                "feedback": {
                    "mr": "सार्वजनिक वितरण प्रणाली रेशन कार्ड पोर्टल उघडत आहे...",
                    "hi": "खाद्य एवं नागरिक आपूर्ति राशन कार्ड पोर्टल खोला जा रहा है...",
                    "en": "Opening Public Distribution System Ration Card portal..."
                }
            },
            {
                "thought": "Entering citizen 12-digit ration card number.",
                "action": "fill",
                "selector": "#ration_card_no",
                "value": "272001458923",
                "feedback": {
                    "mr": "रेशन कार्ड क्रमांक प्रविष्ट केला आहे.",
                    "hi": "राशन कार्ड संख्या दर्ज की गई है.",
                    "en": "Ration card number entered."
                }
            },
            {
                "thought": "Selecting member modification or subsidy service.",
                "action": "click",
                "selector": "#service_select",
                "value": "",
                "feedback": {
                    "mr": "रेशन कार्ड सेवा पर्याय निवडत आहे.",
                    "hi": "राशन कार्ड सेवा विकल्प का चयन किया जा रहा है.",
                    "en": "Selecting ration card service option."
                }
            },
            {
                "thought": "Entering new family member name.",
                "action": "fill",
                "selector": "#member_name",
                "value": "अनिल सुरेश गायकवाड",
                "feedback": {
                    "mr": "नवीन कुटुंबातील सदस्याचे नाव भरले आहे.",
                    "hi": "नए परिवार सदस्य का नाम भरा गया है.",
                    "en": "New family member name filled."
                }
            },
            {
                "thought": "Submitting ration card service application.",
                "action": "click",
                "selector": "#submit_ration",
                "value": "",
                "feedback": {
                    "mr": "रेशन कार्ड अर्ज सादर करत आहे.",
                    "hi": "राशन कार्ड आवेदन जमा किया जा रहा है.",
                    "en": "Submitting ration card application."
                }
            },
            {
                "thought": "Ration card request processed successfully.",
                "action": "finish",
                "selector": "",
                "value": "",
                "feedback": {
                    "mr": "रेशन कार्ड अर्ज यशस्वीपणे सादर झाला आहे. पोचपावती क्रमांक जारी केला आहे.",
                    "hi": "राशन कार्ड आवेदन सफलतापूर्वक जमा हो गया है. पावती जारी कर दी गई है.",
                    "en": "Ration card application submitted successfully. Receipt issued."
                }
            }
        ]
    },
    "caste": {
        "keywords": ["जात", "प्रमाणपत्र", "पडताळणी", "जाति", "सत्यापन", "caste", "verification"],
        "name_mr": "जात प्रमाणपत्र पडताळणी",
        "name_hi": "जाति प्रमाण पत्र सत्यापन",
        "name_en": "Caste Certificate Verification",
        "steps": [
            {
                "thought": "Citizen requested Caste Verification. Navigating to CCVIS portal.",
                "action": "navigate",
                "selector": "",
                "value": "http://127.0.0.1:8000/portal/caste",
                "feedback": {
                    "mr": "जात प्रमाणपत्र पडताळणी पोर्टल उघडत आहे...",
                    "hi": "जाति प्रमाण पत्र सत्यापन पोर्टल खोला जा रहा है...",
                    "en": "Opening Caste Certificate Verification portal..."
                }
            },
            {
                "thought": "Entering caste certificate application number.",
                "action": "fill",
                "selector": "#caste_app_no",
                "value": "CC/2026/98214",
                "feedback": {
                    "mr": "जात प्रमाणपत्र अर्ज क्रमांक नोंदवला आहे.",
                    "hi": "जाति प्रमाण पत्र आवेदन संख्या दर्ज की गई है.",
                    "en": "Caste certificate application number entered."
                }
            },
            {
                "thought": "Submitting documentation for scrutiny.",
                "action": "click",
                "selector": "#verify_docs",
                "value": "",
                "feedback": {
                    "mr": "कागदपत्रे पडताळणीसाठी सादर केली आहेत.",
                    "hi": "दस्तावेज़ सत्यापन के लिए जमा किए गए हैं.",
                    "en": "Submitting documents for verification."
                }
            },
            {
                "thought": "Caste certificate verification request registered.",
                "action": "finish",
                "selector": "",
                "value": "",
                "feedback": {
                    "mr": "जात पडताळणी पावती स्क्रीनवर उपलब्ध झाली आहे.",
                    "hi": "जाति सत्यापन पावती स्क्रीन पर उपलब्ध है.",
                    "en": "Caste verification acknowledgment receipt is ready."
                }
            }
        ]
    },
    "farmer": {
        "keywords": ["शेतकरी", "अनुदान", "किसान", "सम्मान निधि", "mahadbt", "farmer", "subsidy"],
        "name_mr": "महाडीबीटी शेतकरी योजना",
        "name_hi": "महाडीबीटी किसान योजना",
        "name_en": "MahaDBT Farmer Scheme",
        "steps": [
            {
                "thought": "Citizen requested Farmer Subsidy. Navigating to MahaDBT portal.",
                "action": "navigate",
                "selector": "",
                "value": "http://127.0.0.1:8000/portal/mahadbt",
                "feedback": {
                    "mr": "महाडीबीटी शेतकरी योजना पोर्टल उघडत आहे...",
                    "hi": "महाडीबीटी किसान योजना पोर्टल खोला जा रहा है...",
                    "en": "Opening MahaDBT Farmer Subsidy portal..."
                }
            },
            {
                "thought": "Entering farmer identity ID.",
                "action": "fill",
                "selector": "#farmer_id",
                "value": "MH89201472",
                "feedback": {
                    "mr": "शेतकरी ओळख क्रमांक प्रविष्ट केला आहे.",
                    "hi": "किसान पहचान संख्या दर्ज की गई है.",
                    "en": "Farmer ID entered."
                }
            },
            {
                "thought": "Submitting agriculture subsidy application.",
                "action": "click",
                "selector": "#apply_scheme",
                "value": "",
                "feedback": {
                    "mr": "योजनेसाठी अर्ज सादर करत आहे.",
                    "hi": "योजना के लिए आवेदन जमा किया जा रहा है.",
                    "en": "Applying for agriculture subsidy scheme."
                }
            },
            {
                "thought": "Farmer subsidy application submitted.",
                "action": "finish",
                "selector": "",
                "value": "",
                "feedback": {
                    "mr": "शेतकरी अनुदान अर्ज यशस्वीपणे नोंदवला गेला आहे.",
                    "hi": "किसान सब्सिडी आवेदन सफलतापूर्वक दर्ज कर लिया गया है.",
                    "en": "Farmer subsidy application registered successfully."
                }
            }
        ]
    },
    "aadhaar": {
        "keywords": ["आधार", "लिंक", "तपासा", "aadhaar", "uidai", "status"],
        "name_mr": "आधार पडताळणी स्थिती",
        "name_hi": "आधार स्थिति सत्यापन",
        "name_en": "Aadhaar Status Verification",
        "steps": [
            {
                "thought": "Citizen requested Aadhaar link status. Navigating to UIDAI portal.",
                "action": "navigate",
                "selector": "",
                "value": "http://127.0.0.1:8000/portal/aadhaar",
                "feedback": {
                    "mr": "आधार पडताळणी पोर्टल उघडत आहे...",
                    "hi": "आधार सत्यापन पोर्टल खोला जा रहा है...",
                    "en": "Opening Aadhaar Status portal..."
                }
            },
            {
                "thought": "Entering masked Aadhaar number.",
                "action": "fill",
                "selector": "#aadhaar_no",
                "value": "XXXXXXXX4821",
                "feedback": {
                    "mr": "आधार क्रमांक प्रविष्ट केला आहे.",
                    "hi": "आधार संख्या दर्ज की गई है.",
                    "en": "Aadhaar number entered."
                }
            },
            {
                "thought": "Querying linking status.",
                "action": "click",
                "selector": "#check_status",
                "value": "",
                "feedback": {
                    "mr": "आधार लिंकिंग स्थिती तपासत आहे.",
                    "hi": "आधार लिंकिंग स्थिति जांची जा रही है.",
                    "en": "Checking Aadhaar linking status."
                }
            },
            {
                "thought": "Aadhaar link status confirmed active.",
                "action": "finish",
                "selector": "",
                "value": "",
                "feedback": {
                    "mr": "तुमचे आधार कार्ड यशस्वीरीत्या जोडलेले आहे.",
                    "hi": "आपका आधार कार्ड सफलतापूर्वक लिंक है.",
                    "en": "Your Aadhaar card is successfully linked."
                }
            }
        ]
    },
    "housing": {
        "keywords": ["आवास", "घरकुल", "housing", "pmay", "awas"],
        "name_mr": "ग्रामीण आवास घरकुल योजना",
        "name_hi": "ग्रामीण आवास योजना",
        "name_en": "Rural Housing Scheme",
        "steps": [
            {
                "thought": "Citizen requested housing scheme. Navigating to PMAY portal.",
                "action": "navigate",
                "selector": "",
                "value": "http://127.0.0.1:8000/portal/awas",
                "feedback": {
                    "mr": "ग्रामीण आवास घरकुल योजना पोर्टल उघडत आहे...",
                    "hi": "ग्रामीण आवास योजना पोर्टल खोला जा रहा है...",
                    "en": "Opening Rural Housing Scheme portal..."
                }
            },
            {
                "thought": "Entering beneficiary ID.",
                "action": "fill",
                "selector": "#beneficiary_id",
                "value": "MH-PMAY-4491",
                "feedback": {
                    "mr": "लाभार्थी नोंदणी क्रमांक प्रविष्ट केला आहे.",
                    "hi": "लाभार्थी पंजीकरण संख्या दर्ज की गई है.",
                    "en": "Beneficiary registration ID entered."
                }
            },
            {
                "thought": "Submitting housing scheme application.",
                "action": "click",
                "selector": "#submit_awas",
                "value": "",
                "feedback": {
                    "mr": "आवास योजनेसाठी अर्ज सादर करत आहे.",
                    "hi": "आवास योजना के लिए आवेदन जमा किया जा रहा है.",
                    "en": "Submitting housing scheme application."
                }
            },
            {
                "thought": "Housing scheme registration completed.",
                "action": "finish",
                "selector": "",
                "value": "",
                "feedback": {
                    "mr": "घरकुल आवास योजना अर्ज नोंदणी पूर्ण झाली आहे.",
                    "hi": "आवास योजना आवेदन पंजीकरण पूरा हो गया है.",
                    "en": "Housing scheme application completed."
                }
            }
        ]
    }
}


def clean_json_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Strips markdown code blocks, extracts JSON object, and strictly validates schema.
    Conforms to LLMDecision contract:
    { "thought": str, "action": str, "selector": str, "value": str, "feedback": str }
    """
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Search for json object { ... } with balanced braces
    start = cleaned.find("{")
    if start != -1:
        depth = 0
        end = -1
        for i in range(start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end != -1:
            cleaned = cleaned[start:end]

    try:
        obj = json.loads(cleaned)
        if not isinstance(obj, dict):
            return None

        # Enforce required keys
        required = ["thought", "action", "selector", "value", "feedback"]
        for k in required:
            if k not in obj:
                return None

        # Normalize and strictly validate action primitive
        action = str(obj.get("action", "")).lower().strip()
        if action not in VALID_ACTIONS:
            return None

        # Ensure feedback is non-empty
        feedback_str = str(obj.get("feedback", ""))

        if LLMDecision is not None:
            try:
                dec = LLMDecision(
                    thought=str(obj.get("thought", "")),
                    action=action,
                    selector=str(obj.get("selector", "") or ""),
                    value=str(obj.get("value", "") or ""),
                    feedback=feedback_str
                )
                return dec.to_dict()
            except Exception as e:
                logger.debug(f"[LLM] LLMDecision validation failed: {e}")
                return None

        return {
            "thought": str(obj.get("thought", "")),
            "action": action,
            "selector": str(obj.get("selector", "") or ""),
            "value": str(obj.get("value", "") or ""),
            "feedback": feedback_str
        }
    except Exception as e:
        logger.debug(f"[LLM] JSON parse failure: {e} in '{raw_text[:100]}'")
        return None


def match_governance_service(prompt: str) -> str:
    """Classifies user intent into a known Maharashtra e-governance domain."""
    p = prompt.lower()
    for s_key, s_data in GOVERNANCE_SERVICES.items():
        for kw in s_data["keywords"]:
            if kw.lower() in p:
                return s_key
    return "income"  # Default common governance service


def fallback_decide(
    prompt: str,
    language: str,
    step_index: int,
    current_url: str = "",
    dom_elements: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Deterministic Fallback Engine (PRD FR-3.3).
    Ensures 100% valid JSON contract and zero downtime when cloud API keys
    are expired, offline, or rate-limited.
    """
    lang_key = "mr" if "mr" in language.lower() else ("hi" if "hi" in language.lower() else "en")
    svc_key = match_governance_service(prompt)
    service = GOVERNANCE_SERVICES.get(svc_key, GOVERNANCE_SERVICES["income"])
    steps = service["steps"]

    # Choose step based on index, capping at final step
    idx = min(max(0, step_index), len(steps) - 1)
    step = steps[idx]

    fb = step["feedback"]
    feedback_text = fb.get(lang_key, fb.get("mr", fb.get("en", "")))

    return {
        "thought": step["thought"],
        "action": step["action"],
        "selector": step["selector"],
        "value": step["value"],
        "feedback": feedback_text
    }


def prune_context(prompt: str, history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Rolling Scratchpad (PRD Loop Guard):
    Retains only the original citizen goal and the last 3 immediate step deltas.
    Prevents context degradation and keeps cloud inference fast (<1.8s).
    """
    history = history or []
    pruned_history = history[-3:] if len(history) > 3 else history
    summary = f"Citizen Goal: {prompt}\n"
    if pruned_history:
        summary += "Recent Steps (last 3):\n"
        for i, h in enumerate(pruned_history, 1):
            if isinstance(h, dict):
                summary += f"  Step {i}: action={h.get('action')}, selector={h.get('selector')}, status={h.get('status')}\n"
    return summary


class CloudLLMGateway:
    """
    Managed Cloud LLM API Client for SEVA AI.
    Dual-Model Routing:
      1. Primary: Gemini 2.5 Flash via direct HTTPS REST endpoint (or google-genai).
      2. Secondary: OpenRouter Qwen 2.5 7B (qwen/qwen-2.5-7b-instruct:free).
      3. Fallback: Deterministic local Maharashtra e-governance database.
    Guarded by 8-second timeout, rate-limit (429) & network error handling.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        gemini_model: Optional[str] = None
    ):
        self.openrouter_api_key = api_key or OPENROUTER_API_KEY
        self.openrouter_model = model or OPENROUTER_MODEL
        self.openrouter_base_url = base_url or OPENROUTER_BASE_URL
        if not self.openrouter_base_url.endswith("/chat/completions"):
            self.openrouter_base_url = f"{self.openrouter_base_url.rstrip('/')}/chat/completions"

        self.gemini_api_key = gemini_api_key or GEMINI_API_KEY
        self.gemini_model = gemini_model or GEMINI_MODEL

        # Legacy attribute compatibility
        self.api_key = self.openrouter_api_key
        self.model = self.openrouter_model
        self.base_url = self.openrouter_base_url

        self._gemini_disabled = False
        self._openrouter_disabled = False

    @property
    def _api_disabled(self) -> bool:
        return self._gemini_disabled and self._openrouter_disabled

    @_api_disabled.setter
    def _api_disabled(self, val: bool) -> None:
        self._gemini_disabled = val
        self._openrouter_disabled = val

    def _call_cloud_api(
        self,
        prompt: str,
        language: str = "mr-IN",
        current_url: str = "",
        dom_elements: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        *args,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Unified cloud API call router for backward test compatibility."""
        dom_elements = dom_elements or []
        history = history or []

        # 1. Primary: Gemini 2.5 Flash
        if self.gemini_api_key and not self._gemini_disabled and not self.gemini_api_key.startswith("dummy"):
            gemini_result = self._call_gemini_api(prompt, language, current_url, dom_elements, history)
            if gemini_result is not None:
                return gemini_result

        # 2. Secondary: OpenRouter Qwen 2.5 7B
        if self.openrouter_api_key and not self._openrouter_disabled and not self.openrouter_api_key.startswith("sk-or-v1-dummy"):
            openrouter_result = self._call_openrouter_api(prompt, language, current_url, dom_elements, history)
            if openrouter_result is not None:
                return openrouter_result

        return None

    def decide(
        self,
        prompt: str,
        language: str = "mr-IN",
        current_url: str = "",
        dom_elements: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        step_index: int = 0
    ) -> Dict[str, Any]:
        """
        Main decision gateway:
        1. Prepares pruned context and visible DOM metadata.
        2. Tries Primary: Gemini 2.5 Flash within timeout budget (<=8s).
        3. Tries Secondary: OpenRouter Qwen 2.5 7B within timeout budget (<=8s).
        4. If cloud APIs fail/timeout/rate-limit, seamlessly invokes Fallback Engine (FR-3.3).
        """
        dom_elements = dom_elements or []
        history = history or []

        if not self._api_disabled:
            cloud_result = self._call_cloud_api(prompt, language, current_url, dom_elements, history)
            if cloud_result is not None:
                return cloud_result

        # 3. Deterministic Fallback Engine (FR-3.3)
        return fallback_decide(prompt, language, step_index, current_url, dom_elements)

    def _call_gemini_api(
        self,
        prompt: str,
        language: str,
        current_url: str,
        dom_elements: List[Dict[str, Any]],
        history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Makes direct HTTPS REST call to Gemini 2.5 Flash endpoint."""
        context_str = prune_context(prompt, history)
        dom_summary = json.dumps(dom_elements[:25], ensure_ascii=False)

        user_content = (
            f"Citizen Goal: {prompt}\n"
            f"Citizen Language: {language}\n"
            f"Active URL: {current_url}\n"
            f"Visible DOM Elements (max 25): {dom_summary}\n"
            f"{context_str}\n"
            "Return SINGLE next action as pure JSON conforming strictly to schema."
        )

        endpoint_url = f"{GEMINI_REST_BASE}/{self.gemini_model}:generateContent?key={self.gemini_api_key}"

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_content}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 300,
                "responseMimeType": "application/json"
            }
        }

        req = urllib.request.Request(
            endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SEVA-AI-Kiosk/1.0"
            }
        )

        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=API_TIMEOUT_SEC) as resp:
                elapsed = time.time() - t0
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_reply = parts[0].get("text", "")
                        validated = clean_json_response(raw_reply)
                        if validated:
                            logger.info(f"[LLM] Gemini 2.5 Flash succeeded in {elapsed:.2f}s: {validated['action']}")
                            return validated
                logger.warning(f"[LLM] Gemini 2.5 Flash output failed validation or missing candidates")
        except urllib.error.HTTPError as e:
            logger.warning(f"[LLM] Gemini HTTP {e.code}: {e.reason}")
            if e.code in (401, 403):
                logger.info("[LLM] Gemini API key rejected (401/403). Disabling Gemini.")
                self._api_disabled = True
            elif e.code == 429:
                logger.warning("[LLM] Gemini rate limited (429). Switching to secondary fallback.")
        except urllib.error.URLError as e:
            logger.warning(f"[LLM] Gemini network error: {e.reason}")
            self._gemini_disabled = True
        except TimeoutError:
            logger.warning(f"[LLM] Gemini exceeded timeout budget ({API_TIMEOUT_SEC}s)")
        except Exception as e:
            logger.warning(f"[LLM] Unexpected Gemini API error: {e}")
            if "401" in str(e) or "403" in str(e):
                self._api_disabled = True

        return None

    def _call_openrouter_api(
        self,
        prompt: str,
        language: str,
        current_url: str,
        dom_elements: List[Dict[str, Any]],
        history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Makes HTTPS request to OpenRouter Qwen 2.5 7B endpoint."""
        context_str = prune_context(prompt, history)
        dom_summary = json.dumps(dom_elements[:25], ensure_ascii=False)

        user_content = (
            f"Citizen Goal: {prompt}\n"
            f"Citizen Language: {language}\n"
            f"Active URL: {current_url}\n"
            f"Visible DOM Elements (max 25): {dom_summary}\n"
            f"{context_str}\n"
            "Return SINGLE next action as pure JSON."
        )

        payload = {
            "model": self.openrouter_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "max_tokens": 300
        }

        req = urllib.request.Request(
            self.openrouter_base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://seva-ai.kiosk.gov.in",
                "X-Title": "SEVA AI Kiosk",
                "User-Agent": "SEVA-AI-Kiosk/1.0"
            }
        )

        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=API_TIMEOUT_SEC) as resp:
                elapsed = time.time() - t0
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                choices = data.get("choices", [])
                if choices:
                    raw_reply = choices[0].get("message", {}).get("content", "")
                    validated = clean_json_response(raw_reply)
                    if validated:
                        logger.info(f"[LLM] OpenRouter Qwen succeeded in {elapsed:.2f}s: {validated['action']}")
                        return validated
                    logger.warning(f"[LLM] OpenRouter output failed validation: {raw_reply[:120]}")
        except urllib.error.HTTPError as e:
            logger.warning(f"[LLM] OpenRouter HTTP {e.code}: {e.reason}")
            if e.code in (401, 403):
                logger.info("[LLM] OpenRouter authentication rejected (401/403). Disabling OpenRouter.")
                self._api_disabled = True
            elif e.code == 429:
                logger.warning("[LLM] OpenRouter rate limited (429). Switching to local fallback.")
        except urllib.error.URLError as e:
            logger.warning(f"[LLM] OpenRouter network error: {e.reason}")
            self._openrouter_disabled = True
        except TimeoutError:
            logger.warning(f"[LLM] OpenRouter exceeded timeout budget ({API_TIMEOUT_SEC}s)")
        except Exception as e:
            logger.warning(f"[LLM] Unexpected OpenRouter error: {e}")
            if "401" in str(e) or "403" in str(e):
                self._api_disabled = True

        return None


# Module-level default gateway singleton
_default_gateway: Optional[CloudLLMGateway] = None


def get_default_gateway() -> CloudLLMGateway:
    """Returns singleton instance of CloudLLMGateway."""
    global _default_gateway
    if _default_gateway is None:
        _default_gateway = CloudLLMGateway()
    return _default_gateway


def decide_action(
    goal: str,
    history: List[Dict[str, Any]],
    url: str,
    dom_elements: List[Dict[str, Any]],
    language: str = "mr"
) -> Dict[str, str]:
    """
    Interface contract per PROJECT.md:
    backend/llm_client.py ↔ backend/odav_engine.py

    Returns deterministic dictionary:
    {
        "thought": str,
        "action": "navigate" | "click" | "fill" | "scroll" | "wait" | "finish",
        "selector": str,
        "value": str,
        "feedback": str
    }
    """
    gateway = get_default_gateway()
    return gateway.decide(
        prompt=goal,
        language=language,
        current_url=url,
        dom_elements=dom_elements,
        history=history,
        step_index=len(history) if history else 0
    )

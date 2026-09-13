"""
vdak-host/config/languages.py
Central language configuration for all 7 supported Indian languages.
Includes Whisper codes, EasyOCR script codes, Piper model names,
and all kiosk prompts translated into each language.
"""

# ─────────────────────────────────────────────────────────────────────────────
# SUPPORTED LANGUAGES — from PRD.md REQ-VOC-002
# ─────────────────────────────────────────────────────────────────────────────

SUPPORTED_LANGUAGES: dict = {

    "mr": {
        "name":          "Marathi",
        "native_name":   "मराठी",
        "whisper_code":  "mr",
        "easyocr_codes": ["hi", "en"],   # Devanagari script
        "piper_model":   "mr_IN-male.onnx",
        "prompts": {
            "greeting":    "नमस्कार! मी तुम्हाला सरकारी योजना किंवा अर्जासाठी कशी मदत करू शकतो?",
            "scan_doc":    "कृपया तुमचे आधार कार्ड कॅमेऱ्यासमोर ठेवा.",
            "confirm":     "मी पुढे जाऊ का? हो म्हणा किंवा नाही म्हणा.",
            "otp_prompt":  "तुमच्या मोबाईलवर आलेला OTP आता टाइप करा.",
            "filling":     "मी आता तुमचा अर्ज भरत आहे, कृपया थांबा.",
            "done":        "तुमचा अर्ज यशस्वीरित्या सादर केला! पावती छापली जात आहे.",
            "error":       "काहीतरी चूक झाली. कृपया पुन्हा प्रयत्न करा.",
            "hold_steady": "कृपया कागद स्थिर धरा.",
            "select_lang": "कृपया तुमची भाषा निवडा.",
            "cancel":      "अर्ज रद्द केला. धन्यवाद.",
        },
    },

    "hi": {
        "name":          "Hindi",
        "native_name":   "हिन्दी",
        "whisper_code":  "hi",
        "easyocr_codes": ["hi", "en"],   # Devanagari script
        "piper_model":   "hi_IN-male.onnx",
        "prompts": {
            "greeting":    "नमस्ते! मैं आपकी सरकारी योजनाओं और आवेदनों में कैसे मदद कर सकता हूँ?",
            "scan_doc":    "कृपया अपना आधार कार्ड कैमरे के सामने रखें।",
            "confirm":     "क्या मैं आगे बढ़ूँ? हाँ या नहीं कहें।",
            "otp_prompt":  "आपके मोबाइल पर आया OTP अभी टाइप करें।",
            "filling":     "मैं अभी आपका फॉर्म भर रहा हूँ, कृपया प्रतीक्षा करें।",
            "done":        "आपका आवेदन सफलतापूर्वक जमा हो गया! रसीद छापी जा रही है।",
            "error":       "कुछ गलत हो गया। कृपया फिर से प्रयास करें।",
            "hold_steady": "कृपया कागज़ स्थिर रखें।",
            "select_lang": "कृपया अपनी भाषा चुनें।",
            "cancel":      "आवेदन रद्द किया। धन्यवाद।",
        },
    },

    "gu": {
        "name":          "Gujarati",
        "native_name":   "ગુજરાતી",
        "whisper_code":  "gu",
        "easyocr_codes": ["gu", "en"],   # Gujarati script
        "piper_model":   "gu_IN-male.onnx",
        "prompts": {
            "greeting":    "નમસ્તે! હું સરકારી યોજનાઓ અને અરજીઓ માટે આપની કેવી રીતે મદદ કરી શકું?",
            "scan_doc":    "કૃપા કરીને આપનું આધાર કાર્ડ કૅમેરાની સામે રાખો.",
            "confirm":     "હું આગળ વધું? હા કે ના કહો.",
            "otp_prompt":  "આપના મોબાઇલ પર આવેલ OTP હવે ટાઇપ કરો.",
            "filling":     "હું હમણાં આપની અરજી ભરી રહ્યો છું, કૃપા કરી રાહ જુઓ.",
            "done":        "આપની અરજી સફળતાપૂર્વક સબમિટ થઈ! રસીદ છપાઈ રહી છે.",
            "error":       "કંઈક ખોટું થયું. કૃપા ફરી પ્રયાસ કરો.",
            "hold_steady": "કૃપા કરી કાગળ સ્થિર રાખો.",
            "select_lang": "કૃપા કરીને ભાષા પસંદ કરો.",
            "cancel":      "અરજી રદ કરી. આભાર.",
        },
    },

    "ta": {
        "name":          "Tamil",
        "native_name":   "தமிழ்",
        "whisper_code":  "ta",
        "easyocr_codes": ["ta", "en"],   # Tamil script
        "piper_model":   "ta_IN-male.onnx",
        "prompts": {
            "greeting":    "வணக்கம்! அரசு திட்டங்கள் மற்றும் விண்ணப்பங்களுக்கு நான் உங்களுக்கு எவ்வாறு உதவலாம்?",
            "scan_doc":    "உங்கள் ஆதார் அட்டையை கேமராவின் முன்னால் வையுங்கள்.",
            "confirm":     "நான் தொடரட்டுமா? ஆம் அல்லது இல்லை என்று சொல்லுங்கள்.",
            "otp_prompt":  "உங்கள் மொபைலில் வந்த OTP-ஐ இப்போது தட்டச்சு செய்யுங்கள்.",
            "filling":     "நான் இப்போது உங்கள் படிவத்தை நிரப்புகிறேன், தயவுசெய்து காத்திருங்கள்.",
            "done":        "உங்கள் விண்ணப்பம் வெற்றிகரமாக சமர்ப்பிக்கப்பட்டது! ரசீது அச்சிடப்படுகிறது.",
            "error":       "ஏதோ தவறு நடந்தது. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.",
            "hold_steady": "தாளை நிலையாக வையுங்கள்.",
            "select_lang": "உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்.",
            "cancel":      "விண்ணப்பம் ரத்து செய்யப்பட்டது. நன்றி.",
        },
    },

    "kn": {
        "name":          "Kannada",
        "native_name":   "ಕನ್ನಡ",
        "whisper_code":  "kn",
        "easyocr_codes": ["kn", "en"],   # Kannada script
        "piper_model":   "kn_IN-male.onnx",
        "prompts": {
            "greeting":    "ನಮಸ್ಕಾರ! ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಮತ್ತು ಅರ್ಜಿಗಳಿಗೆ ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?",
            "scan_doc":    "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಆಧಾರ್ ಕಾರ್ಡ್ ಅನ್ನು ಕ್ಯಾಮೆರಾ ಮುಂದೆ ಇಡಿ.",
            "confirm":     "ನಾನು ಮುಂದುವರಿಯಲೇ? ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ.",
            "otp_prompt":  "ನಿಮ್ಮ ಮೊಬೈಲ್‌ಗೆ ಬಂದ OTP ಅನ್ನು ಈಗ ಟೈಪ್ ಮಾಡಿ.",
            "filling":     "ನಾನು ಈಗ ನಿಮ್ಮ ಅರ್ಜಿಯನ್ನು ತುಂಬುತ್ತಿದ್ದೇನೆ, ದಯವಿಟ್ಟು ಕಾಯಿರಿ.",
            "done":        "ನಿಮ್ಮ ಅರ್ಜಿ ಯಶಸ್ವಿಯಾಗಿ ಸಲ್ಲಿಸಲಾಗಿದೆ! ರಸೀದಿ ಮುದ್ರಿಸಲಾಗುತ್ತಿದೆ.",
            "error":       "ಏನೋ ತಪ್ಪಾಗಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
            "hold_steady": "ದಯವಿಟ್ಟು ಕಾಗದವನ್ನು ಸ್ಥಿರವಾಗಿ ಹಿಡಿಯಿರಿ.",
            "select_lang": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ಆಯ್ಕೆ ಮಾಡಿ.",
            "cancel":      "ಅರ್ಜಿ ರದ್ದುಪಡಿಸಲಾಗಿದೆ. ಧನ್ಯವಾದ.",
        },
    },

    "te": {
        "name":          "Telugu",
        "native_name":   "తెలుగు",
        "whisper_code":  "te",
        "easyocr_codes": ["te", "en"],   # Telugu script
        "piper_model":   "te_IN-male.onnx",
        "prompts": {
            "greeting":    "నమస్కారం! ప్రభుత్వ పథకాలు మరియు దరఖాస్తులకు నేను మీకు ఎలా సహాయం చేయగలను?",
            "scan_doc":    "దయచేసి మీ ఆధార్ కార్డును కెమెరా ముందు ఉంచండి.",
            "confirm":     "నేను కొనసాగనా? అవును లేదా కాదు అని చెప్పండి.",
            "otp_prompt":  "మీ మొబైల్‌కు వచ్చిన OTP ఇప్పుడు టైప్ చేయండి.",
            "filling":     "నేను ఇప్పుడు మీ ఫారమ్ నింపుతున్నాను, దయచేసి వేచి ఉండండి.",
            "done":        "మీ దరఖాస్తు విజయవంతంగా సమర్పించబడింది! రసీదు ముద్రించబడుతోంది.",
            "error":       "ఏదో తప్పు జరిగింది. దయచేసి మళ్ళీ ప్రయత్నించండి.",
            "hold_steady": "దయచేసి కాగితాన్ని స్థిరంగా పట్టుకోండి.",
            "select_lang": "దయచేసి మీ భాషను ఎంచుకోండి.",
            "cancel":      "దరఖాస్తు రద్దు చేయబడింది. ధన్యవాదాలు.",
        },
    },

    "bn": {
        "name":          "Bengali",
        "native_name":   "বাংলা",
        "whisper_code":  "bn",
        "easyocr_codes": ["bn", "en"],   # Bengali script
        "piper_model":   "bn_IN-male.onnx",
        "prompts": {
            "greeting":    "নমস্কার! সরকারি প্রকল্প ও আবেদনের জন্য আমি আপনাকে কীভাবে সাহায্য করতে পারি?",
            "scan_doc":    "অনুগ্রহ করে আপনার আধার কার্ড ক্যামেরার সামনে রাখুন।",
            "confirm":     "আমি কি এগিয়ে যাব? হ্যাঁ বা না বলুন।",
            "otp_prompt":  "আপনার মোবাইলে আসা OTP এখন টাইপ করুন।",
            "filling":     "আমি এখন আপনার ফর্ম পূরণ করছি, অনুগ্রহ করে অপেক্ষা করুন।",
            "done":        "আপনার আবেদন সফলভাবে জমা দেওয়া হয়েছে! রসিদ মুদ্রণ করা হচ্ছে।",
            "error":       "কিছু একটা ভুল হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
            "hold_steady": "অনুগ্রহ করে কাগজটি স্থির রাখুন।",
            "select_lang": "অনুগ্রহ করে আপনার ভাষা বেছে নিন।",
            "cancel":      "আবেদন বাতিল করা হয়েছে। ধন্যবাদ।",
        },
    },
}

# Default language if none selected
DEFAULT_LANGUAGE = "mr"

# Language display list for UI dropdown
LANGUAGE_CHOICES = [
    (f"{v['native_name']} ({v['name']})", k)
    for k, v in SUPPORTED_LANGUAGES.items()
]


def get_language(code: str) -> dict:
    """Get language config by code. Falls back to Marathi."""
    return SUPPORTED_LANGUAGES.get(code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])


def get_prompt(code: str, prompt_key: str) -> str:
    """Get a specific prompt in the specified language."""
    lang = get_language(code)
    return lang["prompts"].get(prompt_key, lang["prompts"].get("error", ""))

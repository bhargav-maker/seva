"""
vdak-host/vision/ocr.py  (multi-language rewrite)
EasyOCR pipeline — dynamically loads the correct script engine
based on selected language. Aadhaar redaction always applied.
"""

import gc
import logging
import re
from typing import Optional

import cv2
import numpy as np

from config.languages import get_language

logger = logging.getLogger("vdak.ocr")

# Cache loaded readers to avoid reloading for the same script
_reader_cache: dict = {}


# ─────────────────────────────────────────────────────────────────────────────
# Aadhaar Redaction (UIDAI Compliance — REQ-DOC-004)
# ─────────────────────────────────────────────────────────────────────────────

def redact_aadhaar(text: str) -> str:
    """Mask first 8 digits of any 12-digit Aadhaar number. Always applied."""
    return re.sub(r'\b(\d{4})[\s\-]?(\d{4})[\s\-]?(\d{4})\b', r'XXXX-XXXX-\3', text)


def extract_fields(text: str) -> dict:
    """
    Regex + pattern-based field extraction from raw OCR text.
    Works across all Indian government identity documents.
    """
    fields = {}

    # Name (English or script variant)
    name = re.search(
        r'(?:Name|नाव|नाम|નામ|பெயர்|ಹೆಸರು|పేరు|নাম)[:\s]+([A-Za-z\u0900-\u097F\u0A80-\u0AFF\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0980-\u09FF ]+)',
        text,
    )
    if name:
        fields["name"] = name.group(1).strip()

    # Date of Birth
    dob = re.search(r'(?:DOB|Date of Birth|जन्म|জন্ম|జన్మ)[:\s/]+(\d{2}[/\-]\d{2}[/\-]\d{4})', text)
    if dob:
        fields["dob"] = dob.group(1)

    # Gender
    if re.search(r'\b(MALE|पुरुष|পুরুষ|పురుషుడు|남성)\b', text, re.IGNORECASE):
        fields["gender"] = "Male"
    elif re.search(r'\b(FEMALE|महिला|स्त्री|মহিলা|స్త్రీ)\b', text, re.IGNORECASE):
        fields["gender"] = "Female"

    # Aadhaar last 4 (after redaction)
    aadh = re.search(r'XXXX-XXXX-(\d{4})', text)
    if aadh:
        fields["aadhaar_last4"] = aadh.group(1)

    return fields


# ─────────────────────────────────────────────────────────────────────────────
# OCR Engine
# ─────────────────────────────────────────────────────────────────────────────

class OCREngine:
    """
    Language-aware EasyOCR engine.
    Loads the correct script reader based on the citizen's language.
    """

    def _get_reader(self, lang_code: str):
        """Return cached reader for the script, or create and cache a new one."""
        ocr_codes = tuple(get_language(lang_code)["easyocr_codes"])
        if ocr_codes not in _reader_cache:
            logger.info(f"[OCR] Loading EasyOCR for scripts: {ocr_codes}")
            import easyocr
            _reader_cache[ocr_codes] = easyocr.Reader(list(ocr_codes), gpu=False)
            logger.info("[OCR] Reader ready.")
        return _reader_cache[ocr_codes]

    def unload(self, lang_code: Optional[str] = None):
        """Free RAM. Unload specific language or all cached readers."""
        global _reader_cache
        if lang_code:
            key = tuple(get_language(lang_code)["easyocr_codes"])
            _reader_cache.pop(key, None)
        else:
            _reader_cache.clear()
        gc.collect()
        logger.info("[OCR] Reader(s) unloaded.")

    def extract(self, frame: np.ndarray, lang_code: str = "mr") -> dict:
        """
        Full OCR pipeline for a document image.

        Args:
            frame:     BGR numpy array from camera
            lang_code: language key (mr, hi, gu, ta, kn, te, bn)

        Returns:
            {
                "raw_text": str,   # Full OCR text, Aadhaar redacted
                "fields":   dict,  # Parsed structured fields
                "language": str,   # Language code used
            }
        """
        reader = self._get_reader(lang_code)

        # Preprocess: greyscale + contrast equalise
        grey     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        enhanced = cv2.equalizeHist(grey)

        results  = reader.readtext(enhanced, detail=0, paragraph=True)
        raw_text = " ".join(results)

        safe_text = redact_aadhaar(raw_text)
        fields    = extract_fields(safe_text)

        logger.info(f"[OCR] [{lang_code}] Fields: {fields}")
        return {
            "raw_text": safe_text,
            "fields":   fields,
            "language": lang_code,
        }

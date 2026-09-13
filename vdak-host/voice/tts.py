"""
vdak-host/voice/tts.py  (multi-language rewrite)
Piper TTS — speaks in all 7 supported Indian languages.
Falls back to text print if model not downloaded yet.
"""

import logging
import subprocess
import tempfile
from pathlib import Path

from config.languages import get_language, get_prompt

logger = logging.getLogger("vdak.tts")

MODELS_DIR = Path(__file__).parent.parent / "models" / "tts"

# Piper voice model download base URL (HuggingFace)
PIPER_HF_BASE = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main"
)

# Piper model paths per language
PIPER_MODEL_URLS = {
    "mr": f"{PIPER_HF_BASE}/mr/mr_IN/male/medium/mr_IN-male-medium.onnx",
    "hi": f"{PIPER_HF_BASE}/hi/hi_IN/male/medium/hi_IN-male-medium.onnx",
    "gu": f"{PIPER_HF_BASE}/gu/gu_IN/female/medium/gu_IN-female-medium.onnx",
    "ta": f"{PIPER_HF_BASE}/ta/ta_IN/female/medium/ta_IN-female-medium.onnx",
    "kn": f"{PIPER_HF_BASE}/kn/kn_IN/female/medium/kn_IN-female-medium.onnx",
    "te": f"{PIPER_HF_BASE}/te/te_IN/female/medium/te_IN-female-medium.onnx",
    "bn": f"{PIPER_HF_BASE}/bn/bn_IN/male/medium/bn_IN-male-medium.onnx",
}


def _model_path(lang_code: str) -> Path:
    model_name = get_language(lang_code)["piper_model"]
    return MODELS_DIR / model_name


def is_model_available(lang_code: str) -> bool:
    return _model_path(lang_code).exists()


class TTSEngine:
    """Multi-language Piper TTS engine."""

    def speak(self, text: str, lang_code: str = "mr") -> None:
        """Synthesise and play text in the given language."""
        logger.info(f"[TTS] [{lang_code}] {text[:70]}...")
        if is_model_available(lang_code):
            self._speak_piper(text, lang_code)
        elif is_model_available("hi") and lang_code in ("mr",):
            # Hindi Devanagari model is close enough for Marathi fallback
            logger.warning(f"[TTS] No {lang_code} model — falling back to Hindi.")
            self._speak_piper(text, "hi")
        else:
            logger.warning(f"[TTS] No model for {lang_code} — text only.")
            print(f"\n🔊 [{lang_code.upper()}] {text}\n")

    def say(self, prompt_key: str, lang_code: str = "mr") -> None:
        """Speak a pre-defined prompt by key in the given language."""
        text = get_prompt(lang_code, prompt_key)
        self.speak(text, lang_code)

    def _speak_piper(self, text: str, lang_code: str) -> None:
        model = _model_path(lang_code)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            subprocess.run(
                ["piper", "--model", str(model), "--output_file", tmp_path],
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
            )
            import sounddevice as sd
            import soundfile as sf
            data, rate = sf.read(tmp_path)
            sd.play(data, rate)
            sd.wait()
        except FileNotFoundError:
            logger.warning("[TTS] Piper binary not found — text only.")
            print(f"\n🔊 {text}\n")
        except Exception as e:
            logger.error(f"[TTS] Piper error: {e}")
            print(f"\n🔊 {text}\n")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # ---------------------------------------------------------------------- #
    # Download helper — run once per language to grab the model
    # ---------------------------------------------------------------------- #
    def download_model(self, lang_code: str) -> bool:
        """Download Piper voice model for a language. Returns True on success."""
        import urllib.request
        url  = PIPER_MODEL_URLS.get(lang_code)
        dest = _model_path(lang_code)
        if not url:
            logger.error(f"[TTS] No download URL for {lang_code}.")
            return False
        if dest.exists():
            logger.info(f"[TTS] Model already exists: {dest}")
            return True
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"[TTS] Downloading {lang_code} model...")
        try:
            urllib.request.urlretrieve(url, dest)
            # Also download .json config
            json_url  = url.replace(".onnx", ".onnx.json")
            json_dest = Path(str(dest) + ".json")
            urllib.request.urlretrieve(json_url, json_dest)
            logger.info(f"[TTS] Downloaded: {dest}")
            return True
        except Exception as e:
            logger.error(f"[TTS] Download failed: {e}")
            return False

    def download_all_models(self) -> None:
        """Download Piper models for all supported languages."""
        for code in PIPER_MODEL_URLS:
            self.download_model(code)

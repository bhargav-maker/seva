"""
vdak-host/voice/tts.py  — Fixed Piper URLs + non-blocking fallback
Uses verified rhasspy/piper-voices paths.
Hindi (rohan) model shared for Marathi — Devanagari script is the same.
"""

import logging
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from config.languages import get_language, get_prompt

logger = logging.getLogger("vdak.tts")

MODELS_DIR = Path(__file__).parent.parent / "models" / "tts"

# ── VERIFIED Piper model URLs (rhasspy/piper-voices, Sept 2026) ───────────────
# Pattern: /resolve/main/{lang}/{lang_IN}/{voice}/{quality}/{filename}
_HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

PIPER_MODEL_URLS: dict[str, dict] = {
    # Marathi → use Hindi (Devanagari identical script, intelligible)
    "mr": {
        "onnx": f"{_HF}/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx",
        "json": f"{_HF}/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx.json",
        "local": "mr_IN-male.onnx",   # saved locally as Marathi
    },
    "hi": {
        "onnx": f"{_HF}/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx",
        "json": f"{_HF}/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx.json",
        "local": "hi_IN-male.onnx",
    },
    # Gujarati
    "gu": {
        "onnx": f"{_HF}/gu/gu_IN/dhruv/medium/gu_IN-dhruv-medium.onnx",
        "json": f"{_HF}/gu/gu_IN/dhruv/medium/gu_IN-dhruv-medium.onnx.json",
        "local": "gu_IN-male.onnx",
    },
    # Tamil
    "ta": {
        "onnx": f"{_HF}/ta/ta_IN/coqui/medium/ta_IN-coqui-medium.onnx",
        "json": f"{_HF}/ta/ta_IN/coqui/medium/ta_IN-coqui-medium.onnx.json",
        "local": "ta_IN-male.onnx",
    },
    # Kannada — fallback to Hindi if not available
    "kn": {
        "onnx": f"{_HF}/kn/kn_IN/coqui/medium/kn_IN-coqui-medium.onnx",
        "json": f"{_HF}/kn/kn_IN/coqui/medium/kn_IN-coqui-medium.onnx.json",
        "local": "kn_IN-male.onnx",
    },
    # Telugu
    "te": {
        "onnx": f"{_HF}/te/te_IN/coqui/medium/te_IN-coqui-medium.onnx",
        "json": f"{_HF}/te/te_IN/coqui/medium/te_IN-coqui-medium.onnx.json",
        "local": "te_IN-male.onnx",
    },
    # Bengali
    "bn": {
        "onnx": f"{_HF}/bn/bn_IN/coqui/medium/bn_IN-coqui-medium.onnx",
        "json": f"{_HF}/bn/bn_IN/coqui/medium/bn_IN-coqui-medium.onnx.json",
        "local": "bn_IN-male.onnx",
    },
}


def _local_path(lang_code: str) -> Path:
    info = PIPER_MODEL_URLS.get(lang_code, {})
    return MODELS_DIR / info.get("local", f"{lang_code}-male.onnx")


def _is_available(lang_code: str) -> bool:
    return _local_path(lang_code).exists()


class TTSEngine:
    """
    Multi-language Piper TTS.
    NEVER blocks a session — always falls back to text print if audio unavailable.
    """

    def speak(self, text: str, lang_code: str = "mr") -> None:
        """Speak text in the given language. Never raises."""
        logger.info(f"[TTS] [{lang_code}] {text[:70]}")

        if _is_available(lang_code):
            self._piper(text, lang_code)
        elif _is_available("hi") and lang_code in ("mr", "kn", "te", "bn", "gu"):
            # Script-compatible fallback
            logger.warning(f"[TTS] No {lang_code} model → Hindi fallback.")
            self._piper(text, "hi")
        else:
            # Graceful text-only — session MUST continue
            logger.warning(f"[TTS] No voice model for '{lang_code}' — text only.")
            print(f"\n🔊 [{lang_code.upper()}] {text}\n", flush=True)

    def say(self, prompt_key: str, lang_code: str = "mr") -> None:
        """Speak a pre-defined prompt key."""
        self.speak(get_prompt(lang_code, prompt_key), lang_code)

    def _piper(self, text: str, lang_code: str) -> None:
        model = _local_path(lang_code)
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = Path(tmp.name)

            result = subprocess.run(
                ["piper", "--model", str(model), "--output_file", str(tmp_path)],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=15,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.decode())

            import sounddevice as sd
            import soundfile as sf
            data, rate = sf.read(str(tmp_path))
            sd.play(data, rate)
            sd.wait()
        except FileNotFoundError:
            logger.warning("[TTS] 'piper' binary not on PATH — install piper-tts.")
            print(f"\n🔊 {text}\n", flush=True)
        except Exception as e:
            logger.error(f"[TTS] Piper error: {e}")
            print(f"\n🔊 {text}\n", flush=True)
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

    # ── Download helpers ──────────────────────────────────────────────────── #

    def download_model(self, lang_code: str) -> bool:
        """Download Piper model files. Returns True on success."""
        info = PIPER_MODEL_URLS.get(lang_code)
        if not info:
            logger.error(f"[TTS] Unknown language: {lang_code}")
            return False

        dest = _local_path(lang_code)
        if dest.exists():
            logger.info(f"[TTS] {lang_code} model already present.")
            return True

        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        for file_type, url in [("onnx", info["onnx"]), ("json", info["json"])]:
            file_dest = dest if file_type == "onnx" else Path(str(dest) + ".json")
            logger.info(f"[TTS] Downloading {lang_code} {file_type} from {url}")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "vdak-kiosk/1.0"})
                with urllib.request.urlopen(req, timeout=30) as r, open(file_dest, "wb") as f:
                    f.write(r.read())
                logger.info(f"[TTS] Saved: {file_dest}")
            except urllib.error.HTTPError as e:
                logger.error(f"[TTS] HTTP {e.code} downloading {url} — model may not exist for {lang_code}")
                if file_type == "onnx":
                    return False   # Can't proceed without the model
            except Exception as e:
                logger.error(f"[TTS] Download error: {e}")
                if file_type == "onnx":
                    return False
        return dest.exists()

    def download_all_models(self) -> dict[str, bool]:
        results = {}
        for code in PIPER_MODEL_URLS:
            results[code] = self.download_model(code)
        return results

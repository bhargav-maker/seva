"""
vdak-host/voice/asr.py  — Fixed for Windows (WinError 1314 bypass)
Sets HF env vars BEFORE any import so symlinks are never attempted.
"""

# ── FIX: Set BEFORE any huggingface/ctranslate2 import ───────────────────────
import os
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

import gc
import logging
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd

from config.languages import get_language, SUPPORTED_LANGUAGES

logger = logging.getLogger("vdak.asr")

SAMPLE_RATE  = 16000
CHANNELS     = 1
MODEL_SIZE   = "tiny"   # ~150MB RAM — safe on 4GB Windows

# Local whisper model cache — avoids HF Hub symlink issues on Windows
WHISPER_CACHE = Path(__file__).parent.parent / "models" / "whisper"


class ASREngine:
    """
    Multi-language Whisper ASR with:
    - Lazy load / explicit unload to stay within 4GB RAM
    - Windows WinError 1314 bypass via env vars + local cache dir
    - Graceful fallback if model download fails
    """

    def __init__(self, model_size: str = MODEL_SIZE):
        self.model_size  = model_size
        self._model      = None
        self._load_lock  = threading.Lock()

    def _load(self) -> bool:
        """Load Whisper model. Returns True on success, False on failure."""
        if self._model is not None:
            return True
        with self._load_lock:
            if self._model is not None:
                return True
            try:
                logger.info(f"[ASR] Loading Whisper {self.model_size}...")
                WHISPER_CACHE.mkdir(parents=True, exist_ok=True)

                from faster_whisper import WhisperModel
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(WHISPER_CACHE),  # local cache, no HF symlinks
                )
                logger.info("[ASR] Whisper ready.")
                return True
            except OSError as e:
                if "1314" in str(e) or "symlink" in str(e).lower():
                    logger.error(
                        "[ASR] WinError 1314 — Windows blocked symlink creation.\n"
                        "FIX: Enable Developer Mode in Windows Settings → Update & Security → For Developers\n"
                        "OR run as Administrator."
                    )
                else:
                    logger.error(f"[ASR] Load failed: {e}")
                return False
            except Exception as e:
                logger.error(f"[ASR] Unexpected load error: {e}")
                return False

    def unload(self):
        self._model = None
        gc.collect()
        logger.info("[ASR] Unloaded.")

    def record(self, duration: float = 5.0) -> Optional[np.ndarray]:
        """Record from default mic. Returns None if sounddevice unavailable."""
        try:
            logger.info(f"[ASR] Recording {duration}s...")
            audio = sd.rec(
                int(duration * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
            )
            sd.wait()
            return audio.flatten()
        except Exception as e:
            logger.error(f"[ASR] Recording failed: {e}")
            return None

    def transcribe(self, audio: np.ndarray, lang_code: str = "mr") -> str:
        """Transcribe audio. Returns empty string if model unavailable."""
        if not self._load():
            return ""
        try:
            whisper_code = get_language(lang_code)["whisper_code"]
            segments, info = self._model.transcribe(
                audio,
                language=whisper_code,
                beam_size=3,
                vad_filter=True,
            )
            text = " ".join(s.text.strip() for s in segments)
            logger.info(f"[ASR] [{info.language}] → {text[:80]}")
            return text
        except Exception as e:
            logger.error(f"[ASR] Transcribe failed: {e}")
            return ""

    def listen_and_transcribe(self, lang_code: str = "mr", duration: float = 5.0) -> str:
        """Full pipeline: record → transcribe → unload. Never raises."""
        audio = self.record(duration)
        if audio is None:
            return ""
        text = self.transcribe(audio, lang_code)
        self.unload()
        return text

    def detect_language(self, duration: float = 3.0) -> str:
        """Auto-detect spoken language. Returns a key from SUPPORTED_LANGUAGES."""
        if not self._load():
            return "mr"
        audio = self.record(duration)
        if audio is None:
            return "mr"
        try:
            _, info = self._model.transcribe(audio, beam_size=1)
            detected = info.language
            self.unload()
            supported = {v["whisper_code"]: k for k, v in SUPPORTED_LANGUAGES.items()}
            return supported.get(detected, "mr")
        except Exception:
            return "mr"

"""
vdak-host/voice/asr.py  (multi-language rewrite)
Whisper Tiny ASR — supports all 7 Indian languages.
Lazy-loads and unloads model to stay within 4GB RAM.
"""

import gc
import logging
from typing import Optional

import numpy as np
import sounddevice as sd

from config.languages import get_language, SUPPORTED_LANGUAGES

logger = logging.getLogger("vdak.asr")

SAMPLE_RATE  = 16000
CHANNELS     = 1
MODEL_SIZE   = "tiny"   # ~150MB RAM — safe on 4GB Windows


class ASREngine:
    """Multi-language Whisper ASR with lazy load/unload for RAM efficiency."""

    def __init__(self, model_size: str = MODEL_SIZE):
        self.model_size = model_size
        self._model     = None

    def _load(self):
        if self._model is None:
            logger.info(f"[ASR] Loading Whisper {self.model_size}...")
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info("[ASR] Ready.")

    def unload(self):
        """Free RAM immediately after use."""
        self._model = None
        gc.collect()
        logger.info("[ASR] Unloaded.")

    def record(self, duration: float = 5.0) -> np.ndarray:
        """Record from default microphone for given duration."""
        logger.info(f"[ASR] Recording {duration}s...")
        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
        )
        sd.wait()
        return audio.flatten()

    def transcribe(self, audio: np.ndarray, lang_code: str = "mr") -> str:
        """
        Transcribe audio in the given language.
        lang_code: any key from SUPPORTED_LANGUAGES
                   e.g. "mr", "hi", "gu", "ta", "kn", "te", "bn"
        """
        self._load()
        whisper_code = get_language(lang_code)["whisper_code"]
        segments, info = self._model.transcribe(
            audio,
            language=whisper_code,
            beam_size=3,
            vad_filter=True,
        )
        text = " ".join(s.text.strip() for s in segments)
        logger.info(f"[ASR] [{info.language}] → {text}")
        return text

    def listen_and_transcribe(
        self,
        lang_code:  str   = "mr",
        duration:   float = 5.0,
    ) -> str:
        """Full pipeline — record → transcribe → unload."""
        audio = self.record(duration)
        text  = self.transcribe(audio, lang_code)
        self.unload()
        return text

    # ---------------------------------------------------------------------- #
    # Language detection — let Whisper decide the language automatically
    # ---------------------------------------------------------------------- #
    def detect_language(self, duration: float = 3.0) -> str:
        """
        Record a short clip and return the detected language code.
        Useful for auto-selecting UI language at kiosk startup.
        Returns a code like 'hi', 'ta', 'mr', etc.
        """
        self._load()
        audio = self.record(duration)
        _, info = self._model.transcribe(audio, beam_size=1)
        detected = info.language
        self.unload()
        logger.info(f"[ASR] Detected language: {detected}")
        # Map Whisper code back to our supported set (fallback to 'mr')
        supported_whisper = {v["whisper_code"]: k for k, v in SUPPORTED_LANGUAGES.items()}
        return supported_whisper.get(detected, "mr")

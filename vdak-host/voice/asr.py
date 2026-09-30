"""
vdak-host/voice/asr.py
Hardened Faster-Whisper ASR for SEVA AI Kiosk.
Uses WAV tempfile buffer + Silero VAD to permanently eliminate trailing loop hallucinations.
"""

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

import gc
import logging
import re
import tempfile
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import scipy.io.wavfile as wav
import sounddevice as sd

logger = logging.getLogger("vdak.asr")

SAMPLE_RATE = 16000
CHANNELS = 1
MODEL_SIZE = "tiny"

WHISPER_DIR = Path(__file__).parent.parent / "models" / "whisper"

PLACEHOLDER_PATTERNS = [
    r'\[(?:BLANK_AUDIO|SILENCE)\]',
    r'<\|nospeech\|>',
    r'\[\s*S\s*\]'
]

def clean_output(text: str) -> str:
    for pattern in PLACEHOLDER_PATTERNS:
        text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
    # Remove any word repeated 4 or more times consecutively (catches loops)
    text = re.sub(r'(\b\w+\b)(?:\s+\1){3,}', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

class ASREngine:
    def __init__(self, model_size: str = MODEL_SIZE):
        self.model_size = model_size
        self._model = None
        self._load_lock = threading.Lock()

    def _load(self) -> bool:
        if self._model is not None:
            return True
        with self._load_lock:
            if self._model is not None:
                return True
            try:
                from faster_whisper import WhisperModel
                WHISPER_DIR.mkdir(parents=True, exist_ok=True)
                logger.info(f"[ASR] Loading Whisper model ({self.model_size})...")
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(WHISPER_DIR),
                )
                logger.info("[ASR] Whisper ASR ready.")
                return True
            except Exception as e:
                logger.error(f"[ASR] Failed to load Whisper: {e}")
                return False

    def unload(self):
        self._model = None
        gc.collect()
        logger.info("[ASR] Whisper unloaded.")

    def record(self, duration: float = 4.0) -> Optional[np.ndarray]:
        try:
            logger.info(f"[ASR] Recording {duration}s...")
            audio = sd.rec(
                int(duration * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
            )
            sd.wait()
            arr = audio.flatten()

            max_vol = float(np.max(np.abs(arr)))
            if max_vol < 0.02:
                logger.info("[ASR] Audio too quiet, skipping.")
                return None

            arr = arr / max_vol * 0.95
            return arr
        except Exception as e:
            logger.error(f"[ASR] Recording error: {e}")
            return None

    def transcribe(self, audio: np.ndarray, lang_code: Optional[str] = None) -> str:
        if not self._load():
            return ""

        tmp_path = None
        try:
            # Save normalized float32 audio as standard 16-bit PCM WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                int16_data = (audio * 32767).astype(np.int16)
                wav.write(tmp_path, SAMPLE_RATE, int16_data)

            # Transcribe WAV file with VAD enabled to eliminate trailing silence loops
            segments, info = self._model.transcribe(
                tmp_path,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400),
            )
            raw_text = " ".join([s.text.strip() for s in list(segments)]).strip()
            final_text = clean_output(raw_text)
            logger.info(f"[ASR] [{info.language}] Recognized: '{final_text}'")
            return final_text
        except Exception as e:
            logger.error(f"[ASR] Transcription failed: {e}")
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def listen_and_transcribe(self, lang_code: Optional[str] = None, duration: float = 4.0) -> str:
        audio = self.record(duration)
        if audio is None:
            return ""
        return self.transcribe(audio, lang_code)

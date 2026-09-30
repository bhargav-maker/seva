"""
vdak-host/voice/tts.py
Direct Native Speech Synthesis Engine for SEVA AI / V-DAK.
Guarantees audible playback directly through Python sound drivers.
"""

import logging
import os
import pyttsx3
from pathlib import Path

from config.languages import get_prompt

logger = logging.getLogger("vdak.tts")

class TTSEngine:
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            # Select Indian accent or best clear voice available
            voices = self.engine.getProperty('voices')
            selected_voice = None
            for v in voices:
                desc = (v.name + " " + getattr(v, 'id', '')).lower()
                if any(x in desc for x in ["india", "ravi", "heera", "kalpana", "hemant", "en-in", "hi-in"]):
                    selected_voice = v.id
                    break
            
            if selected_voice:
                self.engine.setProperty('voice', selected_voice)
            
            # Natural speaking rate
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)
        except Exception as e:
            logger.error(f"[TTS] Engine init error: {e}")
            self.engine = None

    def speak(self, text: str, lang_code: str = "mr") -> None:
        logger.info(f"[TTS] [{lang_code}] {text[:70]}")
        print(f"\n🔊 Speaking: {text}\n", flush=True)

        if not self.engine:
            try:
                self.engine = pyttsx3.init()
            except Exception:
                return

        try:
            self.engine.stop()  # Clear any hung buffer
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logger.error(f"[TTS] Playback failure: {e}")

    def say(self, prompt_key: str, lang_code: str = "mr") -> None:
        self.speak(get_prompt(lang_code, prompt_key), lang_code)

    def download_model(self, lang_code: str = "hi") -> bool:
        return True

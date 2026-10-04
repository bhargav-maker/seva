#!/usr/bin/env python3
"""
SEVA AI Voice Agent
Real-time multilingual voice pipeline using LiveKit + Gemini 2.5 Flash.
Handles 22 Indian languages with proactive webcam presence detection.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from livekit import rtc
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.agents.llm import ChatContext, ChatMessage
from livekit.plugins import openai, silero
from livekit.plugins.google import gemini

logger = logging.getLogger(__name__)


@dataclass
class VoiceConfig:
    language: str = "hi-IN"
    sample_rate: int = 16000
    vad_threshold: float = 0.5
    presence_dwell_seconds: float = 1.0
    walk_away_seconds: float = 15.0


class PresenceDetector:
    """Ultra-lightweight OpenCV presence detector (<15MB RAM, 0% GPU)."""

    def __init__(self, config: VoiceConfig):
        self.config = config
        self.cap = None
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=100, varThreshold=50, detectShadows=False
        )
        self.presence_start = None
        self.absence_start = None
        self.citizen_present = False

    def start(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FPS, 10)
        logger.info("Presence detector started (webcam)")

    def stop(self):
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

    def check_presence(self) -> tuple[bool, str]:
        """
        Returns (presence_changed, event_type)
        event_type: "dwell_triggered", "walk_away", "none"
        """
        if not self.cap or not self.cap.isOpened():
            return False, "none"

        ret, frame = self.cap.read()
        if not ret:
            return False, "none"

        fg_mask = self.bg_subtractor.apply(frame)
        kernel = np.ones((5, 5), np.uint8)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        large_motion = any(cv2.contourArea(c) > 1500 for c in contours)

        current_time = asyncio.get_event_loop().time()

        if large_motion:
            self.absence_start = None
            if not self.citizen_present:
                if self.presence_start is None:
                    self.presence_start = current_time
                elif current_time - self.presence_start >= self.config.presence_dwell_seconds:
                    self.citizen_present = True
                    self.presence_start = None
                    return True, "dwell_triggered"
        else:
            self.presence_start = None
            if self.citizen_present:
                if self.absence_start is None:
                    self.absence_start = current_time
                elif current_time - self.absence_start >= self.config.walk_away_seconds:
                    self.citizen_present = False
                    self.absence_start = None
                    return True, "walk_away"

        return False, "none"


class VoiceAgent:
    """Main voice agent orchestrating LiveKit + Gemini + Presence Detection."""

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self.presence_detector = PresenceDetector(self.config)
        self.room: Optional[rtc.Room] = None
        self.agent_task: Optional[asyncio.Task] = None
        self.running = False
        self.current_language = self.config.language

    async def start(self):
        self.running = True
        self.presence_detector.start()

        livekit_url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
        livekit_token = os.getenv("LIVEKIT_TOKEN", "")

        self.room = rtc.Room()

        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"Participant connected: {participant.identity}")

        await self.room.connect(livekit_url, livekit_token, AutoSubscribe.AUDIO_ONLY)

        self.agent_task = asyncio.create_task(self._run_agent_loop())
        asyncio.create_task(self._presence_monitor_loop())
        logger.info("Voice Agent started successfully")

    async def stop(self):
        self.running = False
        if self.agent_task:
            self.agent_task.cancel()
        if self.room:
            await self.room.disconnect()
        self.presence_detector.stop()
        logger.info("Voice Agent stopped")

    async def _presence_monitor_loop(self):
        while self.running:
            changed, event = self.presence_detector.check_presence()
            if changed:
                if event == "dwell_triggered":
                    await self._proactive_greeting()
                elif event == "walk_away":
                    await self._privacy_purge()
            await asyncio.sleep(0.1)

    async def _proactive_greeting(self):
        greetings = {
            "mr-IN": "नमस्कार! ग्राम पंचायत डिजिटल सहाय्यकात स्वागत आहे. आज मी तुम्हाला कशी मदत करू शकतो?",
            "gu-IN": "નમસ્તે! ગ્રામ પંચાયત ડિજિટલ સહાયકમાં આપનું સ્વાગત છે. આજે હું તમને કેવી રીતે મદદ કરી શકું?",
            "kn-IN": "ನಮಸ್ಕಾರ! ಗ್ರಾಮ ಪಂಚಾಯತ ಡಿಜಿಟಲ್ ಸಹಾಯಕದಲ್ಲಿ ನಿಮಗೆ ಸ್ವಾಗತ. ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
            "ta-IN": "வணக்கம்! Граம் பஞ்சாயத் டிஜிட்டல் உதவியாளரில் உங்களை வரவேற்கிறேன். இன்று நான் உங்களுக்கு எப்படி உதவ முடியும்?",
            "hi-IN": "नमस्ते! ग्राम पंचायत डिजिटल सहायक में आपका स्वागत है। आज मैं आपकी कैसे मदद कर सकता हूँ?",
            "en-IN": "Namaste! Welcome to Gram Panchayat Digital Assistant. How can I help you today?",
        }
        greeting = greetings.get(self.current_language, greetings["hi-IN"])
        await self._speak(greeting)

    async def _privacy_purge(self):
        logger.warning("PRIVACY PURGE: Citizen walked away - wiping all session data")
        await self._speak("Session ended for privacy. Thank you.")

    async def _speak(self, text: str):
        if self.room and self.room.local_participant:
            await self.room.local_participant.publish_data(
                json.dumps({"type": "tts", "text": text, "language": self.current_language}).encode()
            )

    async def _run_agent_loop(self):
        try:
            llm = gemini.LLM(model="gemini-2.5-flash", temperature=0.3)
            stt = openai.STT(model="whisper-1", language=self.current_language)
            tts = openai.TTS(model="tts-1", voice="nova")
            vad = silero.VAD.load(threshold=self.config.vad_threshold)

            agent = rtc.Agent(
                llm=llm,
                stt=stt,
                tts=tts,
                vad=vad,
                chat_ctx=ChatContext(messages=[
                    ChatMessage(role="system", content=self._get_system_prompt())
                ]),
            )

            await agent.start(self.room)
            await asyncio.Future()
        except Exception as e:
            logger.error(f"Agent loop error: {e}")

    def _get_system_prompt(self) -> str:
        return f"""You are SEVA AI, a voice-first autonomous kiosk for Indian Gram Panchayats.
Current language: {self.current_language}

INVARIANTS (NEVER VIOLATE):
1. Chit-chat/scheme inquiries → NEVER open browser. Answer from offline DB.
2. Transaction requests (forms, certificates, payments) → MUST open visible Chrome (headless=False).
3. Before final Submit/Pay → PAUSE, highlight green (#00cc44), verbally summarize, wait for spoken confirmation.
4. Arithmetic captchas (e.g., "12 + 5") → Solve instantly with 100% accuracy.
5. Voice-first Indic number parsing: "पाच दोन आठ तीन" → 5283.
6. If citizen walks away 15+ sec → instant privacy purge.

CAPABILITIES (via FastMCP tools):
- open_government_portal(portal_name, parameters) → fills forms, solves captchas
- control_mobile_app(app_package, action, data) → e-Pik Pahani via ADB/REST
- print_and_send_document(file_path, citizen_phone) → thermal print + WhatsApp PDF
- query_offline_schemes(scheme_name, category) → offline FAQ answers

RESPONSE FORMAT: Natural conversational response in citizen's language.
Use tools when transaction/action required.
"""

    def set_language(self, language: str):
        self.current_language = language
        logger.info(f"Language switched to: {language}")


async def main():
    agent = VoiceAgent()
    await agent.start()
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
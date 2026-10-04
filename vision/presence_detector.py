#!/usr/bin/env python3
"""
SEVA AI Vision Presence Detector
Ultra-lightweight OpenCV presence detection (<15MB RAM, 0% GPU).
1-second dwell trigger & 15-second walk-away privacy purge.
"""

import asyncio
import cv2
import logging
import numpy as np
import time
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class PresenceConfig:
    dwell_seconds: float = 1.0
    walk_away_seconds: float = 15.0
    min_contour_area: int = 1500
    frame_width: int = 320
    frame_height: int = 240
    fps: int = 10
    history: int = 100
    var_threshold: int = 50


class PresenceDetector:
    """
    Lightweight webcam-based presence detector.
    - Dwell trigger: Citizen stands still for 1+ seconds → proactive greeting
    - Walk-away purge: Citizen absent for 15+ seconds → instant data wipe
    """

    def __init__(
        self,
        config: Optional[PresenceConfig] = None,
        on_dwell: Optional[Callable] = None,
        on_walk_away: Optional[Callable] = None
    ):
        self.config = config or PresenceConfig()
        self.on_dwell = on_dwell
        self.on_walk_away = on_walk_away

        self.cap: Optional[cv2.VideoCapture] = None
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.config.history,
            varThreshold=self.config.var_threshold,
            detectShadows=False
        )

        self.presence_start: Optional[float] = None
        self.absence_start: Optional[float] = None
        self.citizen_present = False
        self.running = False
        self._task: Optional[asyncio.Task] = None

        self.kernel = np.ones((5, 5), np.uint8)

    def start(self):
        """Start the webcam capture."""
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.running = True
        self._task = asyncio.create_task(self._detection_loop())
        logger.info("Presence detector started")

    def stop(self):
        """Stop the webcam capture."""
        self.running = False
        if self._task:
            self._task.cancel()
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        logger.info("Presence detector stopped")

    async def _detection_loop(self):
        while self.running:
            try:
                changed, event = self._check_presence()
                if changed:
                    if event == "dwell_triggered" and self.on_dwell:
                        await self.on_dwell()
                    elif event == "walk_away" and self.on_walk_away:
                        await self.on_walk_away()
            except Exception as e:
                logger.error(f"Detection loop error: {e}")
            await asyncio.sleep(0.1)

    def _check_presence(self) -> tuple[bool, str]:
        """
        Check for presence changes.
        Returns: (changed, event_type)
        event_type: "dwell_triggered", "walk_away", "none"
        """
        if not self.cap or not self.cap.isOpened():
            return False, "none"

        ret, frame = self.cap.read()
        if not ret:
            return False, "none"

        fg_mask = self.bg_subtractor.apply(frame)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self.kernel)

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        large_motion = any(cv2.contourArea(c) > self.config.min_contour_area for c in contours)

        current_time = time.time()

        if large_motion:
            self.absence_start = None
            if not self.citizen_present:
                if self.presence_start is None:
                    self.presence_start = current_time
                elif current_time - self.presence_start >= self.config.dwell_seconds:
                    self.citizen_present = True
                    self.presence_start = None
                    logger.info("DWELL TRIGGERED: Citizen detected for 1+ seconds")
                    return True, "dwell_triggered"
        else:
            self.presence_start = None
            if self.citizen_present:
                if self.absence_start is None:
                    self.absence_start = current_time
                elif current_time - self.absence_start >= self.config.walk_away_seconds:
                    self.citizen_present = False
                    self.absence_start = None
                    logger.warning("WALK AWAY: Citizen absent for 15+ seconds - PRIVACY PURGE")
                    return True, "walk_away"

        return False, "none"

    def is_citizen_present(self) -> bool:
        return self.citizen_present

    def get_status(self) -> dict:
        return {
            "citizen_present": self.citizen_present,
            "dwell_progress": (time.time() - self.presence_start) / self.config.dwell_seconds if self.presence_start else 0,
            "away_progress": (time.time() - self.absence_start) / self.config.walk_away_seconds if self.absence_start else 0,
        }


async def main():
    async def on_dwell():
        print("🎯 DWELL TRIGGERED - Proactive greeting!")

    async def on_walk_away():
        print("🚨 WALK AWAY - Privacy purge!")

    detector = PresenceDetector(on_dwell=on_dwell, on_walk_away=on_walk_away)
    detector.start()

    try:
        while True:
            status = detector.get_status()
            print(f"Status: {status}")
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        detector.stop()


if __name__ == "__main__":
    asyncio.run(main())
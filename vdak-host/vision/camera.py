"""
vdak-host/vision/camera.py
OpenCV camera abstraction — document capture + perspective dewarping.
Optimised for lightweight footprint on 4GB machines.
"""

import logging
import time
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("vdak.camera")

CAMERA_INDEX  = 0          # Default webcam
BLUR_THRESHOLD = 80.0      # Laplacian variance — below this = too blurry


def measure_blur(frame: np.ndarray) -> float:
    """Laplacian variance — higher = sharper."""
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(grey, cv2.CV_64F).var()


def dewarp(frame: np.ndarray) -> np.ndarray:
    """
    Attempt automatic quad-corner detection and perspective correction.
    Falls back to the original frame if no clear document contour found.
    """
    grey   = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur   = cv2.GaussianBlur(grey, (5, 5), 0)
    edges  = cv2.Canny(blur, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return frame

    # Largest contour = document boundary
    largest = max(contours, key=cv2.contourArea)
    epsilon = 0.02 * cv2.arcLength(largest, True)
    approx  = cv2.approxPolyDP(largest, epsilon, True)

    if len(approx) != 4:
        return frame    # Not a clean quad — return as-is

    pts = approx.reshape(4, 2).astype("float32")
    # Order: top-left, top-right, bottom-right, bottom-left
    s   = pts.sum(axis=1)
    rect = np.zeros((4, 2), dtype="float32")
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    (tl, tr, br, bl) = rect
    w = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    h = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))

    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype="float32")
    M   = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(frame, M, (w, h))


class CameraCapture:
    """Manages webcam lifecycle and document capture."""

    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index
        self._cap: Optional[cv2.VideoCapture] = None

    def open(self):
        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_index}")
        logger.info(f"[CAM] Camera {self.camera_index} opened.")

    def close(self):
        if self._cap:
            self._cap.release()
            self._cap = None
        logger.info("[CAM] Camera released.")

    def capture_document(
        self,
        max_attempts: int = 10,
        delay: float = 0.3,
    ) -> Optional[np.ndarray]:
        """
        Capture a sharp, dewarped document frame.
        Retries up to max_attempts until sharpness threshold is met.
        Returns None if no sharp frame found.
        """
        if not self._cap:
            self.open()

        for attempt in range(max_attempts):
            ret, frame = self._cap.read()
            if not ret:
                logger.warning("[CAM] Frame read failed.")
                time.sleep(delay)
                continue

            sharpness = measure_blur(frame)
            logger.debug(f"[CAM] Attempt {attempt+1}: sharpness={sharpness:.1f}")

            if sharpness >= BLUR_THRESHOLD:
                dewarped = dewarp(frame)
                logger.info(f"[CAM] Sharp frame captured (blur={sharpness:.1f})")
                return dewarped

            time.sleep(delay)

        logger.warning("[CAM] Could not capture sharp frame — returning best effort.")
        ret, frame = self._cap.read()
        return frame if ret else None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()

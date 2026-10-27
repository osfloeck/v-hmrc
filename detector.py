
"""
    detector.py
    Detects objects in captured Minecraft frames.
"""

import cv2
import numpy as np

CONTOUR_AREA_MIN_SIZE_FILTER = 250

def detect_magenta_objects(frame: np.ndarray) -> list[dict]:
    """
        frame: ndarray[tuple[int, int, int], dtype[unsignedinteger[_8Bit]]]
    """
    
    # First convert raw frame to BGR (drop alpha), then to HSV
    bgr_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    hsv_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2HSV)

    lower_magenta = (125, 70, 50)
    upper_magenta = (175, 255, 255)

    mask = cv2.inRange(hsv_frame, lower_magenta, upper_magenta)

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    detections = []

    for contour in contours:
        if cv2.contourArea(contour) < CONTOUR_AREA_MIN_SIZE_FILTER:
            continue

        x, y, width, height = cv2.boundingRect(contour)

        detections.append({
            "x": x, "y": y,
            "width": width, "height": height,
            "label": "Magenta object",
        })

    return detections

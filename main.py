
"""
    main.py
    Application entry point for V-HMRC.
"""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from capture import MinecraftCapture
from detector import detect_magenta_objects
from overlay import MinecraftOverlay


def main():
    application = QApplication(sys.argv)

    mc = MinecraftCapture(target_fps=30)
    mc.start()

    try:
        overlay = MinecraftOverlay(mc.window_bounds)
        overlay.show()

        def refresh_overlay():
            frame = mc.get_latest_frame()

            if frame is None:
                return

            detections = detect_magenta_objects(frame)
            overlay.update_detections(detections)

        detection_timer = QTimer()
        detection_timer.timeout.connect(refresh_overlay)
        detection_timer.start(100)

        QTimer.singleShot(30000, application.quit)
        application.exec()

    finally:
        mc.stop()


if __name__ == "__main__":
    main()

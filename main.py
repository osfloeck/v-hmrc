"""
    main.py
    Application entry point for V-HMRC
"""

# pyright: reportAttributeAccessIssue=false

import time

from AppKit import NSApplication
from capture import MinecraftCapture


def main():
    NSApplication.sharedApplication()

    mc = MinecraftCapture(target_fps=30)
    mc.start()

    try:
        for _ in range(5):
            time.sleep(1)

            frame = mc.get_latest_frame()

            if frame is None:
                print("Waiting for first frame...")
                continue

            print(f"Latest frame: {frame.shape}")

    finally:
        mc.stop()
    
if __name__ == "__main__":
    main()



"""
    main.py
    Program entry point
"""

# pyright: reportAttributeAccessIssue=false

import Quartz
import mss
import numpy as np
import cv2
import time

def find_mc_window():
    """
    Here we simply grab the Minecraft window and pass these dimensions to our
    mss library for screen recording.
    """
    options = (
        Quartz.kCGWindowListOptionOnScreenOnly
        | Quartz.kCGWindowListExcludeDesktopElements
    )
    windows = Quartz.CGWindowListCopyWindowInfo(
        options,
        Quartz.kCGNullWindowID
    )
    mc_window = None

    for window in windows:
        if window.get(Quartz.kCGWindowLayer) != 0:
            continue
        
        application = window.get(Quartz.kCGWindowOwnerName, "")
        title = window.get(Quartz.kCGWindowName, "")
        
        if "java" not in application or "Minecraft" not in title:
            continue
        
        mc_window = window

    return mc_window


def screenshot(window):    
    if window is None:
        print("Error: Window provided does not exist!")
        return
    
    window_bounds = window["kCGWindowBounds"]
    print(f"window: {window_bounds}")
   
    with mss.MSS() as sct:
        monitor = {"top": window_bounds["Y"], "left": window_bounds["X"],
                    "width": window_bounds["Width"], "height": window_bounds["Height"]}
        
        while "Screen capturing":
            last_time = time.time()
            
            img = np.array(sct.grab(monitor))
            
            cv2.imshow("OpenCV/Numpy normal", img)
            print(f"fps: {1 / (time.time() - last_time)}")
            
            # press "q" to quit
            if cv2.waitKey(25) & 0xFF == ord("q"):
                cv2.destroyAllWindows()
                break

        
def main():
    window = find_mc_window()
    screenshot(window)
    
if __name__ == "__main__":
    main()



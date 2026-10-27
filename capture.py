"""
    capture.py
    Discovers Minecraft and captures its window using ScreenCaptureKit
"""

# pyright: reportAttributeAccessIssue=false

from threading import Lock, Event
import numpy as np
import dispatch
import objc
from Foundation import NSObject
import Quartz
from CoreMedia import (
    CMTimeMake, 
    CMSampleBufferGetImageBuffer
)
from ScreenCaptureKit import (
    SCContentFilter,
    SCShareableContent,
    SCStream,
    SCStreamConfiguration,
    SCStreamOutputTypeScreen,
)

CALLBACK_TIMEOUT_SECONDS = 10

class MinecraftCapture:
    """
        Retrieves frame from Minecraft window using
        Apple's ScreenCaptureKit
    """
    def __init__(self, target_fps: int = 30):
        if target_fps <= 0:
            raise ValueError("Target FPS must be positive")
        
        self.target_fps = target_fps
        self._stream = None
        self._receiver = None
        self._callback_queue = None
        
        self._latest_frame = None
        self._frame_lock = Lock()
        
        self.window_bounds = None
        
    def _publish_frame(self, frame):
        with self._frame_lock:
            self._latest_frame = frame
    
    def get_latest_frame(self):
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()
    
    def _create_stream(self):
        minecraft_window = find_minecraft_window()
        
        if minecraft_window is None:
            raise RuntimeError("Minecraft window not found!")
        
        frame = minecraft_window.frame()
        
        self.window_bounds = {
            "x": frame.origin.x,
            "y": frame.origin.y,
            "width": frame.size.width,
            "height": frame.size.height,
        }
        
        content_filter = SCContentFilter.alloc().initWithDesktopIndependentWindow_(
            minecraft_window
        )
        
        configuration = create_configuration(content_filter, self.target_fps)
        configuration.setPixelFormat_(Quartz.kCVPixelFormatType_32BGRA)

        # Give the receiver access to its owning capture instance
        self._receiver = FrameReceiver.alloc().init()
        self._receiver.capture = self

        self._callback_queue = dispatch.dispatch_queue_create(
            b"vhmrc.capture",
            None,
        )
        
        return create_stream(
            content_filter, configuration, self._receiver, self._callback_queue
        )
    
    def start(self):
        if self._stream is not None:
            raise RuntimeError("Capture already started")

        self._stream = self._create_stream()
        
        wait_for_operation(
            self._stream.startCaptureWithCompletionHandler_,
            "start capture"
        )
    
    def stop(self):
        if self._stream is None:
            return
        
        wait_for_operation(
            self._stream.stopCaptureWithCompletionHandler_,
            "stop capture"
        )
    
        with self._frame_lock:
            self._latest_frame = None
        
        if self._receiver is not None:
            self._receiver.capture = None
    
        self._stream = None
        self._receiver = None
        self._callback_queue = None
        
        self.window_bounds = None


class FrameReceiver(NSObject, protocols=[objc.protocolNamed("SCStreamOutput")]):
    """
        output_type: 0 screen, 1 audio, 2 microphone
        sample_buffer (CMSampleBufferRef): an opaque Apple container holding raw frame
    """
    def stream_didOutputSampleBuffer_ofType_(self, stream, sample_buffer, output_type):
        try:
            if output_type != SCStreamOutputTypeScreen:
                return

            pixel_buffer = CMSampleBufferGetImageBuffer(sample_buffer)
            
            if pixel_buffer is None:
                return

            frame = pixel_buffer_to_numpy(pixel_buffer)
            
            self.capture._publish_frame(frame)

        except Exception as error:
            print(f"Frame callback error: {error}")


def find_minecraft_window():
    result_holder = {}
    completed_event = Event()

    def handle_content(content, error):
        result_holder["content"] = content
        result_holder["error"] = error
        completed_event.set()

    SCShareableContent.getShareableContentWithCompletionHandler_(
        handle_content
    )

    if not completed_event.wait(timeout=CALLBACK_TIMEOUT_SECONDS):
        raise TimeoutError("Timed out retrieving windows")

    if result_holder["error"] is not None:
        raise RuntimeError(
            f"ScreenCaptureKit error: {result_holder['error']}"
        )

    if result_holder["content"] is None:
        raise RuntimeError("No shareable content returned")

    for window in result_holder["content"].windows():
        application = window.owningApplication()
        application_name = (
            application.applicationName() if application else ""
        )
        window_title = window.title() or ""

        if "java" in application_name and "Minecraft" in window_title:
            return window

    return None


def create_configuration(content_filter, target_fps):
    configuration = SCStreamConfiguration.alloc().init()

    content_rect = content_filter.contentRect()
    pixel_scale = content_filter.pointPixelScale()

    width = round(content_rect.size.width * pixel_scale)
    height = round(content_rect.size.height * pixel_scale)

    configuration.setWidth_(width)
    configuration.setHeight_(height)
    configuration.setMinimumFrameInterval_(
        CMTimeMake(1, target_fps)
    )
    configuration.setQueueDepth_(3)

    return configuration


def create_stream(content_filter, configuration, receiver, queue):
    stream = SCStream.alloc().initWithFilter_configuration_delegate_(
        content_filter,
        configuration,
        None,
    )

    success, error = stream.addStreamOutput_type_sampleHandlerQueue_error_(
        receiver,
        SCStreamOutputTypeScreen,
        queue,
        None,
    )

    if not success:
        raise RuntimeError(f"Could not register stream output: {error}")

    return stream


def wait_for_operation(operation, operation_name):
    result_holder = {}
    completed_event = Event()

    def handle_completion(error):
        result_holder["error"] = error
        completed_event.set()

    operation(handle_completion)

    if not completed_event.wait(timeout=CALLBACK_TIMEOUT_SECONDS):
        raise TimeoutError(f"Timed out waiting to {operation_name}")

    if result_holder["error"] is not None:
        raise RuntimeError(
            f"Could not {operation_name}: {result_holder['error']}"
        )


def pixel_buffer_to_numpy(pixel_buffer):
    pixel_format = Quartz.CVPixelBufferGetPixelFormatType(pixel_buffer)

    if pixel_format != Quartz.kCVPixelFormatType_32BGRA:
        raise ValueError("Expected BGRA pixel format")

    width = Quartz.CVPixelBufferGetWidth(pixel_buffer)
    height = Quartz.CVPixelBufferGetHeight(pixel_buffer)
    bytes_per_row = Quartz.CVPixelBufferGetBytesPerRow(pixel_buffer)

    ## lock before playing with frame
    lock_flags = Quartz.kCVPixelBufferLock_ReadOnly
    lock_result = Quartz.CVPixelBufferLockBaseAddress(pixel_buffer, lock_flags)

    if lock_result != 0:
        raise RuntimeError(f"Pixel buffer lock failed: {lock_result}")

    try:
        base_address = Quartz.CVPixelBufferGetBaseAddress(pixel_buffer)
        if base_address is None:
            raise RuntimeError("Pixel buffer has no base address")

        raw_memory = base_address.as_buffer(height * bytes_per_row)

        pixel_rows = np.frombuffer(raw_memory, dtype=np.uint8)
        pixel_rows = pixel_rows.reshape(height, bytes_per_row)

        image_bytes = pixel_rows[:, :width * 4]
        frame = image_bytes.reshape(height, width, 4).copy()

        return frame
    finally:
        # then unlock buffer
        Quartz.CVPixelBufferUnlockBaseAddress(pixel_buffer, lock_flags)


"""
    overlay.py
    Transparent drawing layer
"""

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget


class MinecraftOverlay(QWidget):
    def __init__(self, bounds):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )
        
        self.setGeometry(
            round(bounds["x"]),
            round(bounds["y"]),
            round(bounds["width"]),
            round(bounds["height"]),
        )
        
        self._detections = []

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(QColor(0, 255, 0), 3))

        for detection in self._detections:
            rect = QRect(
                detection["x"],
                detection["y"],
                detection["width"],
                detection["height"],
            )
            
            painter.drawRect(rect)
            painter.setFont(QFont("Menlo", 14))
            painter.drawText(
                detection["x"],
                detection["y"] + detection["height"] + 17,
                detection["label"],
            )
            
        painter.end()
    
    def update_detections(self, detections: list[dict]):
        self._detections = detections.copy()
        self.update()
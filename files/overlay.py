"""
overlay.py — Borderless, always-on-top PyQt6 overlay window.

Renders keys as rounded rectangles on a transparent background.
Receives key events via update_key(key_id, pressed).
"""

import logging
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QFontMetrics
from PyQt6.QtWidgets import QWidget

log = logging.getLogger("overlay")

UNIT = 44   # fallback — overridden by theme


def _hex(color: str | None, fallback: str) -> QColor:
    if color:
        try:
            return QColor(color)
        except Exception:
            log.warning("Invalid colour '%s', using fallback", color)
    return QColor(fallback)


class OverlayWindow(QWidget):
    closed = pyqtSignal()

    def __init__(self, keys: list, theme: dict):
        super().__init__()
        self._keys   = keys      # list of key dicts
        self._theme  = dict(theme)
        self._pressed: set[str] = set()
        self._drag_pos: QPoint | None = None

        self._setup_window()
        self._compute_geometry()
        log.info("OverlayWindow created with %d keys", len(keys))

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setWindowTitle("Keyboard Overlay")

        alpha = int(self._theme.get("overlay_alpha", 0.93) * 255)
        self.setWindowOpacity(self._theme.get("overlay_alpha", 0.93))

    def _compute_geometry(self):
        """Work out the pixel size needed to fit all keys."""
        t = self._theme
        unit = t.get("key_unit_px", UNIT)
        gap  = t.get("key_gap_px", 4)
        kh   = t.get("key_height_px", UNIT)
        PAD  = 10

        max_x = max_y = 0
        for k in self._keys:
            rx = k["x"] * (unit + gap) + k["w"] * unit + (k["w"] - 1) * gap
            ry = k["y"] * (kh + gap) + k["h"] * kh + (k["h"] - 1) * gap
            max_x = max(max_x, rx)
            max_y = max(max_y, ry)

        w = int(max_x) + PAD * 2
        h = int(max_y) + PAD * 2
        self.setFixedSize(w, h)
        log.debug("Overlay size: %dx%d", w, h)

    # ── Public API ────────────────────────────────────────────────────────────

    def load_keys(self, keys: list, theme: dict | None = None):
        """Hot-swap layout without closing the window."""
        self._keys = keys
        if theme:
            self._theme = dict(theme)
        self._setup_window()
        self._compute_geometry()
        self.update()
        log.info("Overlay layout reloaded (%d keys)", len(keys))

    def update_key(self, key_id: str, pressed: bool):
        """Called from main thread via Qt signal/slot or after() safe call."""
        changed = False
        if pressed and key_id not in self._pressed:
            self._pressed.add(key_id)
            changed = True
        elif not pressed and key_id in self._pressed:
            self._pressed.discard(key_id)
            changed = True
        if changed:
            self.update()   # triggers paintEvent — Qt batches these efficiently

    def set_theme(self, theme: dict):
        self._theme = dict(theme)
        self._setup_window()
        self._compute_geometry()
        self.update()

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        t = self._theme
        unit  = t.get("key_unit_px", UNIT)
        gap   = t.get("key_gap_px", 4)
        kh    = t.get("key_height_px", UNIT)
        rad   = t.get("key_radius", 6)
        PAD   = 10

        font = QFont(
            t.get("font_family", "Consolas"),
            t.get("font_size", 10),
        )
        if t.get("font_bold", True):
            font.setBold(True)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(font)

        # Transparent background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        for k in self._keys:
            kid = k["id"]
            pressed = kid in self._pressed
            is_mouse = kid.startswith("mouse_")

            # Colours — per-key override → theme
            if pressed:
                if is_mouse:
                    bg_color = _hex(None, t.get("mouse_pressed", "#1e90ff"))
                else:
                    bg_color = _hex(k.get("color") and None, t.get("key_pressed", "#7b68ee"))
            else:
                if k.get("color"):
                    bg_color = _hex(k["color"], t.get("key_idle", "#2a2a3a"))
                elif is_mouse:
                    bg_color = _hex(None, t.get("mouse_idle", "#1e3a5f"))
                else:
                    bg_color = _hex(None, t.get("key_idle", "#2a2a3a"))

            outline_color = _hex(t.get("key_outline", "#444466"), "#444466")
            if k.get("text_color"):
                text_color = _hex(k["text_color"], t.get("key_text", "#ffffff"))
            else:
                text_color = _hex(None, t.get("key_text", "#ffffff"))

            # Pixel rect
            px = PAD + k["x"] * (unit + gap)
            py = PAD + k["y"] * (kh + gap)
            pw = k["w"] * unit + (k["w"] - 1) * gap
            ph = k["h"] * kh + (k["h"] - 1) * gap

            rect = QRectF(px, py, pw, ph)

            # Draw background
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(outline_color, 1))
            painter.drawRoundedRect(rect, rad, rad)

            # Draw label
            painter.setPen(QPen(text_color))
            fm = QFontMetrics(font)
            label = k.get("label", kid)
            # Use smaller font if label is long
            draw_font = font
            if len(label) > 5:
                small = QFont(font)
                small.setPointSize(max(6, t.get("font_size", 10) - 2))
                painter.setFont(small)
                draw_font = small
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
            if draw_font is not font:
                painter.setFont(font)

        painter.end()

    # ── Drag to move ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def closeEvent(self, event):
        log.info("Overlay window closed")
        self.closed.emit()
        super().closeEvent(event)

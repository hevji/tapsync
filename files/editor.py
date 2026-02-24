"""
editor.py — Visual drag-and-drop layout editor.

Features:
  - Drag keys to reposition
  - Snap-to-grid toggle
  - Click key to select and edit properties in side panel
  - Add / delete keys
  - Per-key colour, label, size, radius overrides
"""

import copy
import logging
import uuid

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (QColor, QPainter, QPen, QBrush, QFont,
                          QFontMetrics, QCursor)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QSpinBox, QCheckBox, QColorDialog,
    QSizePolicy, QScrollArea, QFrame, QGroupBox, QFormLayout,
    QSplitter
)

log = logging.getLogger("editor")

UNIT = 44
GAP  = 4
KH   = 44
PAD  = 10
GRID = 44


def _hex(color, fallback="#2a2a3a"):
    if color:
        try:
            return QColor(color)
        except Exception:
            pass
    return QColor(fallback)


class EditorCanvas(QWidget):
    """The main drag canvas for placing / moving keys."""

    selection_changed = pyqtSignal(object)   # emits selected key dict or None
    layout_changed    = pyqtSignal()

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self._theme   = theme
        self._keys    = []
        self._selected: dict | None = None
        self._drag_key: dict | None = None
        self._drag_offset = QPointF(0, 0)
        self._snap = theme.get("snap_to_grid", True)
        self._grid = theme.get("grid_size", GRID)
        self._show_grid = theme.get("grid_visible", True)

        self.setMinimumSize(900, 500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        log.debug("EditorCanvas initialised")

    # ── Units → pixels ────────────────────────────────────────────────────────

    def _unit(self):
        return self._theme.get("key_unit_px", UNIT)

    def _gap(self):
        return self._theme.get("key_gap_px", GAP)

    def _kh(self):
        return self._theme.get("key_height_px", KH)

    def _key_rect(self, k) -> QRectF:
        u = self._unit(); g = self._gap(); kh = self._kh()
        px = PAD + k["x"] * (u + g)
        py = PAD + k["y"] * (kh + g)
        pw = k["w"] * u + (k["w"] - 1) * g
        ph = k["h"] * kh + (k["h"] - 1) * g
        return QRectF(px, py, pw, ph)

    def _snap_pos(self, x, y):
        if not self._snap:
            return x, y
        u = self._unit(); g = self._gap(); kh = self._kh()
        gx = u + g
        gy = kh + g
        sx = round(x / gx)
        sy = round(y / gy)
        return sx, sy

    # ── Public API ────────────────────────────────────────────────────────────

    def load_keys(self, keys: list):
        self._keys = copy.deepcopy(keys)
        self._selected = None
        self.selection_changed.emit(None)
        self.update()
        self._resize_to_fit()
        log.debug("EditorCanvas loaded %d keys", len(self._keys))

    def get_keys(self) -> list:
        return copy.deepcopy(self._keys)

    def set_theme(self, theme: dict):
        self._theme = theme
        self._snap = theme.get("snap_to_grid", True)
        self._grid = theme.get("grid_size", GRID)
        self._show_grid = theme.get("grid_visible", True)
        self.update()

    def set_snap(self, snap: bool):
        self._snap = snap
        log.debug("Snap-to-grid: %s", snap)

    def set_show_grid(self, show: bool):
        self._show_grid = show
        self.update()

    def add_key(self):
        new_id = f"key_{uuid.uuid4().hex[:6]}"
        k = {
            "id": new_id, "label": "New",
            "x": 0.0, "y": 9.0, "w": 1.0, "h": 1.0,
            "color": None, "text_color": None,
        }
        self._keys.append(k)
        self._selected = k
        self.selection_changed.emit(k)
        self.layout_changed.emit()
        self.update()
        log.info("Added new key: %s", new_id)

    def delete_selected(self):
        if self._selected is None:
            return
        kid = self._selected["id"]
        self._keys = [k for k in self._keys if k["id"] != kid]
        self._selected = None
        self.selection_changed.emit(None)
        self.layout_changed.emit()
        self.update()
        log.info("Deleted key: %s", kid)

    def update_selected(self, updates: dict):
        if self._selected is None:
            return
        for key, val in updates.items():
            self._selected[key] = val
        self.layout_changed.emit()
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        t = self._theme
        rad = t.get("key_radius", 6)
        font = QFont(t.get("font_family", "Consolas"), t.get("font_size", 10))
        if t.get("font_bold", True):
            font.setBold(True)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background
        p.fillRect(self.rect(), QColor(t.get("bg", "#111111")))

        # Grid
        if self._show_grid:
            p.setPen(QPen(QColor("#2a2a3a"), 1))
            u = self._unit(); g = self._gap(); kh = self._kh()
            gx = u + g; gy = kh + g
            for xi in range(0, self.width() // gx + 1):
                x = PAD + xi * gx
                p.drawLine(int(x), 0, int(x), self.height())
            for yi in range(0, self.height() // gy + 1):
                y = PAD + yi * gy
                p.drawLine(0, int(y), self.width(), int(y))

        # Keys
        p.setFont(font)
        for k in self._keys:
            rect = self._key_rect(k)
            selected = (k is self._selected)

            if k.get("color"):
                bg = _hex(k["color"])
            else:
                bg = _hex(t.get("key_idle", "#2a2a3a"))

            if selected:
                ol = QColor("#ffffff")
                ol_w = 2
            else:
                ol = _hex(t.get("key_outline", "#444466"))
                ol_w = 1

            p.setBrush(QBrush(bg))
            p.setPen(QPen(ol, ol_w))
            p.drawRoundedRect(rect, rad, rad)

            tc = _hex(k.get("text_color") or t.get("key_text", "#ffffff"))
            p.setPen(QPen(tc))
            draw_font = font
            if len(k.get("label", "")) > 5:
                sf = QFont(font)
                sf.setPointSize(max(6, t.get("font_size", 10) - 2))
                p.setFont(sf)
                draw_font = sf
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, k.get("label", k["id"]))
            if draw_font is not font:
                p.setFont(font)

        p.end()

    # ── Mouse interaction ─────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            hit = self._key_at(pos)
            if hit:
                self._selected = hit
                self._drag_key = hit
                rect = self._key_rect(hit)
                self._drag_offset = QPointF(pos.x() - rect.x(), pos.y() - rect.y())
                self.selection_changed.emit(hit)
            else:
                self._selected = None
                self.selection_changed.emit(None)
            self.update()

    def mouseMoveEvent(self, event):
        if self._drag_key and event.buttons() & Qt.MouseButton.LeftButton:
            pos = event.position()
            u = self._unit(); g = self._gap(); kh = self._kh()
            raw_x = (pos.x() - self._drag_offset.x() - PAD) / (u + g)
            raw_y = (pos.y() - self._drag_offset.y() - PAD) / (kh + g)
            sx, sy = self._snap_pos(raw_x, raw_y)
            self._drag_key["x"] = max(0.0, float(sx) if self._snap else max(0.0, raw_x))
            self._drag_key["y"] = max(0.0, float(sy) if self._snap else max(0.0, raw_y))
            self.layout_changed.emit()
            self.selection_changed.emit(self._drag_key)
            self.update()
            self._resize_to_fit()

    def mouseReleaseEvent(self, event):
        self._drag_key = None

    def _key_at(self, pos: QPointF) -> dict | None:
        for k in reversed(self._keys):
            if self._key_rect(k).contains(pos):
                return k
        return None

    def _resize_to_fit(self):
        if not self._keys:
            return
        u = self._unit(); g = self._gap(); kh = self._kh()
        max_x = max(PAD + k["x"] * (u+g) + k["w"] * u + (k["w"]-1)*g for k in self._keys)
        max_y = max(PAD + k["y"] * (kh+g) + k["h"] * kh + (k["h"]-1)*g for k in self._keys)
        self.setMinimumSize(int(max_x) + PAD*4, int(max_y) + PAD*4)


# ── Properties panel ─────────────────────────────────────────────────────────

class KeyPropertiesPanel(QWidget):
    """Side panel for editing the selected key's properties."""

    changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key: dict | None = None
        self._building = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._title = QLabel("No key selected")
        self._title.setStyleSheet("font-weight:bold; font-size:13px;")
        layout.addWidget(self._title)

        grp = QGroupBox("Key Properties")
        form = QFormLayout(grp)

        self._id     = QLineEdit(); self._id.setPlaceholderText("pynput key id")
        self._label  = QLineEdit(); self._label.setPlaceholderText("Display label")
        self._x      = QDoubleSpinBox(); self._x.setRange(0, 100); self._x.setSingleStep(0.25)
        self._y      = QDoubleSpinBox(); self._y.setRange(0, 100); self._y.setSingleStep(0.25)
        self._w      = QDoubleSpinBox(); self._w.setRange(0.5, 20); self._w.setSingleStep(0.25)
        self._h      = QDoubleSpinBox(); self._h.setRange(0.5, 10); self._h.setSingleStep(0.25)

        form.addRow("ID:",     self._id)
        form.addRow("Label:",  self._label)
        form.addRow("X (u):",  self._x)
        form.addRow("Y (row):", self._y)
        form.addRow("Width:",  self._w)
        form.addRow("Height:", self._h)

        # Colour buttons
        self._col_btn  = QPushButton("Set colour…")
        self._col_btn.setToolTip("Per-key idle background colour")
        self._col_clear = QPushButton("Clear colour")
        self._txt_btn  = QPushButton("Set text colour…")
        self._txt_clear = QPushButton("Clear text colour")

        form.addRow("Bg colour:", self._col_btn)
        form.addRow("",           self._col_clear)
        form.addRow("Text colour:", self._txt_btn)
        form.addRow("",            self._txt_clear)

        layout.addWidget(grp)
        layout.addStretch()

        # Wire signals
        for w in (self._id, self._label):
            w.textChanged.connect(self._emit)
        for w in (self._x, self._y, self._w, self._h):
            w.valueChanged.connect(self._emit)
        self._col_btn.clicked.connect(self._pick_color)
        self._col_clear.clicked.connect(lambda: self._clear_color("color"))
        self._txt_btn.clicked.connect(self._pick_text_color)
        self._txt_clear.clicked.connect(lambda: self._clear_color("text_color"))

        self.setEnabled(False)

    def load_key(self, k: dict | None):
        self._key = k
        self._building = True
        if k is None:
            self._title.setText("No key selected")
            self.setEnabled(False)
        else:
            self._title.setText(f"Key: {k['id']}")
            self.setEnabled(True)
            self._id.setText(k.get("id", ""))
            self._label.setText(k.get("label", ""))
            self._x.setValue(k.get("x", 0))
            self._y.setValue(k.get("y", 0))
            self._w.setValue(k.get("w", 1.0))
            self._h.setValue(k.get("h", 1.0))
            self._update_color_buttons(k)
        self._building = False

    def _update_color_buttons(self, k):
        c = k.get("color")
        tc = k.get("text_color")
        style = f"background:{c};" if c else ""
        self._col_btn.setStyleSheet(style)
        tstyle = f"background:{tc};" if tc else ""
        self._txt_btn.setStyleSheet(tstyle)

    def _emit(self):
        if self._building or self._key is None:
            return
        updates = {
            "id":         self._id.text().strip(),
            "label":      self._label.text(),
            "x":          self._x.value(),
            "y":          self._y.value(),
            "w":          self._w.value(),
            "h":          self._h.value(),
        }
        self.changed.emit(updates)

    def _pick_color(self):
        if self._key is None:
            return
        c = QColorDialog.getColor(QColor(self._key.get("color") or "#2a2a3a"), self)
        if c.isValid():
            self._key["color"] = c.name()
            self._update_color_buttons(self._key)
            self.changed.emit({"color": c.name()})

    def _pick_text_color(self):
        if self._key is None:
            return
        c = QColorDialog.getColor(QColor(self._key.get("text_color") or "#ffffff"), self)
        if c.isValid():
            self._key["text_color"] = c.name()
            self._update_color_buttons(self._key)
            self.changed.emit({"text_color": c.name()})

    def _clear_color(self, field):
        if self._key is None:
            return
        self._key[field] = None
        self._update_color_buttons(self._key)
        self.changed.emit({field: None})


# ── Full editor tab ───────────────────────────────────────────────────────────

class EditorTab(QWidget):
    layout_saved = pyqtSignal(list)   # emits key list when user clicks Save

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        # Toolbar
        toolbar = QHBoxLayout()
        self._snap_cb = QCheckBox("Snap to grid")
        self._snap_cb.setChecked(self._theme.get("snap_to_grid", True))
        self._grid_cb = QCheckBox("Show grid")
        self._grid_cb.setChecked(self._theme.get("grid_visible", True))
        btn_add = QPushButton("+ Add Key")
        btn_del = QPushButton("✕ Delete Key")
        btn_save = QPushButton("💾 Save Layout")
        btn_save.setStyleSheet("font-weight:bold;")

        toolbar.addWidget(self._snap_cb)
        toolbar.addWidget(self._grid_cb)
        toolbar.addStretch()
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_del)
        toolbar.addWidget(btn_save)
        root.addLayout(toolbar)

        # Splitter: canvas | properties
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Scrollable canvas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.canvas = EditorCanvas(self._theme)
        scroll.setWidget(self.canvas)
        splitter.addWidget(scroll)

        # Properties panel
        self.props = KeyPropertiesPanel()
        self.props.setMaximumWidth(260)
        self.props.setMinimumWidth(220)
        splitter.addWidget(self.props)
        splitter.setSizes([700, 240])

        root.addWidget(splitter)

        # Wire
        self._snap_cb.toggled.connect(self.canvas.set_snap)
        self._grid_cb.toggled.connect(self.canvas.set_show_grid)
        btn_add.clicked.connect(self.canvas.add_key)
        btn_del.clicked.connect(self.canvas.delete_selected)
        btn_save.clicked.connect(self._on_save)
        self.canvas.selection_changed.connect(self.props.load_key)
        self.props.changed.connect(self.canvas.update_selected)

    def load_keys(self, keys: list):
        self.canvas.load_keys(keys)

    def set_theme(self, theme: dict):
        self._theme = theme
        self.canvas.set_theme(theme)

    def _on_save(self):
        keys = self.canvas.get_keys()
        self.layout_saved.emit(keys)
        log.info("Editor: layout saved (%d keys)", len(keys))

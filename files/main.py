"""
main.py — Main PyQt6 application.

Tabs:
  1. Overlay   — live preview controls, show/hide overlay
  2. Presets   — built-in and saved layout browser
  3. Editor    — drag-and-drop layout editor
  4. Theme     — global appearance settings
  5. About

Run:
  pip install PyQt6 pynput
  python main.py
"""

import copy
import logging
import sys
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSlider, QSpinBox,
    QDoubleSpinBox, QCheckBox, QLineEdit, QGroupBox,
    QFormLayout, QColorDialog, QMessageBox, QInputDialog,
    QFileDialog, QSplitter, QScrollArea, QComboBox,
    QSizePolicy, QFrame, QTextEdit
)

from config   import (load_settings, save_settings, list_configs, load_config,
                       save_config, delete_config, rename_config, duplicate_config,
                       export_config, import_config, preset_to_config, DEFAULT_THEME)
from presets  import BUILTIN_PRESETS
from overlay  import OverlayWindow
from editor   import EditorTab
from listener import InputListener

# ── Logging setup ─────────────────────────────────────────────────────────────

class QtLogHandler(logging.Handler):
    """Pushes log records into a QTextEdit."""
    def __init__(self, widget: QTextEdit):
        super().__init__()
        self._w = widget
        fmt = logging.Formatter("[%(levelname)s] %(name)s — %(message)s")
        self.setFormatter(fmt)

    def emit(self, record):
        msg = self.format(record)
        color = {
            "DEBUG":    "#888888",
            "INFO":     "#aaddff",
            "WARNING":  "#ffcc44",
            "ERROR":    "#ff6666",
            "CRITICAL": "#ff2222",
        }.get(record.levelname, "#ffffff")
        html = f'<span style="color:{color};">{msg}</span>'
        # Must run on main thread
        try:
            self._w.append(html)
        except RuntimeError:
            pass


def setup_logging(log_widget: QTextEdit):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(name)s — %(message)s"))
    root.addHandler(ch)
    # Widget handler
    wh = QtLogHandler(log_widget)
    wh.setLevel(logging.DEBUG)
    root.addHandler(wh)


log = logging.getLogger("main")


# ── Key event bridge (thread-safe) ────────────────────────────────────────────

class KeyBridge(QObject):
    key_event = pyqtSignal(str, bool)


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keyboard Overlay — Control Panel")
        self.resize(960, 680)

        self._settings  = load_settings()
        self._theme     = self._settings.get("theme", dict(DEFAULT_THEME))
        self._overlay: OverlayWindow | None = None
        self._current_keys: list = copy.deepcopy(BUILTIN_PRESETS[0]["keys"])
        self._current_name: str = BUILTIN_PRESETS[0]["name"]

        # Log widget must exist before setup_logging
        self._log_widget = QTextEdit()
        self._log_widget.setReadOnly(True)
        self._log_widget.setStyleSheet(
            "background:#0a0a0a; color:#aaaaaa; font-family:Consolas; font-size:10px;"
        )

        setup_logging(self._log_widget)
        log.info("Application starting")

        # Key bridge for thread-safe overlay updates
        self._bridge = KeyBridge()
        self._bridge.key_event.connect(self._on_key_event)

        self._listener = InputListener(callback=self._listener_cb)

        self._build_ui()
        self._refresh_config_list()

        # Start listener
        try:
            self._listener.start()
        except Exception as e:
            log.error("Could not start input listener: %s", e)

        # Restore last config
        last = self._settings.get("last_config")
        if last:
            data = load_config(last)
            if data:
                self._load_layout(data["keys"], last)
                log.info("Restored last config: %s", last)

        log.info("Application ready")

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        vbox.addWidget(self._tabs)

        self._tabs.addTab(self._build_overlay_tab(),  "🖥  Overlay")
        self._tabs.addTab(self._build_presets_tab(),  "📋  Presets")
        self._tabs.addTab(self._build_editor_tab(),   "✏️  Editor")
        self._tabs.addTab(self._build_theme_tab(),    "🎨  Theme")
        self._tabs.addTab(self._build_log_tab(),      "📜  Log")

        # Apply dark theme to main window
        self.setStyleSheet("""
            QMainWindow, QWidget { background:#1e1e2e; color:#e0e0ff; }
            QTabWidget::pane { border:1px solid #444466; }
            QTabBar::tab { background:#2a2a3a; color:#aaaacc; padding:6px 14px; }
            QTabBar::tab:selected { background:#3a3a5a; color:#ffffff; }
            QPushButton {
                background:#3a3a5a; color:#e0e0ff; border:1px solid #555577;
                padding:4px 10px; border-radius:4px;
            }
            QPushButton:hover { background:#4a4a7a; }
            QPushButton:pressed { background:#7b68ee; }
            QListWidget { background:#161626; border:1px solid #333355; }
            QListWidget::item:selected { background:#3a3a6a; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background:#161626; border:1px solid #333355;
                color:#e0e0ff; padding:2px 4px; border-radius:3px;
            }
            QGroupBox { border:1px solid #333355; border-radius:4px;
                        margin-top:8px; padding-top:4px; }
            QGroupBox::title { color:#aaaacc; }
            QCheckBox { color:#e0e0ff; }
            QLabel { color:#e0e0ff; }
            QScrollBar:vertical { background:#1a1a2a; width:10px; }
            QScrollBar::handle:vertical { background:#444466; border-radius:4px; }
            QSplitter::handle { background:#333355; }
        """)

    # ── Overlay tab ───────────────────────────────────────────────────────────

    def _build_overlay_tab(self):
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setSpacing(12)

        # Status bar
        status_box = QHBoxLayout()
        self._status_lbl = QLabel("Overlay: Hidden")
        self._status_lbl.setStyleSheet("font-size:13px; font-weight:bold;")
        self._btn_toggle = QPushButton("▶ Show Overlay")
        self._btn_toggle.setStyleSheet("font-weight:bold; font-size:13px; padding:6px 20px;")
        self._btn_toggle.clicked.connect(self._toggle_overlay)
        status_box.addWidget(self._status_lbl)
        status_box.addStretch()
        status_box.addWidget(self._btn_toggle)
        vbox.addLayout(status_box)

        # Current layout
        cur_box = QGroupBox("Current Layout")
        cur_form = QFormLayout(cur_box)
        self._cur_name_lbl = QLabel(self._current_name)
        self._cur_name_lbl.setStyleSheet("font-weight:bold;")
        cur_form.addRow("Loaded:", self._cur_name_lbl)
        vbox.addWidget(cur_box)

        # Opacity slider
        alpha_box = QGroupBox("Overlay Opacity")
        alpha_layout = QHBoxLayout(alpha_box)
        self._alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self._alpha_slider.setRange(20, 100)
        self._alpha_slider.setValue(int(self._theme.get("overlay_alpha", 0.93) * 100))
        self._alpha_val = QLabel(f"{self._alpha_slider.value()}%")
        self._alpha_slider.valueChanged.connect(self._on_alpha_changed)
        alpha_layout.addWidget(self._alpha_slider)
        alpha_layout.addWidget(self._alpha_val)
        vbox.addWidget(alpha_box)

        # Scale slider
        scale_box = QGroupBox("Key Size (unit px)")
        scale_layout = QHBoxLayout(scale_box)
        self._scale_spin = QSpinBox()
        self._scale_spin.setRange(20, 80)
        self._scale_spin.setValue(self._theme.get("key_unit_px", 44))
        self._scale_spin.valueChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(QLabel("1u ="))
        scale_layout.addWidget(self._scale_spin)
        scale_layout.addWidget(QLabel("px"))
        scale_layout.addStretch()
        vbox.addWidget(scale_box)

        # OBS tip
        tip = QLabel(
            "💡 OBS: Add <b>Window Capture</b> → select <i>Keyboard Overlay</i> "
            "→ enable <b>Allow Transparency</b>."
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color:#888899; font-size:11px; padding:8px;")
        vbox.addWidget(tip)
        vbox.addStretch()
        return w

    # ── Presets tab ───────────────────────────────────────────────────────────

    def _build_presets_tab(self):
        w = QWidget()
        vbox = QVBoxLayout(w)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Built-in presets
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.addWidget(QLabel("Built-in Presets"))
        self._preset_list = QListWidget()
        for p in BUILTIN_PRESETS:
            self._preset_list.addItem(QListWidgetItem(p["name"]))
        lv.addWidget(self._preset_list)
        btn_load_preset = QPushButton("Load Preset")
        btn_save_as     = QPushButton("Save as Config…")
        lv.addWidget(btn_load_preset)
        lv.addWidget(btn_save_as)
        splitter.addWidget(left)

        # Saved configs
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.addWidget(QLabel("Saved Configs"))
        self._config_list = QListWidget()
        rv.addWidget(self._config_list)
        btn_row = QHBoxLayout()
        btn_load_cfg  = QPushButton("Load")
        btn_rename    = QPushButton("Rename")
        btn_dup       = QPushButton("Duplicate")
        btn_del_cfg   = QPushButton("Delete")
        btn_export    = QPushButton("Export…")
        btn_import    = QPushButton("Import…")
        for b in (btn_load_cfg, btn_rename, btn_dup, btn_del_cfg, btn_export, btn_import):
            btn_row.addWidget(b)
        rv.addLayout(btn_row)
        splitter.addWidget(right)

        vbox.addWidget(splitter)

        # Wire
        btn_load_preset.clicked.connect(self._load_selected_preset)
        btn_save_as.clicked.connect(self._save_preset_as_config)
        btn_load_cfg.clicked.connect(self._load_selected_config)
        btn_rename.clicked.connect(self._rename_config)
        btn_dup.clicked.connect(self._duplicate_config)
        btn_del_cfg.clicked.connect(self._delete_config)
        btn_export.clicked.connect(self._export_config)
        btn_import.clicked.connect(self._import_config)

        return w

    # ── Editor tab ────────────────────────────────────────────────────────────

    def _build_editor_tab(self):
        self._editor = EditorTab(self._theme)
        self._editor.load_keys(self._current_keys)
        self._editor.layout_saved.connect(self._on_editor_save)
        return self._editor

    # ── Theme tab ─────────────────────────────────────────────────────────────

    def _build_theme_tab(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        vbox = QVBoxLayout(inner)
        vbox.setSpacing(8)

        def color_row(label, key):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(160)
            btn = QPushButton()
            btn.setFixedWidth(80)
            val = self._theme.get(key, "#ffffff")
            btn.setStyleSheet(f"background:{val};")
            btn.setText(val)
            def pick(checked=False, k=key, b=btn):
                c = QColorDialog.getColor(QColor(self._theme.get(k, "#ffffff")), self)
                if c.isValid():
                    self._theme[k] = c.name()
                    b.setStyleSheet(f"background:{c.name()};")
                    b.setText(c.name())
                    self._apply_theme()
            btn.clicked.connect(pick)
            row.addWidget(lbl)
            row.addWidget(btn)
            row.addStretch()
            return row

        # Colour section
        col_grp = QGroupBox("Colours")
        cgl = QVBoxLayout(col_grp)
        for label, key in [
            ("Background",         "bg"),
            ("Key Idle",           "key_idle"),
            ("Key Pressed",        "key_pressed"),
            ("Mouse Idle",         "mouse_idle"),
            ("Mouse Pressed",      "mouse_pressed"),
            ("Key Text",           "key_text"),
            ("Key Outline",        "key_outline"),
        ]:
            cgl.addLayout(color_row(label, key))
        vbox.addWidget(col_grp)

        # Font section
        font_grp = QGroupBox("Font")
        fgl = QFormLayout(font_grp)
        self._font_family = QLineEdit(self._theme.get("font_family", "Consolas"))
        self._font_size   = QSpinBox(); self._font_size.setRange(6, 24)
        self._font_size.setValue(self._theme.get("font_size", 10))
        self._font_bold   = QCheckBox("Bold")
        self._font_bold.setChecked(self._theme.get("font_bold", True))
        fgl.addRow("Family:", self._font_family)
        fgl.addRow("Size:",   self._font_size)
        fgl.addRow("",        self._font_bold)
        self._font_family.textChanged.connect(lambda v: self._set_theme("font_family", v))
        self._font_size.valueChanged.connect(lambda v: self._set_theme("font_size", v))
        self._font_bold.toggled.connect(lambda v: self._set_theme("font_bold", v))
        vbox.addWidget(font_grp)

        # Key geometry section
        geom_grp = QGroupBox("Key Geometry")
        ggl = QFormLayout(geom_grp)

        self._key_radius = QSpinBox(); self._key_radius.setRange(0, 22)
        self._key_radius.setValue(self._theme.get("key_radius", 6))
        self._key_radius.setToolTip("Corner rounding radius in pixels (0 = sharp corners)")

        self._key_unit   = QSpinBox(); self._key_unit.setRange(20, 80)
        self._key_unit.setValue(self._theme.get("key_unit_px", 44))

        self._key_height = QSpinBox(); self._key_height.setRange(20, 80)
        self._key_height.setValue(self._theme.get("key_height_px", 44))

        self._key_gap    = QSpinBox(); self._key_gap.setRange(0, 20)
        self._key_gap.setValue(self._theme.get("key_gap_px", 4))

        ggl.addRow("Corner Radius (px):", self._key_radius)
        ggl.addRow("Key Width 1u (px):",  self._key_unit)
        ggl.addRow("Key Height (px):",    self._key_height)
        ggl.addRow("Gap (px):",           self._key_gap)

        self._key_radius.valueChanged.connect(lambda v: self._set_theme("key_radius", v))
        self._key_unit.valueChanged.connect(lambda v: self._set_theme("key_unit_px", v))
        self._key_height.valueChanged.connect(lambda v: self._set_theme("key_height_px", v))
        self._key_gap.valueChanged.connect(lambda v: self._set_theme("key_gap_px", v))
        vbox.addWidget(geom_grp)

        # Editor grid
        grid_grp = QGroupBox("Editor Grid")
        grl = QFormLayout(grid_grp)
        self._grid_size  = QSpinBox(); self._grid_size.setRange(10, 100)
        self._grid_size.setValue(self._theme.get("grid_size", 44))
        self._snap_default = QCheckBox("Snap by default")
        self._snap_default.setChecked(self._theme.get("snap_to_grid", True))
        self._grid_vis = QCheckBox("Show grid by default")
        self._grid_vis.setChecked(self._theme.get("grid_visible", True))
        grl.addRow("Grid size (px):", self._grid_size)
        grl.addRow("", self._snap_default)
        grl.addRow("", self._grid_vis)
        self._grid_size.valueChanged.connect(lambda v: self._set_theme("grid_size", v))
        self._snap_default.toggled.connect(lambda v: self._set_theme("snap_to_grid", v))
        self._grid_vis.toggled.connect(lambda v: self._set_theme("grid_visible", v))
        vbox.addWidget(grid_grp)

        # Reset button
        btn_reset = QPushButton("Reset to Defaults")
        btn_reset.clicked.connect(self._reset_theme)
        vbox.addWidget(btn_reset)
        vbox.addStretch()

        scroll.setWidget(inner)
        outer = QVBoxLayout(w)
        outer.addWidget(scroll)
        return w

    # ── Log tab ───────────────────────────────────────────────────────────────

    def _build_log_tab(self):
        w = QWidget()
        vbox = QVBoxLayout(w)
        btn_clear = QPushButton("Clear Log")
        btn_clear.setMaximumWidth(100)
        btn_clear.clicked.connect(self._log_widget.clear)
        vbox.addWidget(btn_clear)
        vbox.addWidget(self._log_widget)
        return w

    # ── Overlay control ───────────────────────────────────────────────────────

    def _toggle_overlay(self):
        if self._overlay is None or not self._overlay.isVisible():
            self._show_overlay()
        else:
            self._hide_overlay()

    def _show_overlay(self):
        if self._overlay is not None:
            try:
                self._overlay.close()
            except Exception:
                pass
        try:
            self._overlay = OverlayWindow(self._current_keys, self._theme)
            x = self._settings.get("overlay_x", 100)
            y = self._settings.get("overlay_y", 100)
            self._overlay.move(x, y)
            self._overlay.show()
            self._overlay.closed.connect(self._on_overlay_closed)
            self._btn_toggle.setText("⏹ Hide Overlay")
            self._status_lbl.setText("Overlay: Visible ✓")
            log.info("Overlay shown")
        except Exception as e:
            log.error("Failed to show overlay: %s", e)

    def _hide_overlay(self):
        if self._overlay:
            pos = self._overlay.pos()
            self._settings["overlay_x"] = pos.x()
            self._settings["overlay_y"] = pos.y()
            self._overlay.close()
            self._overlay = None
        self._btn_toggle.setText("▶ Show Overlay")
        self._status_lbl.setText("Overlay: Hidden")
        log.info("Overlay hidden")

    def _on_overlay_closed(self):
        self._overlay = None
        self._btn_toggle.setText("▶ Show Overlay")
        self._status_lbl.setText("Overlay: Hidden")

    # ── Key events ────────────────────────────────────────────────────────────

    def _listener_cb(self, key_id: str, pressed: bool):
        """Called from pynput thread — forward to main thread."""
        self._bridge.key_event.emit(key_id, pressed)

    @pyqtSlot(str, bool)
    def _on_key_event(self, key_id: str, pressed: bool):
        if self._overlay and self._overlay.isVisible():
            self._overlay.update_key(key_id, pressed)

    # ── Layout loading ────────────────────────────────────────────────────────

    def _load_layout(self, keys: list, name: str):
        self._current_keys = copy.deepcopy(keys)
        self._current_name = name
        self._cur_name_lbl.setText(name)
        self._editor.load_keys(self._current_keys)
        if self._overlay and self._overlay.isVisible():
            self._overlay.load_keys(self._current_keys)
        log.info("Layout loaded: %s (%d keys)", name, len(keys))

    # ── Preset actions ────────────────────────────────────────────────────────

    def _load_selected_preset(self):
        row = self._preset_list.currentRow()
        if row < 0:
            log.warning("No preset selected")
            return
        preset = BUILTIN_PRESETS[row]
        self._load_layout(preset["keys"], preset["name"])

    def _save_preset_as_config(self):
        row = self._preset_list.currentRow()
        if row < 0:
            return
        preset = BUILTIN_PRESETS[row]
        name, ok = QInputDialog.getText(self, "Save Config", "Config name:", text=preset["name"])
        if not ok or not name.strip():
            return
        name = name.strip()
        cfg = preset_to_config(preset)
        if save_config(name, cfg):
            self._refresh_config_list()
            log.info("Preset saved as config: %s", name)
        else:
            QMessageBox.warning(self, "Error", f"Could not save config '{name}'.")

    # ── Config actions ────────────────────────────────────────────────────────

    def _refresh_config_list(self):
        self._config_list.clear()
        for name in list_configs():
            self._config_list.addItem(QListWidgetItem(name))
        log.debug("Config list refreshed")

    def _selected_config_name(self) -> str | None:
        item = self._config_list.currentItem()
        return item.text() if item else None

    def _load_selected_config(self):
        name = self._selected_config_name()
        if not name:
            log.warning("No config selected")
            return
        data = load_config(name)
        if data:
            self._load_layout(data["keys"], name)
            self._settings["last_config"] = name
            save_settings(self._settings)

    def _rename_config(self):
        name = self._selected_config_name()
        if not name:
            return
        new, ok = QInputDialog.getText(self, "Rename Config", "New name:", text=name)
        if ok and new.strip() and new.strip() != name:
            if rename_config(name, new.strip()):
                self._refresh_config_list()

    def _duplicate_config(self):
        name = self._selected_config_name()
        if not name:
            return
        new, ok = QInputDialog.getText(self, "Duplicate Config", "New name:", text=f"{name} copy")
        if ok and new.strip():
            if duplicate_config(name, new.strip()):
                self._refresh_config_list()

    def _delete_config(self):
        name = self._selected_config_name()
        if not name:
            return
        reply = QMessageBox.question(
            self, "Delete Config", f"Delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if delete_config(name):
                self._refresh_config_list()

    def _export_config(self):
        name = self._selected_config_name()
        if not name:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Config", f"{name}.json", "JSON (*.json)")
        if path:
            export_config(name, path)

    def _import_config(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Config", "", "JSON (*.json)")
        if path:
            new_name = import_config(path)
            if new_name:
                self._refresh_config_list()

    # ── Editor save ───────────────────────────────────────────────────────────

    def _on_editor_save(self, keys: list):
        name, ok = QInputDialog.getText(
            self, "Save Layout", "Config name:", text=self._current_name
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        cfg = {"name": name, "layout": "custom", "keys": keys}
        if save_config(name, cfg):
            self._load_layout(keys, name)
            self._refresh_config_list()
            self._settings["last_config"] = name
            save_settings(self._settings)

    # ── Theme helpers ─────────────────────────────────────────────────────────

    def _set_theme(self, key: str, val):
        self._theme[key] = val
        self._apply_theme()

    def _apply_theme(self):
        self._settings["theme"] = self._theme
        save_settings(self._settings)
        self._editor.set_theme(self._theme)
        if self._overlay and self._overlay.isVisible():
            self._overlay.set_theme(self._theme)

    def _on_alpha_changed(self, val: int):
        self._alpha_val.setText(f"{val}%")
        self._theme["overlay_alpha"] = val / 100.0
        if self._overlay:
            self._overlay.setWindowOpacity(val / 100.0)
        self._apply_theme()

    def _on_scale_changed(self, val: int):
        self._theme["key_unit_px"] = val
        self._apply_theme()

    def _reset_theme(self):
        reply = QMessageBox.question(
            self, "Reset Theme", "Reset all theme settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._theme = dict(DEFAULT_THEME)
            self._apply_theme()
            log.info("Theme reset to defaults")
            QMessageBox.information(self, "Theme Reset", "Theme reset. Restart the app to refresh all controls.")

    # ── Close ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self._overlay:
            pos = self._overlay.pos()
            self._settings["overlay_x"] = pos.x()
            self._settings["overlay_y"] = pos.y()
        self._settings["theme"] = self._theme
        save_settings(self._settings)
        if self._listener:
            self._listener.stop()
        log.info("Application closing")
        event.accept()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Base dark palette so Qt widgets don't flash white before CSS loads
    from PyQt6.QtGui import QPalette
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#1e1e2e"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#e0e0ff"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#161626"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#e0e0ff"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#2a2a3a"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#e0e0ff"))
    app.setPalette(pal)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

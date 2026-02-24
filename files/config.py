"""
config.py — Save / load overlay configs as JSON.

Storage location:
  Windows : %APPDATA%/KeyboardOverlay/configs/
  macOS   : ~/Library/Application Support/KeyboardOverlay/configs/
  Linux   : ~/.config/KeyboardOverlay/configs/

Theme / global settings are stored in settings.json in the same base dir.
"""

import json
import logging
import os
import platform
import shutil
from pathlib import Path

log = logging.getLogger("config")

APP_NAME = "KeyboardOverlay"

# ── Default theme ─────────────────────────────────────────────────────────────

DEFAULT_THEME = {
    "bg":              "#111111",
    "key_idle":        "#2a2a3a",
    "key_pressed":     "#7b68ee",
    "mouse_idle":      "#1e3a5f",
    "mouse_pressed":   "#1e90ff",
    "key_text":        "#ffffff",
    "key_outline":     "#444466",
    "font_family":     "Consolas",
    "font_size":       10,
    "font_bold":       True,
    "key_radius":      6,       # px — corner rounding
    "key_unit_px":     44,      # px per 1u
    "key_gap_px":      4,       # px gap between keys
    "key_height_px":   44,
    "overlay_alpha":   0.93,
    "grid_size":       44,      # editor snap grid in px
    "grid_visible":    True,
    "snap_to_grid":    True,
}

DEFAULT_SETTINGS = {
    "theme": DEFAULT_THEME,
    "last_config": None,
    "overlay_x": 100,
    "overlay_y": 100,
}


def get_app_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    p = base / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    log.debug("App dir: %s", p)
    return p


def get_configs_dir() -> Path:
    p = get_app_dir() / "configs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_settings_path() -> Path:
    return get_app_dir() / "settings.json"


# ── Settings ──────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    path = get_settings_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge missing keys from defaults
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            merged["theme"] = dict(DEFAULT_THEME)
            merged["theme"].update(data.get("theme", {}))
            log.info("Settings loaded from %s", path)
            return merged
        except Exception as e:
            log.error("Failed to load settings: %s — using defaults", e)
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict):
    path = get_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        log.info("Settings saved to %s", path)
    except Exception as e:
        log.error("Failed to save settings: %s", e)


# ── Layout configs ────────────────────────────────────────────────────────────

def list_configs() -> list[str]:
    """Return list of config names (no extension)."""
    d = get_configs_dir()
    names = sorted(p.stem for p in d.glob("*.json"))
    log.debug("Found %d configs: %s", len(names), names)
    return names


def load_config(name: str) -> dict | None:
    path = get_configs_dir() / f"{name}.json"
    if not path.exists():
        log.warning("Config not found: %s", path)
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info("Config loaded: %s (%d keys)", name, len(data.get("keys", [])))
        return data
    except Exception as e:
        log.error("Failed to load config '%s': %s", name, e)
        return None


def save_config(name: str, config: dict) -> bool:
    """Save a layout config. Returns True on success."""
    path = get_configs_dir() / f"{name}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        log.info("Config saved: %s", path)
        return True
    except Exception as e:
        log.error("Failed to save config '%s': %s", name, e)
        return False


def delete_config(name: str) -> bool:
    path = get_configs_dir() / f"{name}.json"
    try:
        path.unlink()
        log.info("Config deleted: %s", name)
        return True
    except Exception as e:
        log.error("Failed to delete config '%s': %s", name, e)
        return False


def rename_config(old: str, new: str) -> bool:
    src = get_configs_dir() / f"{old}.json"
    dst = get_configs_dir() / f"{new}.json"
    if dst.exists():
        log.warning("Cannot rename '%s' → '%s': destination exists", old, new)
        return False
    try:
        src.rename(dst)
        log.info("Config renamed: %s → %s", old, new)
        return True
    except Exception as e:
        log.error("Failed to rename config: %s", e)
        return False


def duplicate_config(name: str, new_name: str) -> bool:
    src = get_configs_dir() / f"{name}.json"
    dst = get_configs_dir() / f"{new_name}.json"
    if not src.exists():
        log.warning("Cannot duplicate '%s': not found", name)
        return False
    try:
        shutil.copy2(src, dst)
        log.info("Config duplicated: %s → %s", name, new_name)
        return True
    except Exception as e:
        log.error("Failed to duplicate config: %s", e)
        return False


def export_config(name: str, dest_path: str) -> bool:
    src = get_configs_dir() / f"{name}.json"
    try:
        shutil.copy2(src, dest_path)
        log.info("Config exported: %s → %s", name, dest_path)
        return True
    except Exception as e:
        log.error("Failed to export config: %s", e)
        return False


def import_config(src_path: str) -> str | None:
    """Import a .json file. Returns the config name on success."""
    src = Path(src_path)
    if not src.exists():
        log.warning("Import source not found: %s", src_path)
        return None
    dst = get_configs_dir() / src.name
    try:
        shutil.copy2(src, dst)
        log.info("Config imported: %s", dst)
        return dst.stem
    except Exception as e:
        log.error("Failed to import config: %s", e)
        return None


def preset_to_config(preset: dict) -> dict:
    """Wrap a preset dict into a saveable config dict."""
    import copy
    return {
        "name":   preset["name"],
        "layout": preset.get("layout", "qwerty"),
        "keys":   copy.deepcopy(preset["keys"]),
    }

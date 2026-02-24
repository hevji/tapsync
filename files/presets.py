"""
presets.py — Built-in keyboard layout presets.
Each preset is a dict with:
  - name: display name
  - layout: str layout variant (qwerty / azerty)
  - keys: list of key dicts (see schema below)

Key schema:
  {
    "id":      str   — unique id used for pynput matching
    "label":   str   — display text
    "x":       int   — grid column (or pixel x in free mode)
    "y":       int   — grid row    (or pixel y in free mode)
    "w":       float — width in units
    "h":       float — height in units
    "color":   str | None  — per-key override (None = use theme)
    "text_color": str | None
  }
"""

import logging
log = logging.getLogger("presets")


def _key(kid, label, x, y, w=1.0, h=1.0, color=None, text_color=None):
    return {
        "id": kid, "label": label,
        "x": x, "y": y, "w": w, "h": h,
        "color": color, "text_color": text_color,
    }


# ── QWERTY rows ───────────────────────────────────────────────────────────────

def _qwerty_full():
    keys = []
    # Row 0 – function keys
    row0 = [
        ("esc","Esc"), ("f1","F1"), ("f2","F2"), ("f3","F3"), ("f4","F4"),
        ("f5","F5"), ("f6","F6"), ("f7","F7"), ("f8","F8"),
        ("f9","F9"), ("f10","F10"), ("f11","F11"), ("f12","F12"),
        ("print_screen","Prt"), ("insert","Ins"), ("delete","Del"),
    ]
    x = 0
    for kid, lbl in row0:
        keys.append(_key(kid, lbl, x, 0))
        x += 1

    # Row 1 – numbers
    row1 = [
        ("`","`"), ("1","1"), ("2","2"), ("3","3"), ("4","4"), ("5","5"),
        ("6","6"), ("7","7"), ("8","8"), ("9","9"), ("0","0"),
        ("-","-"), ("=","="),
    ]
    x = 0
    for kid, lbl in row1:
        keys.append(_key(kid, lbl, x, 1))
        x += 1
    keys.append(_key("backspace", "Bksp", x, 1, w=2.0))

    # Row 2 – QWERTY
    keys.append(_key("tab", "Tab", 0, 2, w=1.5))
    row2 = [("q","Q"),("w","W"),("e","E"),("r","R"),("t","T"),
            ("y","Y"),("u","U"),("i","I"),("o","O"),("p","P"),
            ("[","["), ("]","]")]
    x = 1.5
    for kid, lbl in row2:
        keys.append(_key(kid, lbl, x, 2))
        x += 1
    keys.append(_key("\\", "\\", x, 2, w=1.5))

    # Row 3 – ASDF
    keys.append(_key("caps_lock", "Caps", 0, 3, w=1.75))
    row3 = [("a","A"),("s","S"),("d","D"),("f","F"),("g","G"),
            ("h","H"),("j","J"),("k","K"),("l","L"),(";",";"),(  "'","'")]
    x = 1.75
    for kid, lbl in row3:
        keys.append(_key(kid, lbl, x, 3))
        x += 1
    keys.append(_key("enter", "Enter", x, 3, w=2.25))

    # Row 4 – ZXCV
    keys.append(_key("shift", "Shift", 0, 4, w=2.25))
    row4 = [("z","Z"),("x","X"),("c","C"),("v","V"),("b","B"),
            ("n","N"),("m","M"),(",",","),(  ".","."),(  "/","/")]
    x = 2.25
    for kid, lbl in row4:
        keys.append(_key(kid, lbl, x, 4))
        x += 1
    keys.append(_key("shift_r", "Shift", x, 4, w=2.75))

    # Row 5 – bottom
    row5 = [
        ("ctrl_l","Ctrl",0,5,1.25), ("cmd","Win",1.25,5,1.25),
        ("alt_l","Alt",2.5,5,1.25),
        ("space","Space",3.75,5,6.25),
        ("alt_r","Alt",10.0,5,1.25), ("cmd_r","Win",11.25,5,1.25),
        ("ctrl_r","Ctrl",12.5,5,1.25),
    ]
    for kid, lbl, x, y, w in row5:
        keys.append(_key(kid, lbl, x, y, w=w))

    # Mouse
    keys.append(_key("mouse_left",   "LMB", 0, 7, w=1.5, h=1.5, color="#1e3a5f", text_color="#aaddff"))
    keys.append(_key("mouse_middle", "MMB", 1.6, 7, w=1.5, h=1.5, color="#1e3a5f", text_color="#aaddff"))
    keys.append(_key("mouse_right",  "RMB", 3.2, 7, w=1.5, h=1.5, color="#1e3a5f", text_color="#aaddff"))

    return keys


def _qwerty_no_fkeys():
    return [k for k in _qwerty_full() if k["y"] != 0 or k["id"] in ("esc",)]


def _qwerty_left_half():
    """Left half of QWERTY — cols 0..6 approx."""
    keep_ids = {
        "esc","f1","f2","f3","f4","f5",
        "`","1","2","3","4","5","6",
        "tab","q","w","e","r","t",
        "caps_lock","a","s","d","f","g",
        "shift","z","x","c","v","b",
        "ctrl_l","cmd","alt_l","space",
        "mouse_left","mouse_middle","mouse_right",
    }
    return [k for k in _qwerty_full() if k["id"] in keep_ids]


def _gaming_wasd():
    """WASD + surrounding keys + mouse."""
    keep_ids = {
        "esc","1","2","3","4","5",
        "tab","q","w","e","r",
        "caps_lock","a","s","d","f",
        "shift","z","x","c","v",
        "ctrl_l","alt_l","space",
        "mouse_left","mouse_middle","mouse_right",
    }
    keys = [k for k in _qwerty_full() if k["id"] in keep_ids]
    # Highlight WASD
    highlight = {"w","a","s","d"}
    for k in keys:
        if k["id"] in highlight:
            k["color"] = "#7b68ee"
    return keys


def _numpad():
    keys = []
    layout = [
        [("num_lock","Num",0), ("kp_divide","/",1), ("kp_multiply","*",2), ("kp_subtract","-",3)],
        [("kp7","7",0), ("kp8","8",1), ("kp9","9",2)],
        [("kp4","4",0), ("kp5","5",1), ("kp6","6",2)],
        [("kp1","1",0), ("kp2","2",1), ("kp3","3",2)],
        [("kp0","0",0, 2.0), ("kp_decimal",".",2)],
    ]
    for row_idx, row in enumerate(layout):
        for item in row:
            if len(item) == 4:
                kid, lbl, col, w = item
            else:
                kid, lbl, col = item
                w = 1.0
            keys.append(_key(kid, lbl, col, row_idx, w=w))
    # Enter spans rows 1-2 col 3
    keys.append(_key("kp_enter", "Ent", 3, 1, w=1.0, h=2.0))
    return keys


# ── AZERTY ────────────────────────────────────────────────────────────────────

def _azerty_full():
    keys = []
    # Row 0 – function keys (same as QWERTY)
    row0 = [
        ("esc","Esc"), ("f1","F1"), ("f2","F2"), ("f3","F3"), ("f4","F4"),
        ("f5","F5"), ("f6","F6"), ("f7","F7"), ("f8","F8"),
        ("f9","F9"), ("f10","F10"), ("f11","F11"), ("f12","F12"),
        ("print_screen","Prt"), ("insert","Ins"), ("delete","Del"),
    ]
    x = 0
    for kid, lbl in row0:
        keys.append(_key(kid, lbl, x, 0))
        x += 1

    # Row 1 – AZERTY numbers
    row1 = [
        ("sup2","²"), ("ampersand","&"), ("eacute","é"),
        ("quotedbl",'"'), ("apostrophe","'"), ("parenleft","("),
        ("minus","-"), ("egrave","è"), ("underscore","_"),
        ("ccedilla","ç"), ("agrave","à"), ("parenright",")"),
        ("equal","="),
    ]
    x = 0
    for kid, lbl in row1:
        keys.append(_key(kid, lbl, x, 1))
        x += 1
    keys.append(_key("backspace", "Bksp", x, 1, w=2.0))

    # Row 2 – AZERTY
    keys.append(_key("tab", "Tab", 0, 2, w=1.5))
    row2 = [("a","A"),("z","Z"),("e","E"),("r","R"),("t","T"),
            ("y","Y"),("u","U"),("i","I"),("o","O"),("p","P"),
            ("caret","^"), ("dollar","$")]
    x = 1.5
    for kid, lbl in row2:
        keys.append(_key(kid, lbl, x, 2))
        x += 1
    keys.append(_key("\\", "\\", x, 2, w=1.5))

    # Row 3 – QSDF
    keys.append(_key("caps_lock", "Caps", 0, 3, w=1.75))
    row3 = [("q","Q"),("s","S"),("d","D"),("f","F"),("g","G"),
            ("h","H"),("j","J"),("k","K"),("l","L"),("m","M"),
            ("ugrave","ù")]
    x = 1.75
    for kid, lbl in row3:
        keys.append(_key(kid, lbl, x, 3))
        x += 1
    keys.append(_key("enter", "Enter", x, 3, w=2.25))

    # Row 4 – WXCV
    keys.append(_key("shift", "Shift", 0, 4, w=2.25))
    row4 = [("w","W"),("x","X"),("c","C"),("v","V"),("b","B"),
            ("n","N"),(",",","),(";",";"),(":",":")  ,("!","!")]
    x = 2.25
    for kid, lbl in row4:
        keys.append(_key(kid, lbl, x, 4))
        x += 1
    keys.append(_key("shift_r", "Shift", x, 4, w=2.75))

    # Row 5
    row5 = [
        ("ctrl_l","Ctrl",0,5,1.25), ("cmd","Win",1.25,5,1.25),
        ("alt_l","Alt",2.5,5,1.25),
        ("space","Space",3.75,5,6.25),
        ("alt_gr","AltGr",10.0,5,1.25), ("cmd_r","Win",11.25,5,1.25),
        ("ctrl_r","Ctrl",12.5,5,1.25),
    ]
    for kid, lbl, x, y, w in row5:
        keys.append(_key(kid, lbl, x, y, w=w))

    # Mouse
    keys.append(_key("mouse_left",   "LMB", 0, 7, w=1.5, h=1.5, color="#1e3a5f", text_color="#aaddff"))
    keys.append(_key("mouse_middle", "MMB", 1.6, 7, w=1.5, h=1.5, color="#1e3a5f", text_color="#aaddff"))
    keys.append(_key("mouse_right",  "RMB", 3.2, 7, w=1.5, h=1.5, color="#1e3a5f", text_color="#aaddff"))

    return keys


# ── Public registry ───────────────────────────────────────────────────────────

BUILTIN_PRESETS = []

def _register():
    entries = [
        ("Full Keyboard (QWERTY)",   "qwerty", _qwerty_full),
        ("No F-Keys (QWERTY)",       "qwerty", _qwerty_no_fkeys),
        ("Left Half (QWERTY)",       "qwerty", _qwerty_left_half),
        ("Gaming / WASD",            "qwerty", _gaming_wasd),
        ("Numpad",                   "qwerty", _numpad),
        ("Full Keyboard (AZERTY)",   "azerty", _azerty_full),
    ]
    for name, layout, fn in entries:
        try:
            keys = fn()
            BUILTIN_PRESETS.append({"name": name, "layout": layout, "keys": keys})
            log.debug("Registered preset: %s (%d keys)", name, len(keys))
        except Exception as e:
            log.error("Failed to build preset '%s': %s", name, e)

_register()

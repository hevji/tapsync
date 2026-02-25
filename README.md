# ⌨️ Kryns (Keyboard Overlay for Streaming)

A real-time keyboard and mouse overlay for streamers, built with Python, PyQt6 and pynput. Keys and mouse buttons light up as you press them — designed to be captured cleanly in OBS as a window source.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)

---

## ✨ Features

- **Real-time key highlighting** — keys and mouse buttons light up instantly on press, no polling lag
- **Full layout support** — QWERTY and AZERTY out of the box
- **Built-in presets** — Full Keyboard, No F-Keys, Left Half, Gaming/WASD, Numpad
- **Visual drag-and-drop editor** — move keys anywhere, snap-to-grid or free placement
- **Per-key customisation** — individual colour, text colour, label, width, height
- **Theme editor** — background, idle/pressed colours, font, corner radius, key size, gap
- **Save / load configs** — stored as JSON in your system's config folder
- **Import / export** — share layouts as `.json` files
- **Transparent overlay** — borderless window with alpha transparency, works with OBS Window Capture
- **Colour-coded log panel** — see exactly what's happening or what failed in real time

---

## 📸 Screenshots

![Presets](images/screenshot1.png)
![Editor](images/screenshot2.png)

`i dont rlly know what to screenshot so you got 2 be happy`

---

## 🚀 Installation

### Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/hevji/overkeys.git
cd overkeys

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

### Dependencies

```
PyQt6
pynput
```

---

## 🖥️ OBS Setup

1. Run `python main.py` and click **▶ Show Overlay** in the Overlay tab
2. In OBS, click **+** under Sources → **Window Capture**
3. Select the window titled **Keyboard Overlay**
4. In the source properties, enable **Allow Transparency**
5. Resize and reposition the source in your scene as needed

> **Tip:** On Windows you can also use a **Color Key** filter in OBS to key out the background colour if transparency doesn't work with your capture method.

---

## 🗂️ Project Structure

```
keyboard-overlay/
├── main.py          # Entry point — PyQt6 app and all tabs
├── overlay.py       # Borderless transparent overlay window
├── editor.py        # Drag-and-drop layout editor + properties panel
├── presets.py       # Built-in keyboard layout presets
├── config.py        # Save / load JSON configs
├── listener.py      # pynput keyboard and mouse listener
└── requirements.txt
```

---

## 🎨 Customisation

### Theme tab

Everything visual is adjustable without touching code:

| Setting | What it controls |
|---|---|
| Key Idle / Pressed colour | Background colour of keys at rest and when held |
| Mouse Idle / Pressed | Same for mouse buttons |
| Key Outline | Border colour |
| Font family / size / bold | Key label text |
| Corner Radius | How rounded the key corners are (0 = sharp) |
| Key Width / Height / Gap | Overall key sizing in pixels |
| Overlay Opacity | Transparency of the whole overlay window |

### Per-key overrides

In the **Editor** tab, click any key to select it and use the properties panel on the right to override its colour, text colour, label, width, and height individually. The WASD preset uses this to highlight movement keys in purple by default.

### Layouts

Layouts are stored as `.json` files. You can edit them by hand if you want — each key has:

```json
{
  "id":         "w",
  "label":      "W",
  "x":          2.5,
  "y":          2.0,
  "w":          1.0,
  "h":          1.0,
  "color":      null,
  "text_color": null
}
```

`x` and `y` are in grid units, `w` and `h` are key width/height multipliers (e.g. `2.0` = double-wide key).

---

## 💾 Config Storage

Configs are saved automatically to your system's standard config folder:

| OS | Path |
|---|---|
| Windows | `%APPDATA%\KeyboardOverlay\configs\` |
| macOS | `~/Library/Application Support/KeyboardOverlay/configs/` |
| Linux | `~/.config/KeyboardOverlay/configs/` |

Global settings (theme, last loaded config, overlay position) are saved to `settings.json` in the parent folder.

---

## ⚠️ Platform Notes

### macOS
pynput requires **Accessibility permissions** to read keystrokes. Go to:
`System Preferences → Privacy & Security → Accessibility` and add your terminal or Python.

Without this, key detection will silently fail — you'll see a warning in the Log tab.

### Linux
For the transparent overlay background to work you need a compositor running (e.g. **picom** or **compton** on X11, or a Wayland compositor that supports it).

### Windows
Works out of the box. For the cleanest OBS capture use **Window Capture** with **Allow Transparency** ticked. If that's not available in your OBS version, use a **Color Key** filter instead.

---

## 🛠️ Built With

- [PyQt6](https://pypi.org/project/PyQt6/) — GUI framework
- [pynput](https://pypi.org/project/pynput/) — Global keyboard and mouse listener

---

## 📄 License

MIT — do whatever you want with it.

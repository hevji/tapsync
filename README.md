# Overkeys, a Keyboard Overlay for Low-End PCs

A lightweight Python keyboard overlay application designed for low-end PCs. It visually displays key presses on your screen in real-time without consuming significant system resources. Perfect for streamers, content creators, or anyone who wants an on-screen representation of keyboard input.

> **Privacy Note:** This script listens to your keyboard input to display key presses on the overlay, but it **does not send any data to the internet, webhooks, or third-party services.** All input is handled locally.

---

## Features

* **Low Resource Usage:** Designed specifically to run smoothly on low-end PCs.
* **Real-Time Key Display:** Shows pressed keys instantly.
* **Customizable Overlay:** Adjust size, position, color, and opacity.
* **Lightweight Dependencies:** Minimal Python libraries required.
* **Cross-Platform Support:** Works on Windows, with experimental support for Linux.

---

## Requirements

* **Python 3.10+**
* **Pynput** – for keyboard input detection
* **PyQt6** – for overlay GUI (included with most Python installations)

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/hevji/overkeys.git
cd overkeys
```

2. Create and activate a virtual environment (optional but recommended):

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Usage

Run the overlay with:

```bash
main.py
```

### Configuration Options

* **Position:** Set the overlay position (x, y) in `config.ini`.
* **Opacity:** Adjust transparency to avoid blocking important parts of the screen.
* **Size:** Change key size and spacing to fit your screen resolution.
* **Colors:** Customize key color, text color, and pressed key highlight color.

Example `config.ini`:

```ini
[Overlay]
x = 100
y = 100
opacity = 0.8
key_size = 50
text_color = #FFFFFF
highlight_color = #00FF00
```

---

## How It Works

1. The app listens for keyboard input using `pynput`.
2. The pressed keys are rendered on a transparent Tkinter window.
3. Key release events are immediately reflected, ensuring real-time display.
4. The overlay remains always on top, with minimal CPU and RAM usage.

---

## Optimization Tips for Low-End PCs

* Reduce the number of displayed keys to only essential ones.
* Lower overlay opacity instead of rendering complex graphics.
* Avoid running multiple Python overlays simultaneously.
* Use `.png` or `.ico` files sparingly if using custom key icons.
* Keep Python updated to improve performance with Tkinter.

---

## Contribution

Contributions are welcome! If you want to add features or improve performance:

1. Fork the repository
2. Create a new branch
3. Commit your changes
4. Open a Pull Request

---

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.

---

## Acknowledgements

* [Pynput](https://pypi.org/project/pynput/) – Keyboard and mouse input handling
* PyQt6 – GUI overlay rendering
* Low-end PC users who inspired a lightweight design

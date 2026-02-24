"""
listener.py — Shared pynput keyboard + mouse listener.

Runs both listeners in daemon threads. Emits key_event(key_id, pressed)
via a callback so the overlay can update without polling.

key_id conventions:
  - single printable char  → lowercase char  e.g. "a", "1", "["
  - special key            → Key.name        e.g. "shift", "ctrl_l", "f1"
  - mouse button           → "mouse_left", "mouse_right", "mouse_middle"
"""

import logging
from pynput import keyboard, mouse

log = logging.getLogger("listener")


def _normalize(key) -> str | None:
    try:
        c = key.char
        if c:
            return c.lower()
    except AttributeError:
        pass
    name = getattr(key, "name", None) or str(key)
    return name.lower()


class InputListener:
    """
    Usage:
        listener = InputListener(callback=my_fn)
        listener.start()

    callback(key_id: str, pressed: bool) is called from background threads.
    """

    def __init__(self, callback):
        self._cb = callback
        self._kb = None
        self._ms = None
        self._started = False

    def start(self):
        if self._started:
            log.warning("InputListener.start() called twice — ignoring")
            return
        try:
            self._kb = keyboard.Listener(
                on_press=self._on_kb_press,
                on_release=self._on_kb_release,
            )
            self._kb.daemon = True
            self._kb.start()
            log.info("Keyboard listener started")
        except Exception as e:
            log.error("Failed to start keyboard listener: %s", e)
            log.error("On macOS: grant Accessibility permissions in System Preferences.")

        try:
            self._ms = mouse.Listener(on_click=self._on_click)
            self._ms.daemon = True
            self._ms.start()
            log.info("Mouse listener started")
        except Exception as e:
            log.error("Failed to start mouse listener: %s", e)

        self._started = True

    def stop(self):
        for l in (self._kb, self._ms):
            if l:
                try:
                    l.stop()
                except Exception as e:
                    log.warning("Error stopping listener: %s", e)
        log.info("Listeners stopped")

    def _on_kb_press(self, key):
        kid = _normalize(key)
        if kid:
            self._cb(kid, True)

    def _on_kb_release(self, key):
        kid = _normalize(key)
        if kid:
            self._cb(kid, False)

    def _on_click(self, x, y, button, pressed):
        kid = f"mouse_{button.name}"
        self._cb(kid, pressed)

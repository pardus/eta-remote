#!/usr/bin/env python
"""Reads the live X11 xkb keymap and produces a JS KeyboardEvent.code to
character label map for the virtual keyboard."""

import os
import re
import subprocess

import traceback

# --- JS KeyboardEvent.code to xkb key name ----------------------------------
# xkb names are evdev identifiers used by xkbcomp (e.g. AD01 = Q key).

CODE_TO_XKB = {
    # Special / modifier keys
    "Escape":     "ESC",
    "Backspace":  "BKSP",
    "Tab":        "TAB",
    "CapsLock":   "CAPS",
    "Enter":      "RTRN",
    "ShiftLeft":  "LFSH",
    "ControlLeft":"LCTL",
    "AltLeft":    "LALT",
    "MetaLeft":   "LWIN",
    "Space":      "SPCE",
    "AltRight":   "RALT",

    # Top row – number keys
    "Backquote":  "TLDE",
    "Digit1": "AE01", "Digit2": "AE02", "Digit3": "AE03", "Digit4": "AE04",
    "Digit5": "AE05", "Digit6": "AE06", "Digit7": "AE07", "Digit8": "AE08",
    "Digit9": "AE09", "Digit0": "AE10",
    "Minus": "AE11",  "Equal": "AE12",

    # QWERTY row (top letter row)
    "KeyQ": "AD01", "KeyW": "AD02", "KeyE": "AD03", "KeyR": "AD04",
    "KeyT": "AD05", "KeyY": "AD06", "KeyU": "AD07", "KeyI": "AD08",
    "KeyO": "AD09", "KeyP": "AD10",
    "BracketLeft": "AD11", "BracketRight": "AD12", "Backslash": "BKSL",

    # Home row
    "KeyA": "AC01", "KeyS": "AC02", "KeyD": "AC03", "KeyF": "AC04",
    "KeyG": "AC05", "KeyH": "AC06", "KeyJ": "AC07", "KeyK": "AC08",
    "KeyL": "AC09", "Semicolon": "AC10", "Quote": "AC11",

    # Bottom letter row
    "KeyZ": "AB01", "KeyX": "AB02", "KeyC": "AB03", "KeyV": "AB04",
    "KeyB": "AB05", "KeyN": "AB06", "KeyM": "AB07",
    "Comma": "AB08", "Period": "AB09", "Slash": "AB10",

    # Navigation
    "Home": "HOME", "End": "END",
    "PageUp": "PGUP", "PageDown": "PGDN",
    "ArrowLeft": "LEFT", "ArrowDown": "DOWN",
    "ArrowRight": "RGHT", "ArrowUp": "UP",

    # Editing / misc
    "Delete": "DELE", "PrintScreen": "PRSC",

    # Function keys
    "F1":  "FK01", "F2":  "FK02", "F3":  "FK03", "F4":  "FK04",
    "F5":  "FK05", "F6":  "FK06", "F7":  "FK07", "F8":  "FK08",
    "F9":  "FK09", "F10": "FK10", "F11": "FK11", "F12": "FK12",
}

# --- Keysym to display text --------------------------------------------------
# Fallbacks for keysyms that don't render as plain Unicode characters.

KEYSYM_TEXT = {
    # Punctuation & symbols
    "space": " ",    "minus": "-",    "equal": "=",
    "plus": "+",     "asterisk": "*", "slash": "/",
    "backslash": "\\", "comma": ",",  "period": ".",
    "semicolon": ";", "colon": ":",
    "quotedbl": '"', "apostrophe": "'", "grave": "`",
    "asciitilde": "~", "exclam": "!",  "at": "@",
    "numbersign": "#", "dollar": "$",  "percent": "%",
    "asciicircum": "^", "ampersand": "&",
    "parenleft": "(", "parenright": ")",
    "underscore": "_",
    "bracketleft": "[", "bracketright": "]",
    "braceleft": "{",  "braceright": "}",
    "bar": "|",  "less": "<",  "greater": ">",
    "question": "?",

    # Accented / international characters
    "EuroSign": "€",
    "idotless": "ı",  "i": "ı",
    "ssharp": "ß",    "gbreve": "ğ",   "Ubreve": "Ğ",
    "scaron": "š",    "caron": "ˇ",
    "scedilla": "ş",  "Scedilla": "Ş",
    "ccedilla": "ç",  "Ccedilla": "Ç",
    "adiaeresis": "ä", "Adiaeresis": "Ä",
    "odiaeresis": "ö", "Odiaeresis": "Ö",
    "udiaeresis": "ü", "Udiaeresis": "Ü",

    # Special key labels
    "BackSpace": "⌫",   "Tab": "Tab ↹",    "Return": "Enter",
    "Escape": "Esc",     "Delete": "Del",
    "Home": "Home",      "End": "End",
    "Up": "▲",           "Down": "▼",
    "Left": "◀",         "Right": "▶",
    "Prior": "PgUp",     "Next": "PgDn",
    "Print": "PrtSc",
    "Caps_Lock": "Caps", "Shift_L": "Shift",
    "Control_L": "Ctrl", "Alt_L": "Alt",
    "Meta_L": "Super",   "Super_L": "Super",
    "ISO_Level3_Shift": "AltGr",
}


# --- X11 helpers -------------------------------------------------------------

def _xkb_dump():
    """Return the raw xkbcomp output for the current DISPLAY."""
    disp = os.environ.get("DISPLAY", ":0")
    try:
        proc = subprocess.run(
            ["xkbcomp", "-w", "0", "-xkb", disp, "-"],
            capture_output=True, text=True, timeout=10,
        )
        return proc.stdout
    except:
        print(traceback.format_exc())
        return ""


def _parse_symbols(text):
    """Parse xkbcomp output into {XKB_NAME: first-symbol} per key's base group."""
    result = {}
    for m in re.finditer(r'key\s+<([^>]+)>\s*\{([^}]*)\}', text):
        name = m.group(1)
        body = m.group(2)

        # Prefer explicit Group1, otherwise take the first bracket group.
        sm = re.search(r"symbols\[Group1\]\s*=\s*\[([^\]]*)\]", body)
        if not sm:
            sm = re.search(r"\[\s*([^\]]*?)\s*\]", body)
        if not sm:
            continue

        syms = [s.strip() for s in sm.group(1).split(",")]
        syms = [s for s in syms if s and s != "VoidSymbol"]
        if syms:
            result[name] = syms
    return result


def _keysym_to_text(sym):
    """Convert an X11 keysym name to a human-readable label."""
    sym = sym.strip()
    if sym in KEYSYM_TEXT:
        return KEYSYM_TEXT[sym]
    # Single letters / digits pass through unchanged.
    if re.fullmatch(r"[a-zA-Z0-9]", sym):
        return sym
    return sym


# --- Public API --------------------------------------------------------------

def build_keymap():
    """Return {JS KeyboardEvent.code: display_label} for all mapped keys."""
    text = _xkb_dump()
    syms = _parse_symbols(text)

    keymap = {}
    for code, xkb in CODE_TO_XKB.items():
        symbol = syms.get(xkb)
        keymap[code] = []
        for sym in symbol:
            key = _keysym_to_text(sym) if sym else code
            keymap[code].append(key)
    return keymap


if __name__ == "__main__":
    import json
    print(json.dumps(build_keymap(), ensure_ascii=False, indent=2))

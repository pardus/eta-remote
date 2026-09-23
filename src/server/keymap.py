#!/usr/bin/env python
"""Reads the live X11 xkb keymap and produces a JS KeyboardEvent.code to
character label map for the virtual keyboard."""

import os
import re
import subprocess

import traceback

import json

_data = {}
with open(os.path.dirname(__file__)+"/keymap.json", "r") as f:
    _data = json.load(f)

KEYSYM_TEXT = _data.get("KEYSYM_TEXT", [])
CODE_TO_XKB = _data.get("CODE_TO_XKB", [])


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
        syms = [s for s in syms if s and s not in ["VoidSymbol", "NoSymbol"] and not s.startswith("dead")]
        if syms:
            result[name] = syms
    return result


def is_hex(sym):
    found = re.findall(r"[a-fA-F0-9]", sym)
    return len(found) > 0 and "".join(found) == sym

def _keysym_to_text(sym):
    """Convert an X11 keysym name to a human-readable label."""
    sym = sym.strip()
    if sym in KEYSYM_TEXT:
        return KEYSYM_TEXT[sym]
    # Unicode. Example U20BA
    if sym.startswith("U") and is_hex(sym[1:]):
        return str(chr(int(sym[1:],16)))
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

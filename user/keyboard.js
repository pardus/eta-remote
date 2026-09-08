"use strict";

// Minimal virtual keyboard.
//
// The layout is expressed purely in JS `KeyboardEvent.code` values
// (e.g. "KeyQ", "Digit1", "ShiftLeft") — never display labels. Labels are
// derived at render time from the hard-coded DISPLAY map, then overridden
// by the live server keymap fetched from /keymap.json.
//
// Modifier keys (Shift, Ctrl, Super, Alt, AltGr, Caps) and Fn are toggles:
// tap once to latch on, tap again to release. Every other key is momentary.

const VirtualKeyboard = (() => {
    let onKey = null;
    let visible = false;
    let container = null;
    let fnActive = false;
    let fnKeys = [];

    const serverLabels = {};

    const LAYOUT = [
        ["Escape", "Backquote", "Digit1", "Digit2", "Digit3", "Digit4", "Digit5",
         "Digit6", "Digit7", "Digit8", "Digit9", "Digit0", "Minus", "Equal", "Backspace"],
        ["Tab", "KeyQ", "KeyW", "KeyE", "KeyR", "KeyT", "KeyY",
         "KeyU", "KeyI", "KeyO", "KeyP", "BracketLeft", "BracketRight", "Backslash"],
        ["CapsLock", "KeyA", "KeyS", "KeyD", "KeyF", "KeyG", "KeyH",
         "KeyJ", "KeyK", "KeyL", "Semicolon", "Quote", "Enter"],
        ["ShiftLeft", "KeyZ", "KeyX", "KeyC", "KeyV", "KeyB", "KeyN",
         "KeyM", "Comma", "Period", "Slash", "ShiftRight","Hide"],
        ["ControlLeft", "MetaLeft", "AltLeft", "Space", "AltRight", "Fn", "ControlRight"],
    ];

    // Rendering only: nice labels for keys that aren't a plain letter/digit.
    const DISPLAY = {
        "Escape": "esc", "Backquote": "`", "Minus": "-", "Equal": "=",
        "Backspace": "⌫", "Tab": "tab", "BracketLeft": "[", "BracketRight": "]",
        "Backslash": "\\", "CapsLock": "caps", "Semicolon": ";", "Quote": "'",
        "Enter": "⏎", "ShiftLeft": "⇧", "ShiftRight": "⇧", "ControlRight": "Ctrl",
        "ControlLeft": "ctrl", "MetaLeft": "⌘", "AltLeft": "alt", "AltRight": "altgr",
        "Space": "space", "ArrowLeft": "◀", "ArrowDown": "▼", "ArrowRight": "▶",
    };

    const MODIFIERS = new Set([
        "ShiftLeft", "ShiftRight", "ControlLeft", "MetaLeft", "AltLeft", "AltRight", 
        "ControlRight"
    ]);

    // While Fn is latched, these codes act as the mapped code.
    const FN = {
        "Digit1": "F1", "Digit2": "F2", "Digit3": "F3", "Digit4": "F4", "Digit5": "F5",
        "Digit6": "F6", "Digit7": "F7", "Digit8": "F8", "Digit9": "F9", "Digit0": "F10",
        "Minus": "F11", "Equal": "F12",
        "KeyQ": "Home", "KeyW": "ArrowUp", "KeyE": "End",
        "KeyA": "ArrowLeft", "KeyS": "ArrowDown", "KeyD": "ArrowRight",
        "KeyR": "PageUp", "KeyF": "PageDown", "Backspace": "Delete",
    };

    function label(code) {
        if (serverLabels[code] != null) return serverLabels[code];
        if (DISPLAY[code] != null) return DISPLAY[code];
        if (/^Key[A-Z]$/.test(code)) return code[3];
        if (/^Digit[0-9]$/.test(code)) return code[5];
        return code;
    }

    function send(action, code) {
        if (onKey) onKey(action, { code });
    }

    function fresh(btn) {
        return fnActive && FN[btn.code] ? FN[btn.code] : btn.code;
    }

    function refresh(btn) {
        btn.textContent = label(fresh(btn));
        btn.classList.toggle("fn", fnActive && FN[btn.code]);
    }

    // Latch: tap -> down, tap again -> up.
    function latch(btn) {
        btn.latched = !btn.latched;
        btn.classList.toggle("active", btn.latched);
        send(btn.latched ? "down" : "up", btn.code);
    }

    function setFn(on) {
        fnActive = on;
        fnKeys.forEach(btn => {
            refresh(btn);
        });
    }

    function bind(btn) {
        if (btn.code === "Fn") {
            btn.addEventListener("click", e => { e.preventDefault(); setFn(!fnActive); });
            return;
        }
        if (MODIFIERS.has(btn.code)) {
            btn.addEventListener("click", e => { e.preventDefault(); latch(btn); });
            return;
        }
        const down = e => { e.preventDefault(); send("down", fresh(btn)); btn.classList.add("active"); };
        const up = e => { e.preventDefault(); send("up", fresh(btn)); btn.classList.remove("active"); };
        btn.addEventListener("mousedown", down);
        btn.addEventListener("mouseup", up);
        btn.addEventListener("mouseleave", up);
        btn.addEventListener("touchstart", down, { passive: false });
        btn.addEventListener("touchend", up, { passive: false });
        btn.addEventListener("touchcancel", up);
    }

    function build() {
        const layer = document.createElement("div");
        layer.className = "layer";


        LAYOUT.forEach((row, idx) => {
            const rowEl = document.createElement("div");
            rowEl.className = "row";

            row.forEach(code => {
                const btn = document.createElement("button");
                btn.className = "key";
                btn.code = code;
                btn.latched = false;
                btn.textContent = label(code);
                if (code === "Space") btn.classList.add("Space");
                if (/^Key[A-Z]$/.test(code)) btn.classList.add("letter");
                if (MODIFIERS.has(code) || code === "Fn" || code == "Hide") btn.classList.add("mod");
                bind(btn);
                rowEl.appendChild(btn);
                if (FN[code]) fnKeys.push(btn);
                if (code === "Hide") {
                    btn.addEventListener("click", e => { e.preventDefault(); toggle(); });
                }

            });

            rowEl.style.height = 100 / LAYOUT.length + "%";
            layer.appendChild(rowEl);
        });

        return layer;
    }

    function init(callback, parentEl) {
        onKey = callback;
        container = document.createElement("div");
        container.id = "virtual-keyboard";
        container.style.display = "none";
        (parentEl || document.body).appendChild(container);
        container.appendChild(build());
    }

    function toggle() {
        if (!container) return;
        visible = !visible;
        container.style.display = visible ? "flex" : "none";
    }

    fetch("/keymap.json")
        .then(r => r.json())
        .then(map => {
            Object.assign(serverLabels, map);
            container && container.querySelectorAll(".key").forEach(btn => refresh(btn));
        })
        .catch(() => {});

    return { init, toggle, get visible() { return visible; } };
})();

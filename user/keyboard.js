"use strict";

// Keyboard layout. Each entry is a display label; the wire `code` is
// resolved via labelToCode so the client EV_KEY lookup works directly.
const keyboardLayoutCodes = [
    ['Esc', '`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Backspace'],
    ['Tab', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '\\'],
    ['CapsLock', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', '\''],
    ['Shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/'],
    ['Ctrl', 'Super', 'Alt', 'Space', 'Fn', 'Altgr',  'Enter']
];

// Display label -> JS KeyboardEvent.code
const labelToCode = {
    'Esc': 'Escape',
    'PrtSc': 'PrintScreen',
    'Del': 'Delete',
    '`': 'Backquote',
    '1': 'Digit1', '2': 'Digit2', '3': 'Digit3', '4': 'Digit4', '5': 'Digit5',
    '6': 'Digit6', '7': 'Digit7', '8': 'Digit8', '9': 'Digit9', '0': 'Digit0',
    '-': 'Minus',
    '=': 'Equal',
    'Backspace': 'Backspace',
    'Tab': 'Tab',
    'Q': 'KeyQ', 'W': 'KeyW', 'E': 'KeyE', 'R': 'KeyR', 'T': 'KeyT',
    'Y': 'KeyY', 'U': 'KeyU', 'I': 'KeyI', 'O': 'KeyO', 'P': 'KeyP',
    '[': 'BracketLeft',
    ']': 'BracketRight',
    '\\': 'Backslash',
    'Home': 'Home',
    'CapsLock': 'CapsLock',
    'A': 'KeyA', 'S': 'KeyS', 'D': 'KeyD', 'F': 'KeyF', 'G': 'KeyG',
    'H': 'KeyH', 'J': 'KeyJ', 'K': 'KeyK', 'L': 'KeyL',
    ';': 'Semicolon',
    "'": 'Quote',
    'Enter': 'Enter',
    'PgUp': 'PageUp',
    'Shift': 'ShiftLeft',
    'Z': 'KeyZ', 'X': 'KeyX', 'C': 'KeyC', 'V': 'KeyV', 'B': 'KeyB',
    'N': 'KeyN', 'M': 'KeyM',
    ',': 'Comma',
    '.': 'Period',
    '/': 'Slash',
    'End': 'End',
    'Up': 'ArrowUp',
    'PgDn': 'PageDown',
    'Ctrl': 'ControlLeft',
    'Super': 'MetaLeft',
    'Alt': 'AltLeft',
    'Space': 'Space',
    'Altgr': 'AltRight',
    'Left': 'ArrowLeft',
    'Down': 'ArrowDown',
    'Right': 'ArrowRight',
    'F1': 'F1', 'F2': 'F2', 'F3': 'F3', 'F4': 'F4', 'F5': 'F5',
    'F6': 'F6', 'F7': 'F7', 'F8': 'F8', 'F9': 'F9', 'F10': 'F10',
    'F11': 'F11', 'F12': 'F12',
};

// When Fn is held these labels change to the mapped one.
const fnLabels = {
    '1': 'F1', '2': 'F2', '3': 'F3', '4': 'F4', '5': 'F5',
    '6': 'F6', '7': 'F7', '8': 'F8', '9': 'F9', '0': 'F10',
    '-': 'F11', '=': 'F12', 'W': "Up", "A": "Left", 
    "S": "Down", "D": "Right", "Q": "Home", "E": "End",
    "R": "PgUp", "F": "PgDn", "Backspace": "Delete"
};

function codeForLabel(label) {
    if (labelToCode.hasOwnProperty(label)) {
        return labelToCode[label];
    }
    return label;
}

function displayForLabel(label) {
    const code = codeForLabel(label);
    if (keyDisplay.hasOwnProperty(code)) {
        return keyDisplay[code];
    }
    if (code.startsWith('Key') && code.length === 4) {
        return code[3];
    }
    if (code.startsWith('Digit') && code.length === 6) {
        return code[5];
    }
    return code;
}

// Friendly button text for each JS code.
const keyDisplay = {
    'Escape': 'Esc',
    'Backquote': '`',
    'Minus': '-',
    'Equal': '=',
    'Backspace': '⌫',
    'Tab': 'Tab',
    'BracketLeft': '[',
    'BracketRight': ']',
    'Backslash': '\\',
    'Home': 'Home',
    'CapsLock': 'CapsLock',
    'Semicolon': ';',
    'Quote': "'",
    'Enter': 'Enter',
    'PageUp': 'PgUp',
    'ShiftLeft': 'Shift',
    'Comma': ',',
    'Period': '.',
    'Slash': '/',
    'End': 'End',
    'ArrowUp': '▲',
    'PageDown': 'PgDn',
    'ControlLeft': 'Ctrl',
    'MetaLeft': '⌘',
    'AltLeft': 'Alt',
    'Space': 'Space',
    'AltRight': 'AltGr',
    'ArrowLeft': '◀',
    'ArrowDown': '▼',
    'ArrowRight': '▶',
    'Delete': 'Del',
    'PrintScreen': 'PrtSc'
};

let onKeyCallback = null;

function sendKey(action, code) {
    if (onKeyCallback) {
        const display = keyDisplay.hasOwnProperty(code) ? keyDisplay[code] : code;
        onKeyCallback(action, { key: display, code, display });
    }
}

// Track currently pressed buttons to avoid stuck keys
let pressedButtons = new Set();

function releaseButton(keyButton) {
    if (!isButtonDown(keyButton)) return;
    pressedButtons.delete(keyButton);
    keyButton.classList.remove('active');
    sendKey('up', keyButton._code);
}

function isButtonDown(keyButton) {
    return pressedButtons.has(keyButton);
}

function listenPress(keyButton) {
    if (isButtonDown(keyButton)) return;
    pressedButtons.add(keyButton);
    keyButton.classList.add('active');
    sendKey('down', keyButton._code);
}

const FN_LABEL = 'Fn';
let fnActive = false;

function relabelKeys(keys) {
    for (const k of keys) {
        const activeLabel = fnActive && fnLabels.hasOwnProperty(k.label) ? fnLabels[k.label] : k.label;
        k.button.textContent = displayForLabel(activeLabel);
        k.button._code = codeForLabel(activeLabel);
    }
}

function createKeyboard(labels) {
    const root = document.createElement('div');
    root.className = 'layer';

    const fnButtons = [];

    labels.forEach(row => {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'row';

        row.forEach(label => {
            const keyButton = document.createElement('button');
            keyButton.className = 'key';
            keyButton.classList.add(codeForLabel(label));

            if (label === FN_LABEL) {
                keyButton.textContent = 'Fn';
                keyButton.classList.add('fn');
                const setFn = (on) => {
                    fnActive = on;
                    relabelKeys(root._keys);
                    for (const b of fnButtons) b.classList.toggle('active', fnActive);
                };
                keyButton.addEventListener('mousedown', (e) => { e.preventDefault(); setFn(true); });
                keyButton.addEventListener('mouseup', (e) => { e.preventDefault(); setFn(false); });
                keyButton.addEventListener('mouseleave', () => setFn(false));
                keyButton.addEventListener('touchstart', (e) => { e.preventDefault(); setFn(true); }, { passive: false });
                keyButton.addEventListener('touchend', (e) => { e.preventDefault(); setFn(false); }, { passive: false });
                keyButton.addEventListener('touchcancel', () => setFn(false));
                fnButtons.push(keyButton);
                rowDiv.appendChild(keyButton);
                return;
            }

            keyButton.textContent = displayForLabel(label);
            keyButton._label = label;
            keyButton._code = codeForLabel(label);
            if (fnLabels.hasOwnProperty(label)) {
                keyButton.classList.add('fn-latch');
            }
            if (/^(Key[A-Z]|Digit[0-9])$/.test(keyButton._code)) {
                keyButton.classList.add('letter');
            }

            keyButton.onmousedown = (e) => { e.preventDefault(); listenPress(keyButton); };
            keyButton.onmouseup = (e) => { e.preventDefault(); releaseButton(keyButton); };
            keyButton.onmouseleave = () => releaseButton(keyButton);
            keyButton.addEventListener('touchstart', (e) => { e.preventDefault(); listenPress(keyButton); }, { passive: false });
            keyButton.addEventListener('touchend', (e) => { e.preventDefault(); releaseButton(keyButton); }, { passive: false });
            keyButton.addEventListener('touchcancel', () => releaseButton(keyButton));

            (root._keys = root._keys || []).push({ button: keyButton, label });
            rowDiv.appendChild(keyButton);
        });

        rowDiv.style.height = (100 / labels.length) + "%";
        root.appendChild(rowDiv);
    });

    return root;
}

const VirtualKeyboard = (() => {
    let isVisible = false;
    let toggleBtn = null;
    let container = null;

    function toggle() {
        if (!container) return;
        isVisible = !isVisible;
        container.style.display = isVisible ? "flex" : "none";
        toggleBtn.textContent = isVisible ? "Hide Keyboard" : "Show Keyboard";
    }

    function init(callback, parentEl) {
        onKeyCallback = callback;

        toggleBtn = document.createElement("button");
        toggleBtn.id = "kb-toggle";
        toggleBtn.textContent = "Show Keyboard";
        toggleBtn.addEventListener("click", toggle);

        container = document.createElement("div");
        container.id = "virtual-keyboard";
        container.style.display = "none";

        (parentEl || document.body).appendChild(toggleBtn);
        (parentEl || document.body).appendChild(container);

        container.appendChild(createKeyboard(keyboardLayoutCodes));

        isVisible = true;
        container.style.display = "flex";
        toggleBtn.textContent = "Hide Keyboard";
    }

    return { init, toggle };
})();

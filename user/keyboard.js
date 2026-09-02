"use strict";

// Keyboard layout. Each entry is a display label; the wire `code` is
// resolved via labelToCode so the client EV_KEY lookup works directly.
const keyboardLayoutCodes = [
    ['Esc', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12', 'PrtSc', 'Del'],
    ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Backspace'],
    ['Tab', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '\\', 'Home'],
    ['CapsLock', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', '\'', 'Enter', 'PgUp'],
    ['Shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', 'End', 'Up', 'PgDn'],
    ['Ctrl', 'Super', 'Alt', 'Space', 'Altgr', 'Left', 'Down', 'Right']
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

function codeForLabel(label) {
    if (labelToCode.hasOwnProperty(label)) {
        return labelToCode[label];
    }
    return label;
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

function displayForCode(code) {
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

let onKeyCallback = null;

function sendKey(action, code) {
    if (onKeyCallback) {
        const display = displayForCode(code);
        onKeyCallback(action, { key: display, code, display });
    }
}

// Track currently pressed buttons to avoid stuck keys
let pressedButtons = new Set();

function releaseButton(keyButton, code) {
    if (!isButtonDown(keyButton)) return;
    pressedButtons.delete(keyButton);
    keyButton.classList.remove('active');
    sendKey('up', code);
}

function isButtonDown(keyButton) {
    return pressedButtons.has(keyButton);
}

function listenPress(code, keyButton) {
    if (isButtonDown(keyButton)) return;
    pressedButtons.add(keyButton);
    keyButton.classList.add('active');
    sendKey('down', code);
}

// Function to create a keyboard
function createKeyboard(page, labels) {
    const container = document.getElementById(page);

    labels.forEach(row => {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'row';

        row.forEach(label => {
            const code = codeForLabel(label);
            const keyButton = document.createElement('button');
            keyButton.className = 'key';
            keyButton.textContent = displayForCode(code);
            keyButton.classList.add(code);
            if (/^(Key[A-Z]|Digit[0-9])$/.test(code)) {
                keyButton.classList.add('letter');
            }

            // Add mouse event listeners
            keyButton.onmousedown = (e) => {
                e.preventDefault();
                listenPress(code, keyButton);
            };

            keyButton.onmouseup = (e) => {
                e.preventDefault();
                releaseButton(keyButton, code);
            };
            keyButton.onmouseleave = (e) => {
                releaseButton(keyButton, code);
            };

            // Add touch event listeners (mobile)
            keyButton.addEventListener('touchstart', (e) => {
                e.preventDefault();
                listenPress(code, keyButton);
            }, { passive: false });

            keyButton.addEventListener('touchend', (e) => {
                e.preventDefault();
                releaseButton(keyButton, code);
            }, { passive: false });
            keyButton.addEventListener('touchcancel', (e) => {
                releaseButton(keyButton, code);
            });

            rowDiv.appendChild(keyButton);
        });

        rowDiv.style.height = (100 / labels.length) + "%";
        container.appendChild(rowDiv);
    });
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

        const isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);

        toggleBtn = document.createElement("button");
        toggleBtn.id = "kb-toggle";
        toggleBtn.textContent = "Show Keyboard";
        toggleBtn.addEventListener("click", toggle);

        container = document.createElement("div");
        container.id = "virtual-keyboard";
        container.style.display = "none";

        (parentEl || document.body).appendChild(toggleBtn);
        (parentEl || document.body).appendChild(container);

        createKeyboard('virtual-keyboard', keyboardLayoutCodes);

        /*if (!isMobile) {
            toggleBtn.style.display = "none";
            return;
        }*/

        isVisible = true;
        container.style.display = "flex";
        toggleBtn.textContent = "Hide Keyboard";
    }

    return { init, toggle };
})();

"use strict";

// - Layout ---------------------------------
// Each entry is a display label; the JS KeyboardEvent.code is resolved via
// labelToCode so the client EV_KEY lookup works directly.

const keyboardLayoutCodes = [
    ['Esc', '`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Backspace'],
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '\\'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', '\''],
    ['Shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/'],
    ['Ctrl', 'Super', 'Alt', 'Space', 'Fn', 'Altgr', 'Enter'],
];

// - Key-code mapping ----------------------------
// Hard-coded display label to JS KeyboardEvent.code.  Used to translate the
// labels above into the codes expected by the browser.

const labelToCode = {
    // Modifiers & special keys
    'Esc':      'Escape',
    'CapsLock': 'CapsLock',
    'Shift':    'ShiftLeft',
    'Ctrl':     'ControlLeft',
    'Super':    'MetaLeft',
    'Alt':      'AltLeft',
    'Altgr':    'AltRight',
    'Space':    'Space',
    'Enter':    'Enter',
    'Tab':      'Tab',
    'Backspace':'Backspace',

    // Top row – number keys
    '`': 'Backquote',
    '1': 'Digit1',  '2': 'Digit2',  '3': 'Digit3',  '4': 'Digit4',  '5': 'Digit5',
    '6': 'Digit6',  '7': 'Digit7',  '8': 'Digit8',  '9': 'Digit9',  '0': 'Digit0',
    '-': 'Minus',
    '=': 'Equal',

    // QWERTY letter row
    'Q': 'KeyQ',  'W': 'KeyW',  'E': 'KeyE',  'R': 'KeyR',  'T': 'KeyT',
    'Y': 'KeyY',  'U': 'KeyU',  'I': 'KeyI',  'O': 'KeyO',  'P': 'KeyP',
    '[': 'BracketLeft',
    ']': 'BracketRight',
    '\\':'Backslash',

    // Home row
    'A': 'KeyA',  'S': 'KeyS',  'D': 'KeyD',  'F': 'KeyF',  'G': 'KeyG',
    'H': 'KeyH',  'J': 'KeyJ',  'K': 'KeyK',  'L': 'KeyL',
    ';': 'Semicolon',
    "'": 'Quote',

    // Bottom row
    'Z': 'KeyZ',  'X': 'KeyX',  'C': 'KeyC',  'V': 'KeyV',  'B': 'KeyB',
    'N': 'KeyN',  'M': 'KeyM',
    ',': 'Comma',
    '.': 'Period',
    '/': 'Slash',

    // Navigation
    'Home': 'Home',
    'End':  'End',
    'PgUp': 'PageUp',
    'PgDn': 'PageDown',
    'Up':   'ArrowUp',
    'Down': 'ArrowDown',
    'Left': 'ArrowLeft',
    'Right':'ArrowRight',
    'Del':  'Delete',
    'PrtSc':'PrintScreen',

    // Function keys
    'F1':  'F1',   'F2':  'F2',   'F3':  'F3',   'F4':  'F4',
    'F5':  'F5',   'F6':  'F6',   'F7':  'F7',   'F8':  'F8',
    'F9':  'F9',   'F10': 'F10',  'F11': 'F11',  'F12': 'F12',
};

// When Fn is held, these keys are remapped to the mapped label.
const fnLabels = {
    '1': 'F1',  '2': 'F2',  '3': 'F3',  '4': 'F4',  '5': 'F5',
    '6': 'F6',  '7': 'F7',  '8': 'F8',  '9': 'F9',  '0': 'F10',
    '-': 'F11', '=': 'F12',
    'Q': 'Home',  'W': 'Up',     'E': 'End',
    'A': 'Left',  'S': 'Down',   'D': 'Right',
    'R': 'PgUp',  'F': 'PgDn',
    'Backspace': 'Delete',
    'T': 'Tab', 'G': 'CapsLock',
};

// - Friendly display text per code ---------------------
// Maps JS KeyboardEvent.code to short label shown on the virtual-key button.
// Overwritten at runtime with server-side labels from /keymap.json.

const keyDisplay = {
    'Escape':      'Esc',
    'Backquote':   '`',
    'Minus':       '-',
    'Equal':       '=',
    'Backspace':   '⌫',
    'Tab':         'Tab',
    'BracketLeft': '[',
    'BracketRight':']',
    'Backslash':   '\\',
    'Home':        'Home',
    'CapsLock':    'CapsLock',
    'Semicolon':   ';',
    'Quote':       "'",
    'Enter':       'Enter',
    'PageUp':      'PgUp',
    'ShiftLeft':   'Shift',
    'Comma':       ',',
    'Period':      '.',
    'Slash':       '/',
    'End':         'End',
    'ArrowUp':     '▲',
    'PageDown':    'PgDn',
    'ControlLeft': 'Ctrl',
    'MetaLeft':    '⌘',
    'AltLeft':     'Alt',
    'Space':       'Space',
    'AltRight':    'AltGr',
    'ArrowLeft':   '◀',
    'ArrowDown':   '▼',
    'ArrowRight':  '▶',
    'Delete':      'Del',
    'PrintScreen': 'PrtSc',
};

// - Server keymap integration ------------------------
// The server generates /keymap.json from the live X11 layout.  We store it
// here and merge its labels into keyDisplay so the virtual keyboard reflects
// the actual system layout (e.g. Turkishğ instead of English;).

let _serverKeymap = null;

fetch('/keymap.json')
    .then(r => r.json())
    .then(map => {
        _serverKeymap = map;

        for (const [code, label] of Object.entries(map)) {
            keyDisplay[code] = label;
        }

        // Re-render buttons that were already created before the fetch.
        document.querySelectorAll('.key').forEach(btn => {
            if (btn._code && keyDisplay[btn._code]) {
                btn.textContent = keyDisplay[btn._code];
            }
        });
    });

// - Label / code helpers ---------------------------

function codeForLabel(label) {
    if (labelToCode.hasOwnProperty(label)) {
        return labelToCode[label];
    }
    // Reverse-lookup in the server keymap for non-ASCII labels (e.g. ğ, ş).
    if (_serverKeymap) {
        for (const [code, lbl] of Object.entries(_serverKeymap)) {
            if (lbl === label) return code;
        }
    }
    return label;
}

function displayForLabel(label) {
    const code = codeForLabel(label);
    if (keyDisplay.hasOwnProperty(code)) {
        return keyDisplay[code];
    }
    // Fallback: extract the letter/digit from codes like "KeyQ" to "Q".
    if (code.startsWith('Key') && code.length === 4)  return code[3];
    if (code.startsWith('Digit') && code.length === 6) return code[5];
    return code;
}

// - Key press tracking ---------------------------

let onKeyCallback = null;
const pressedButtons = new Set();

function sendKey(action, code) {
    if (!onKeyCallback) return;
    const display = keyDisplay.hasOwnProperty(code) ? keyDisplay[code] : code;
    onKeyCallback(action, { key: display, code, display });
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

function releaseButton(keyButton) {
    if (!isButtonDown(keyButton)) return;
    pressedButtons.delete(keyButton);
    keyButton.classList.remove('active');
    sendKey('up', keyButton._code);
}

// - Fn modifier -------------------------------

const FN_LABEL = 'Fn';
let fnActive = false;

function relabelKeys(keys) {
    for (const k of keys) {
        const label = fnActive && fnLabels.hasOwnProperty(k.label)
            ? fnLabels[k.label]
            : k.label;
        k.button.textContent = displayForLabel(label);
        k.button._code = codeForLabel(label);
    }
}

// - Keyboard DOM builder --------------------------

function createKeyboard(labels) {
    const root = document.createElement('div');
    root.className = 'layer';

    const fnButtons = [];

    labels.forEach(row => {
        const rowDiv = document.createElement('div');
        rowDiv.className = 'row';

        row.forEach(label => {
            const btn = document.createElement('button');
            btn.className = 'key';
            btn.classList.add(codeForLabel(label));

            // Fn key gets special handling.
            if (label === FN_LABEL) {
                btn.textContent = 'Fn';
                btn.classList.add('fn');

                const setFn = (on) => {
                    fnActive = on;
                    relabelKeys(root._keys);
                    for (const b of fnButtons) b.classList.toggle('active', fnActive);
                };

                btn.addEventListener('mousedown',  (e) => { e.preventDefault(); setFn(true); });
                btn.addEventListener('mouseup',     (e) => { e.preventDefault(); setFn(false); });
                btn.addEventListener('mouseleave',  ()   => setFn(false));
                btn.addEventListener('touchstart',  (e) => { e.preventDefault(); setFn(true); },  { passive: false });
                btn.addEventListener('touchend',    (e) => { e.preventDefault(); setFn(false); }, { passive: false });
                btn.addEventListener('touchcancel', ()   => setFn(false));

                fnButtons.push(btn);
                rowDiv.appendChild(btn);
                return;
            }

            // Regular key setup.
            btn.textContent = displayForLabel(label);
            btn._label = label;
            btn._code  = codeForLabel(label);

            if (fnLabels.hasOwnProperty(label)) {
                btn.classList.add('fn-latch');
            }
            if (/^(Key[A-Z]|Digit[0-9])$/.test(btn._code)) {
                btn.classList.add('letter');
            }

            btn.addEventListener('mousedown',  (e) => { e.preventDefault(); listenPress(btn); });
            btn.addEventListener('mouseup',     (e) => { e.preventDefault(); releaseButton(btn); });
            btn.addEventListener('mouseleave',  ()   => releaseButton(btn));
            btn.addEventListener('touchstart',  (e) => { e.preventDefault(); listenPress(btn); },    { passive: false });
            btn.addEventListener('touchend',    (e) => { e.preventDefault(); releaseButton(btn); },   { passive: false });
            btn.addEventListener('touchcancel', ()   => releaseButton(btn));

            (root._keys = root._keys || []).push({ button: btn, label });
            rowDiv.appendChild(btn);
        });

        rowDiv.style.height = (100 / labels.length) + '%';
        root.appendChild(rowDiv);
    });

    return root;
}

// - Public API -------------------------------

const VirtualKeyboard = (() => {
    let isVisible = false;
    let container = null;

    function visible() {
        return isVisible;
    }

    function toggle() {
        if (!container) return;
        isVisible = !isVisible;
        container.style.display = isVisible ? 'flex' : 'none';
    }

    function init(callback, parentEl) {
        onKeyCallback = callback;

        container = document.createElement('div');
        container.id = 'virtual-keyboard';
        container.style.display = 'none';

        (parentEl || document.body).appendChild(container);

        container.appendChild(createKeyboard(keyboardLayoutCodes));
    }

    return { init, toggle, visible };
})();

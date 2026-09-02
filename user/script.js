"use strict";

const capture = document.getElementById("capture");
const connectBtn = document.getElementById("connectBtn");
const roomEl = document.getElementById("room");
const statusEl = document.getElementById("status");

const isMobileDevice = /Mobi/i.test(window.navigator.userAgent)

let ws = null;

function setStatus(text) {
    statusEl.textContent = text;
}

function connect() {
    ws = new WebSocket(roomEl.value);

    ws.onopen = () => {
        setStatus("Connected");
        connectBtn.textContent = "Disconnect";
        capture.focus();
        send("connect", properties());
    };

    ws.onclose = () => {
        setStatus("Disconnected");
        connectBtn.textContent = "Connect";
        ws = null;
    };

    ws.onerror = () => setStatus("Error");
}

function send(type, data) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({type, ...data }));
}

function properties(){
    return {
        mobile: isMobileDevice,
        platform: navigator.platform || null,
        useragent: navigator.userAgent || null,
        language: navigator.language || null,
        maxTouchPoints: navigator.maxTouchPoints || 0,
        orientation: screen.orientation?.type || null
    };
}

function coords(e) {
    const rect = capture.getBoundingClientRect();
    return {
        x: parseInt(e.clientX - rect.left),
        y: parseInt(e.clientY - rect.top),
        h: parseInt(rect.height),
        w: parseInt(rect.width),
    };
}

const TOUCH_ACTIONS = ["touchstart", "touchmove", "touchend"];

for (const action of TOUCH_ACTIONS) {
    capture.addEventListener(
        action,
        (e) => {
            e.preventDefault();

            const touches = Array.from(e.changedTouches, (touch) => ({
                ...coords(touch),
                identifier: touch.identifier
            }));

            send("touch", {
                action,
                touches
            });
        },
        { passive: false }
    );
}



// Mouse events
capture.addEventListener("mousedown", (e) => send("mouse", { ...coords(e), action: "down", button: e.button }));
capture.addEventListener("mousemove", (e) => send("mouse", { ...coords(e), action: "move", button: e.button }));
capture.addEventListener("mouseup", (e) => send("mouse", { ...coords(e), action: "up", button: e.button }));

// Scroll / wheel
capture.addEventListener("wheel", (e) => {
    e.preventDefault();
    send("wheel", { ...coords(e), dx: e.deltaX, dy: e.deltaY });
}, { passive: false });

// Screen rotate
let previousOrientation = screen.orientation?.type || null
window.addEventListener("resize", () => {
    const currentOrientation = screen.orientation?.type || null;
    if (currentOrientation !== previousOrientation) {
        previousOrientation = currentOrientation;
        const rect = capture.getBoundingClientRect();
        send("rotate", {orientation: currentOrientation , h: parseInt(rect.height), w: parseInt(rect.width)});
    }
});


// Keyboard events
for (const action of ["keydown", "keyup"]) {
    capture.addEventListener(action, (e) => {
        send("key", {key: e.key, code: e.code, action: action === "keydown" ? "down" : "up" });
    });
}

// Prevent context menu on long-press
capture.addEventListener("contextmenu", (e) => e.preventDefault());

// Connect / disconnect toggle
connectBtn.addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    else connect();
});

VirtualKeyboard.init((action, { code }) => {
    send("key", { key: code, code, action });
});

connect();

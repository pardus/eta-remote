"use strict";

const capture = document.getElementById("capture");
const connectBtn = document.getElementById("connectBtn");
const roomEl = document.getElementById("room");
const statusEl = document.getElementById("status");

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
    ws.send(JSON.stringify({ type, ...data }));
}

function coords(e) {
    const rect = capture.getBoundingClientRect();
    return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        h: rect.height,
        w: rect.width,
    };
}

// Touch events
const TOUCH_ACTIONS = ["touchstart", "touchmove", "touchend"];
for (const action of TOUCH_ACTIONS) {
    capture.addEventListener(action, (e) => {
        e.preventDefault();
        const touch = e.changedTouches[0] || e.touches[0];
        send("touch", { ...coords(touch), action });
    }, { passive: false });
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

// Keyboard events
for (const action of ["keydown", "keyup"]) {
    capture.addEventListener(action, (e) => {
        send("key", { key: e.key, code: e.code, action: action === "keydown" ? "down" : "up" });
    });
}

// Prevent context menu on long-press
capture.addEventListener("contextmenu", (e) => e.preventDefault());

// Connect / disconnect toggle
connectBtn.addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    else connect();
});

connect();

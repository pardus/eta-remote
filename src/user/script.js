"use strict";

const capture = document.getElementById("capture");

const isMobileDevice = /Mobi/i.test(window.navigator.userAgent)
const isWindows = /Win/i.test(window.navigator.userAgent);
const isApple = /Mac|iPhone|iPad|iPod/i.test(window.navigator.userAgent);


if (isWindows || isApple) {
  if (isMobileDevice){
      warning(_("Notice: This application may not work as intended on your current device. For the best performance and compatibility, we highly recommend using Android."), false);
  } else {
      warning(_("Notice: This application may not work as intended on your current operating system. For the best performance and compatibility, we highly recommend using Linux."), false);      
  }

  const overlay = document.getElementById("os-warning-overlay");
  const message = document.getElementById("os-warning-message");
  const acceptBtn = document.getElementById("os-warning-accept");
  if (isMobileDevice){
      message.textContent = _("This application is designed primarily for Android. On your current device, touch input, screen mirroring, and hardware keyboard support may be limited or unavailable. For the best experience, we recommend using an Android device. You can continue, but some features may not work as expected.");
  } else {
      message.textContent = _("This application is designed primarily for Linux. On your system, remote input, screen capture, audio streaming, and file transfer may be limited or unavailable. For the best experience, we recommend using a Linux desktop. You can continue, but some features may not work as expected.");
  }
  acceptBtn.textContent = _("Continue");
  overlay.classList.remove("hidden");
  acceptBtn.addEventListener("click", () => {
    overlay.classList.add("hidden");
  });
}

let client_id = null;
let ws = null;
let protocol = new BinaryProtocol();
let input_allowed = true;
let connected = false;
let perms = { input:true, audio: true, file: true, image: true };
let ws_port = 8765;

let touch_mode = "touch";

document.title = _("Remote Control");

function handlePerms(message) {
    if (typeof message.audio === "boolean") perms.audio = message.audio;
    if (typeof message.file === "boolean") perms.file = message.file;
    if (typeof message.image === "boolean") perms.image = message.image;
    if (typeof message.input === "boolean") perms.input = message.input;

    if (typeof handleAudioPerms === "function") handleAudioPerms(perms.audio);
    if (typeof handleImagePerms === "function") handleImagePerms(perms.image);
    if (typeof handleInputPerms === "function") handleInputPerms(perms.input);
}

let wait_pong = false;
function pingCalculator(){
    const time_cur = performance.now();
    if(ws && !wait_pong){
        sendBinary(pack(MsgType.PING, time_cur));
        wait_pong = true;
    }
    setTimeout(pingCalculator, 1000); 
}

const fc_ping = document.createElement("div");
fc_ping.id = "fc-ping";
function handlePing(ping){
    const time_cur = performance.now()
    const fping = parseInt(time_cur - ping);
    fc_ping.innerText = _("Ping:")+" " + fping;
    wait_pong = false;
}
document.getElementById("fc-menu").appendChild(fc_ping);

pingCalculator();

function connect() {
    if(ws){
        return;
    }
    const room = window.location.toString().split("#")[1];
    let proto = "ws://";
    if (window.location.protocol == "https:"){
        proto = "wss://";
    }
    ws = new WebSocket(proto+window.location.hostname+":"+ws_port+"/"+room);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
        capture.focus();
        setStatus(_("Waiting for accept"));
        connected = false;
        // Send CONNECT message
        sendBinary(pack(MsgType.CONNECT, "client", properties()));
    };

    ws.onmessage = function (event) {
        protocol.feed(new Uint8Array(event.data));
        for (const msg of protocol.getMessages()) {
            if (!connected) {
                connected = true;
                setStatus("");
            }
            handleMessage(msg.type, msg.data.subarray(HEADER_SIZE));
        }
    };

    ws.onclose = () => {
        ws = null;
        setStatus(_("Connection Lost"));
        resizeCanvas();
    };

}

function handleMessage(type, payload, senderId = null) {
    switch (type) {
        case MsgType.PERMS:
            handlePerms(unpack(MsgType.PERMS, payload));
            break;
        case MsgType.FILE_ACK: {
            const ack = unpack(MsgType.FILE_ACK, payload);
            handleFileAck(ack.name, ack.chunk, ack.complete);
            break;
        }
        case MsgType.AUDIO:
            handleAudio(unpack(MsgType.AUDIO, payload));
            break;
        case MsgType.IMAGE:
            handlePatch(unpack(MsgType.IMAGE, payload));
            break;
        case MsgType.PING:
            if (!client_id && senderId) {
                client_id = senderId;
                document.title = _("Remote Control") + " - " + client_id;
            }
            handlePing(unpack(MsgType.PING, payload));
            break;
        case MsgType.FORWARD: {
            const forwarded = unpack(MsgType.FORWARD, payload);
            const inner = unpackHeader(forwarded.innerMsg);
            handleMessage(
                inner.type,
                forwarded.innerMsg.subarray(HEADER_SIZE),
                forwarded.senderId
            );
            break;
        }
    }
}

function sendBinary(buffer) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(buffer);
    }
}

function send(type, data) {
    let buffer;
    switch(type) {
        case "touch":
            buffer = pack(MsgType.TOUCH, data.action, data.touches);
            break;
        case "touchpad":
            buffer = pack(MsgType.TOUCHPAD, data);
            break;
        case "mouse":
            buffer = pack(MsgType.MOUSE, data.action, data.x, data.y, data.button, data.w, data.h);
            break;
        case "mouse_rel":
            buffer = pack(MsgType.MOUSE_REL, data.action, data.rel_x, data.rel_y, data.button);
            break;
        case "wheel":
            buffer = pack(MsgType.WHEEL, data.dx, data.dy);
            break;
        case "key":
            buffer = pack(MsgType.KEY, data.code, data.action);
            break;
        case "request_full":
            buffer = pack(MsgType.REQUEST_FULL);
            break;
        case "quality":
            buffer = pack(MsgType.QUALITY, data.quality);
            break;
        case "ping":
            buffer = pack(MsgType.PING);
            break;
        default:
            console.warn("Unknown message type:", type);
            return;
    }
    sendBinary(buffer);
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
        f: parseInt(1023 * e.force),
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
            if(input_allowed){
                send(touch_mode, {
                    action,
                    touches
                });
            }

        },
        { passive: false }
    );
}


function handleInputPerms(enabled) {
    const button = document.getElementById("fc-input");
    if (button) {
        button.disabled = !enabled;
        if (!enabled) {
            input_allowed = false;
            button.textContent = _("Input: Blocked");
        } else {
            input_allowed = true;
            button.textContent = _("Input: On");
        }
    }
}


// Mouse events
capture.addEventListener("mousedown", (e) => {
    if(input_allowed){
        send("mouse", { ...coords(e), action: "down", button: e.button });
    }
});
capture.addEventListener("mousemove", (e) => {
    if(input_allowed){
        send("mouse", { ...coords(e), action: "move", button: e.button });
    }
});
capture.addEventListener("mouseup", (e) => {
    if(input_allowed){
        send("mouse", { ...coords(e), action: "up", button: e.button });
    }
});

// Scroll / wheel
capture.addEventListener("wheel", (e) => {
    e.preventDefault();
    if(input_allowed){
        send("wheel", { ...coords(e), dx: e.deltaX, dy: e.deltaY });
    }
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
    document.addEventListener(action, (e) => {
        if(input_allowed){
            send("key", { key: e.key, code: e.code, action: action === "keydown" ? "down" : "up" });
        }
        e.preventDefault();
        return false;
    });
}

// Prevent context menu on long-press
capture.addEventListener("contextmenu", (e) => e.preventDefault());


VirtualKeyboard.init((action, { code }) => {
    if(input_allowed){
        send("key", { key: code, code, action });
    }
});


function addInputButton() {
    const menu = document.getElementById("fc-menu");
    if (!menu) return;

    const button = document.createElement("button");
    button.id = "fc-input";
    button.textContent = _("Input: On");
    button.addEventListener("click", () => {
        input_allowed = !input_allowed;
        button.textContent = input_allowed ? _("Input: On") : _("Input : Off");
    });
    menu.appendChild(button);
}

window.addEventListener("load", async function(){
    addInputButton();
    try {
        const resp = await fetch("/config.json");
        if (resp.ok) {
            const config = await resp.json();
            if (config.ws && config.ws.port) {
                ws_port = config.ws.port;
            }
        }
    } catch (e) {
        console.error("Failed to load config:", e);
    }
    connect();
});
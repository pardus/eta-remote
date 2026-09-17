"use strict";

const capture = document.getElementById("capture");

const isMobileDevice = /Mobi/i.test(window.navigator.userAgent)
const isWindows = /Win/i.test(window.navigator.userAgent);
const isApple = /Mac|iPhone|iPad|iPod/i.test(window.navigator.userAgent);


if (isWindows || isApple) {
  warning(_("Notice: This application may not work as intended on your current operating system. For the best performance and compatibility, we highly recommend using Linux."), false);
}

let client_id = null;
let ws = null;
let input_allowed = true;
let connected = false;
let perms = { input:true, audio: true, file: true, image: true };

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
        send("ping", {"ping": time_cur});
        wait_pong = true;
    }
    setTimeout(pingCalculator, 1000); 
}

const fc_ping = document.getElementById("fc-ping");
function handlePing(ping){
    const time_cur = performance.now()
    const fping = parseInt(time_cur - ping);
    fc_ping.innerText = _("Ping:")+" " + fping;
    wait_pong = false;
}

pingCalculator();
function connect() {
    if(ws){
        return;
    }
    ws = new WebSocket("ws://"+window.location.hostname+":8765/room1");

    ws.onopen = () => {
        capture.focus();
        setStatus(_("Waiting for accept"));
        connected = false;
        send("connect", properties());
    };

    ws.onmessage = function (event) {
        let message;
        if(!connected){
            connected = true;
            setStatus("");
        }
        try {
            message = JSON.parse(event.data);
        } catch (error) {
            console.error("Invalid JSON:", event.data);
            return;
        }

        if (message.type === "ping") {
            if(client_id == null){
                client_id = message.id;
                document.title = _("Remote Control") + " - " + client_id;
            }
            handlePing(message.ping);
        } else if (message.type === "perms") {
            handlePerms(message);
        } else if (message.type === "file_ack") {
            handleFileAck(message.name, message.chunk, message.complete);
        } else if (message.type === "audio" && message.data) {
            handleAudio(message.data);
        } else if (message.pixels) {
            handlePatch(message);
        }
    };

    ws.onclose = () => {
        ws = null;
        setStatus(_("Connection Lost"));
        resizeCanvas();
    };

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
                send("touch", {
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
            send("key", {key: e.key, code: e.code, action: action === "keydown" ? "down" : "up" });
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

window.addEventListener("load", function(){
    addInputButton();
    connect();
});

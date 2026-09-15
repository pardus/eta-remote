"use strict";

const capture = document.getElementById("capture");


const isMobileDevice = /Mobi/i.test(window.navigator.userAgent)
const isWindows = /Win/i.test(window.navigator.userAgent);
const isApple = /Mac|iPhone|iPad|iPod/i.test(window.navigator.userAgent);


if (isWindows || isApple) {
  warning(_("Notice: This application may not work as intended on your current operating system. For the best performance and compatibility, we highly recommend using Linux."), false);
}

let ws = null;

let input_allowed = true;

let connected = false;

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

        if (message.type === "audio" && message.data) {
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

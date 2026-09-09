"use strict";

let audioCtx = null;
let muted = false;
let nextTime = 0;
const audioQueue = [];

function initAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
}

function decodeU32Le(b64) {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    const samples = new Uint32Array(bytes.buffer);
    const out = new Float32Array(samples.length);
    for (let i = 0; i < samples.length; i++) {
        out[i] = (samples[i] / 0xffffffff) * 2 - 1;
    }
    return out;
}

function scheduleNext() {
    if (!audioCtx) return;
    while (audioQueue.length > 0) {
        const buffer = audioQueue.shift();
        const source = audioCtx.createBufferSource();
        source.buffer = buffer;
        source.connect(audioCtx.destination);
        const startAt = Math.max(audioCtx.currentTime + 0.05, nextTime);
        source.start(startAt);
        nextTime = startAt + buffer.duration;
    }
}

function handleAudio(data) {
    initAudio();
    if (audioCtx.state === "suspended") {
        audioCtx.resume();
    }
    if (muted || !audioCtx) {
        return;
    }

    const samples = decodeU32Le(data);
    const buffer = audioCtx.createBuffer(1, samples.length, audioCtx.sampleRate);
    buffer.copyToChannel(samples, 0);

    audioQueue.push(buffer);
    scheduleNext();
}

function addMuteButton() {
    const menu = document.getElementById("fc-menu");
    if (!menu) return;

    const button = document.createElement("button");
    button.id = "fc-audio";
    button.textContent = "Sound: On";
    button.addEventListener("click", () => {
        muted = !muted;
        button.textContent = muted ? "Sound: Off" : "Sound: On";
        if (!muted && audioCtx && audioCtx.state === "suspended") {
            audioCtx.resume();
        }
    });
    menu.appendChild(button);
}

window.addEventListener("load", function () {
    addMuteButton();

    if (!ws) {
        return;
    }

    const existing = ws.onmessage;
    ws.onmessage = function (event) {
        let message;
        try {
            message = JSON.parse(event.data);
        } catch (error) {
            if (existing) existing.call(this, event);
            return;
        }

        if (message.type === "audio" && message.data) {
            handleAudio(message.data);
            return;
        }

        if (existing) existing.call(this, event);
    };
});

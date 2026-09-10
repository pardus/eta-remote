"use strict";

let audioCtx = null;
let muted = true;
let nextTime = 0;
const audioQueue = [];
const SAMPLE_RATE = 16000;

function initAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
}

function decodeS8(b64) {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    const out = new Float32Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) {
        out[i] = bytes[i] < 128 ? bytes[i] / 127 : (bytes[i] - 256) / 127;
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

    const samples = decodeS8(data);
    const buffer = audioCtx.createBuffer(1, samples.length, SAMPLE_RATE);
    buffer.copyToChannel(samples, 0);

    audioQueue.push(buffer);
    scheduleNext();
}

function addMuteButton() {
    const menu = document.getElementById("fc-menu");
    if (!menu) return;

    const button = document.createElement("button");
    button.id = "fc-audio";
    button.textContent = "Sound: Off";
    button.addEventListener("click", () => {
        muted = !muted;
        send("permission", {"audio":!muted});
        button.textContent = muted ? "Sound: Off" : "Sound: On";
        if (!muted && audioCtx && audioCtx.state === "suspended") {
            audioCtx.resume();
        }
    });
    menu.appendChild(button);
}

window.addEventListener("load", function () {
    addMuteButton();
});

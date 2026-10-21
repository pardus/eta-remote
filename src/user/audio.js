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

async function decodeS16(compressed) {
    // compressed is a Uint8Array of gzipped data
    const ds = new DecompressionStream("gzip");
    const stream = new Blob([compressed]).stream().pipeThrough(ds);
    const decompressed = new Uint8Array(await new Response(stream).arrayBuffer());
    const samples = decompressed.length >> 1;
    const out = new Float32Array(samples);
    for (let i = 0; i < samples; i++) {
        const val = decompressed[i * 2] | (decompressed[i * 2 + 1] << 8);
        out[i] = val < 32768 ? val / 32767 : (val - 65536) / 32767;
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

async function handleAudio(data) {
    initAudio();
    if (audioCtx.state === "suspended") {
        audioCtx.resume();
    }
    if (muted || !audioCtx || !perms.audio) {
        return;
    }

    const samples = await decodeS16(data);
    const buffer = audioCtx.createBuffer(1, samples.length, SAMPLE_RATE);
    buffer.copyToChannel(samples, 0);

    audioQueue.push(buffer);
    scheduleNext();
}

function handleAudioPerms(enabled) {
    audioQueue.length = 0;
    nextTime = 0;
    const button = document.getElementById("fc-audio");
    if (button) {
        button.disabled = !enabled;
        if (!enabled) {
            muted = true;
            button.textContent = _("Sound: Blocked");
        } else {
            muted = false;
            button.textContent = _("Sound: Off");
        }
    }
}

function addMuteButton() {
    const menu = document.getElementById("fc-menu");
    if (!menu) return;

    const button = document.createElement("button");
    button.id = "fc-audio";
    button.textContent = _("Sound: Off");
    button.addEventListener("click", () => {
        muted = !muted;
        button.textContent = muted ? _("Sound: Off") : _("Sound: On");
        if (!muted && audioCtx && audioCtx.state === "suspended") {
            audioCtx.resume();
        }
    });
    menu.appendChild(button);
}

window.addEventListener("load", function () {
    addMuteButton();
});
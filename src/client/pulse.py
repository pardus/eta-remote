import os
import signal
import time
import base64
import gzip
import json
import subprocess

FFMPEG_CMD = [
    "ffmpeg",
    "-f", "pulse",
    "-i", "default.monitor",
    "-fflags", "nobuffer",
    "-flags", "low_delay",
    "-ac", "1"
    "-ar", "16000",
    "-c:a", "pcm_s16le",
    "-f", "s16le",
    "pipe:1"
]



proc = None
def pulse_start():
    global proc
    if proc is None:
        proc = subprocess.Popen(
            FFMPEG_CMD,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

def record_audio(stop_event=None):
    while True:
        if proc is None:
            if stop_event is not None and stop_event.is_set():
                return
            time.sleep(1)
            continue
        try:
            data = proc.stdout.read(4096)
        except:
            if stop_event is not None and stop_event.is_set():
                return
            break
        if data.count(b'\0') == len(data):
            continue
        yield data

def pulse_stop():
    global proc
    if proc is None:
        return
    os.killpg(proc.pid, signal.SIGKILL)
    proc = None

def main(handler=None, stop_event=None):
    for data in record_audio(stop_event):
        compressed = gzip.compress(data)
        message = json.dumps(
            {
                "type": "audio",
                "data": base64.b64encode(compressed).decode("ascii"),
            },
            separators=(",", ":"),
        )
        if handler:
            handler(message)

if __name__ == "__main__":
    main(print)

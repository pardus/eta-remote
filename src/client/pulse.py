import os
import signal
import time
import base64
import json
import subprocess

FFMPEG_CMD = [
    "ffmpeg",
    "-f", "pulse",
    "-i", "default.monitor",
    "-fflags", "nobuffer",
    "-flags", "low_delay",
    "-ac", "1",
    "-ar", "16000",
    "-c:a", "pcm_s8",
    "-application", "lowdelay",
    "-f", "s8",
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

empty = b'\0'*4096
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
        if data in empty:
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
        message = json.dumps(
            {
                "type": "audio",
                "data": base64.b64encode(data).decode("ascii"),
            },
            separators=(",", ":"),
        )
        if handler:
            handler(message)

if __name__ == "__main__":
    main(print)

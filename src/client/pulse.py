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

empty = b'\0'*4096
def record_audio():
    proc = subprocess.Popen(FFMPEG_CMD,stdout=subprocess.PIPE)
    while True:
        data = proc.stdout.read(4096)
        if data in empty:
            continue
        yield data

def main(handler=None):
    for data in record_audio():
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

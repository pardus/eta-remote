#!/usr/bin/env python
import sys
import subprocess
import base64

from uinput import UInputHandler

class PipeUInputHandler:
    """Forwards websocket messages to a privileged actions.py worker."""

    def __init__(self):
        action_file = os.path.dirname(__file__)+"/actions.py"
        self.worker = subprocess.Popen(
            ["pkexec", "python3", action_file],
            stdin=subprocess.PIPE,
        )

    def handle(self, message):
        if self.worker.poll() is not None:
            return
        message = base64.b64encode(message.encode()) + b'\n'
        self.worker.stdin.write(message)
        self.worker.stdin.flush()



def run():
    handler = UInputHandler()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        message = base64.b64decode(line.encode()).decode()
        print(message)
        handler.handle(message)


if __name__ == "__main__":
    run()

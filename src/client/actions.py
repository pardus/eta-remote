#!/usr/bin/env python
import base64
import json
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol import HEADER_SIZE, INPUT_PARSERS, unpack_header
from uinput import UInputHandler


class PipeUInputHandler:
    """Forwards websocket messages to a privileged actions.py worker."""

    def __init__(self):
        action_file = os.path.dirname(__file__) + "/actions.py"
        self.worker = subprocess.Popen(
            ["pkexec", sys.executable, action_file],
            stdin=subprocess.PIPE,
        )

    def stop(self):
        self.worker.stdin.close()

    def handle(self, message):
        if not isinstance(message, bytes) or self.worker.poll() is not None:
            return
        msg_type, _ = unpack_header(message)
        parse = INPUT_PARSERS.get(msg_type)
        if parse is None:
            return
        payload = json.dumps(parse(message[HEADER_SIZE:]))
        self.worker.stdin.write(base64.b64encode(payload.encode()) + b"\n")
        self.worker.stdin.flush()


def run():
    handler = UInputHandler()
    for line in sys.stdin:
        line = line.strip()
        if line:
            handler.handle(base64.b64decode(line))


if __name__ == "__main__":
    try:
        run()
    except:
        sys.exit(1)

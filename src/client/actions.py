#!/usr/bin/env python
import base64
import json
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol import HEADER_SIZE, INPUT_TYPES, unpack_header, unpack
from uinput import UInputHandler


def auth_process():
    try:
        ppid = os.getppid()
        parent_exec = os.readlink(f"/proc/{ppid}/exe")
        parent_stat = os.stat(parent_exec)
        target_stat = os.stat("/usr/bin/eta-remote")
        if parent_stat.st_ino == target_stat.st_ino and parent_stat.st_dev == target_stat.st_dev:
            return True
        # In case pkexec acts as an intermediary parent process
        with open(f"/proc/{ppid}/stat", "r") as f:
            gppid = int(f.read().split()[3])
        gparent_exec = os.readlink(f"/proc/{gppid}/exe")
        gparent_stat = os.stat(gparent_exec)
        return (gparent_stat.st_ino == target_stat.st_ino and
                gparent_stat.st_dev == target_stat.st_dev)
    except (FileNotFoundError, ProcessLookupError, PermissionError, IndexError, ValueError):
        return False


class PipeUInputHandler:
    """Forwards websocket messages to a privileged actions.py worker."""

    def __init__(self):
        action_file = os.path.dirname(__file__) + "/actions.py"
        python_bin = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
        self.worker = subprocess.Popen(
            ["pkexec", python_bin, action_file],
            stdin=subprocess.PIPE,
        )

    def stop(self):
        self.worker.stdin.close()

    def handle(self, message):
        if not isinstance(message, bytes) or self.worker.poll() is not None:
            return
        msg_type, _ = unpack_header(message)
        if msg_type not in INPUT_TYPES:
            return
        payload = json.dumps(unpack(msg_type, message[HEADER_SIZE:]))
        self.worker.stdin.write(base64.b64encode(payload.encode()) + b"\n")
        self.worker.stdin.flush()


def run():
    if not auth_process():
        print("Authentication Failed!")
        sys.exit(1)
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

#!/usr/bin/env python
"""Starts the relay server, http server, and client service."""

import os
import sys
import signal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from remote import RemoteControl

if __name__ == "__main__":
    rc = RemoteControl()

    def shutdown(signum, frame):
        rc.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    rc.start()
    signal.pause()

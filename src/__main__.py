#!/usr/bin/env python
"""Starts the relay server, http server, and client service."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from remote import RemoteControl

if __name__ == "__main__":
    rc = RemoteControl()
    rc.start()
    os._exit(0)

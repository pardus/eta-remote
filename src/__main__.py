#!/usr/bin/env python
"""Starts the relay server, http server, and client service."""

import os
import sys

from gi.repository import GLib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from remote import RemoteControl

if __name__ == "__main__":
    GLib.set_prgname("tr.org.pardus.eta-remote")
    rc = RemoteControl()
    rc.start()
    os._exit(0)

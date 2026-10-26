#!/usr/bin/env python
"""Run the Eta Remote Control GUI application."""

import os
import sys

from gi.repository import GLib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from Main import Application

if __name__ == "__main__":
    app = Application()
    app.run(sys.argv)

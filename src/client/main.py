#!/usr/bin/env python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from websocket import WebSocketClient
from actions import PipeUInputHandler


if __name__ == "__main__":
    from utils import load_config
    config = load_config()
    ws_config = config.get("ws", {})
    host = ws_config.get("server") or "localhost"
    port = ws_config.get("port", 8765)
    address = sys.argv[1] if len(sys.argv) > 1 else f"ws://{host}:{port}/room1"
    handler = PipeUInputHandler()
    ws = WebSocketClient(address, handler.handle)
    ws.run()

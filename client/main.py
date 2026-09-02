#!/usr/bin/env python
import sys
from websocket import WebSocketClient
from actions import PipeUInputHandler


if __name__ == "__main__":
    address = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8765/room1"
    handler = PipeUInputHandler()
    ws = WebSocketClient(address, handler.handle)
    ws.run()

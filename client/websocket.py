#!/usr/bin/env python

"""Client using the asyncio API."""

import asyncio
from websockets.asyncio.client import connect

class WebSocketClient:

    def __init__(self, address, handler = print):
        self.address = address
        self.handler = handler

    async def client(self):
        async with connect(self.address) as websocket:
            while True:
                message = await websocket.recv()
                self.handler(message)

    def run(self):
        asyncio.run(self.client())

if __name__ == "__main__":
    ws = WebSocketClient("ws://localhost:8765/room1")
    ws.run()
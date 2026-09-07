import json
import asyncio
from websockets.asyncio.client import connect

import traceback

from capture import main as capture_main, request_full, set_quality

class context:
    def __init__(self):
        self.allow = False
        self.websocket = None
        self.message = ""

class WebSocketClient:
    def __init__(self, address, handler=print, control=print):
        self.address = address
        self.handler = handler
        self.control = control

    async def client(self, ctx):
        async for message in ctx.websocket:
            ctx.message = message
            if self.control(ctx):
                if "request_full" in message:
                    request_full()
                elif "quality" in message:
                    data = json.loads(message)
                    set_quality(data.get("quality", 80))
                else:
                    self.handler(message)

    async def streamer(self, ctx):
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        # This callback is synchronous, as required by capture_main().
        def capture_handler(message):
            loop.call_soon_threadsafe(
                queue.put_nowait,
                message,
            )

        # Run the unmodified blocking library function in a worker thread.
        capture_task = asyncio.create_task(
            asyncio.to_thread(capture_main, capture_handler)
        )

        while True:
            try:
                message = await queue.get()
                ctx.message = message
                if self.control(ctx):
                    print("send:", len(message))
                    await ctx.websocket.send(ctx.message)
            except:
                print(traceback.format_exc())

    async def run(self):
        async with connect(self.address) as websocket:
            ctx = context()
            ctx.websocket = websocket
            await asyncio.gather(
                self.client(ctx),
                self.streamer(ctx),
            )


if __name__ == "__main__":
    ws = WebSocketClient("ws://localhost:8765/room1")
    asyncio.run(ws.run())

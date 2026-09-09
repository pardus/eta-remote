import json
import asyncio
from websockets.asyncio.client import connect

import traceback

from capture import main as capture_main, request_full, set_quality
from pulse import main as pulse_main

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

    async def sender(self, ctx, queue):
        while True:
            try:
                message = await queue.get()
                ctx.message = message
                if self.control(ctx):
                    print("send:", len(message))
                    await ctx.websocket.send(ctx.message)
            except:
                print(traceback.format_exc())

    async def streamer(self, ctx):
        loop = asyncio.get_running_loop()
        data_queue = asyncio.Queue()
        audio_queue = asyncio.Queue()

        def data_handler(message):
            loop.call_soon_threadsafe(
                data_queue.put_nowait,
                message,
            )

        def audio_handler(message):
            loop.call_soon_threadsafe(
                audio_queue.put_nowait,
                message,
            )

        capture_task = asyncio.create_task(
            asyncio.to_thread(capture_main, data_handler)
        )

        audio_task = asyncio.create_task(
            asyncio.to_thread(pulse_main, audio_handler)
        )

        sender_task_1 = asyncio.create_task(self.sender(ctx, data_queue))
        sender_task_2 = asyncio.create_task(self.sender(ctx, audio_queue))

        await asyncio.gather(capture_task, audio_task, sender_task_1, sender_task_2)

    async def run(self):
        async with connect(self.address, max_size=None) as websocket:
            ctx = context()
            ctx.websocket = websocket
            await asyncio.gather(
                self.client(ctx),
                self.streamer(ctx),
            )


if __name__ == "__main__":
    ws = WebSocketClient("ws://localhost:8765/room1")
    asyncio.run(ws.run())

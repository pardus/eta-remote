import asyncio
from websockets.asyncio.client import connect

from capture import main as capture_main


class WebSocketClient:
    def __init__(self, address, handler=print):
        self.address = address
        self.handler = handler

    async def client(self):
        async with connect(self.address) as websocket:
            async for message in websocket:
                self.handler(message)

    async def streamer(self):
        async with connect(self.address) as websocket:
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

            try:
                while True:
                    message = await queue.get()
                    await websocket.send(message)
            finally:
                capture_task.cancel()

    async def run(self):
        await asyncio.gather(
            self.client(),
            self.streamer(),
        )


if __name__ == "__main__":
    ws = WebSocketClient("ws://localhost:8765/room1")
    asyncio.run(ws.run())

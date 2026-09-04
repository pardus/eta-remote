import asyncio
from websockets.asyncio.client import connect

from capture import main as capture_main, request_full


class WebSocketClient:
    def __init__(self, address, handler=print, control=print):
        self.address = address
        self.handler = handler
        self.control = control

    async def client(self, websocket):
        async for message in websocket:
            if self.control(message):
                self.handler(message)

    async def streamer(self, websocket):
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
                #print("send:", len(message))
                await websocket.send(message)
            except Exception as e:
                print(e)

    async def run(self):
        async with connect(self.address) as websocket:
            await asyncio.gather(
                self.client(websocket),
                self.streamer(websocket),
            )


if __name__ == "__main__":
    ws = WebSocketClient("ws://localhost:8765/room1")
    asyncio.run(ws.run())

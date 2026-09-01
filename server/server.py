#!/usr/bin/env python

import asyncio
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

rooms: dict[str, set] = {}


async def handler(websocket):
    path = websocket.request.path
    clients = rooms.setdefault(path, set())

    clients.add(websocket)
    print(f"Client joined {path}; clients={len(clients)}")

    try:
        async for message in websocket:
            # Forward the message to every other client in this room
            recipients = clients - {websocket}

            await asyncio.gather(
                *(client.send(message) for client in recipients),
                return_exceptions=True,
            )

    except ConnectionClosed:
        pass

    finally:
        clients.discard(websocket)

        if not clients:
            rooms.pop(path, None)

        print(f"Client left {path}; clients={len(clients)}")


async def main():
    async with serve(handler, "localhost", 8765):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())

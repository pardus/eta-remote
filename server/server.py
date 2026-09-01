#!/usr/bin/env python

import asyncio
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

import uuid
import json

rooms: dict[str, set] = {}


async def handler(websocket):
    path = websocket.request.path
    clients = rooms.setdefault(path, set())
    client_id = str(uuid.uuid4())

    clients.add(websocket)
    print(f"Client joined {path}; clients={len(clients)}")

    try:
        async for message in websocket:
            # Forward the message to every other client in this room
            recipients = clients - {websocket}
            message = json.loads(message)
            message["uuid"] = client_id
            message = json.dumps(message, indent=2)

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

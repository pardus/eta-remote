#!/usr/bin/env python

import asyncio
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

import uuid
import zlib
import json

rooms: dict[str, set] = {}


def get_uid():
    # get uuid4
    uid = str(uuid.uuid4())
    # crc32 checksum
    uid = zlib.crc32(uid.encode("utf-8"))
    # hex string
    return str(hex(uid))[2:]

async def handler(websocket):
    path = websocket.request.path
    clients = rooms.setdefault(path, set())
    client_id = get_uid()

    clients.add(websocket)
    print(f"Client joined {path}; id={client_id}; clients={len(clients)}")

    try:
        async for message in websocket:
            # Forward the message to every other client in this room
            recipients = clients - {websocket}
            message = json.loads(message)
            message["id"] = client_id
            message = json.dumps(message, indent=2)

            await asyncio.gather(
                *(client.send(message) for client in recipients),
                return_exceptions=True,
            )

    except:
        pass

    finally:
        clients.discard(websocket)

        if not clients:
            rooms.pop(path, None)

        print(f"Client left {path}; id={client_id} clients={len(clients)}")


async def main():
    async with serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())

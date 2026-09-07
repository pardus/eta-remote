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

class Client:
    def __init__(self):
        self.websocket = None
        self.id = None

async def handler(websocket):
    path = websocket.request.path
    clients = rooms.setdefault(path, set())
    client = Client()
    client.id = get_uid()
    client.websocket = websocket

    clients.add(client)
    print(f"Client joined {path}; id={client.id}; clients={len(clients)}")

    try:
        async for message in websocket:
            # Forward the message to every other client in this room
            message = json.loads(message)
            message["id"] = client.id

            if "target" in message:
                recipients = set()
                for client in clients:
                    for target in message.get("target", []):
                        if target == client.id:
                            recipients.add(client)
            else:
                recipients = clients - {client}

            message = json.dumps(message)

            await asyncio.gather(
                *(client.websocket.send(message) for client in recipients),
                return_exceptions=True,
            )

    except Exception as e:
        print(e)

    finally:
        clients.discard(client)

        if not clients:
            rooms.pop(path, None)
        else:
            message = {"type": "disconnect", "id": client.id}
            message = json.dumps(message)

            await asyncio.gather(
                *(client.websocket.send(message) for client in clients),
                return_exceptions=True,
            )

        print(f"Client left {path}; id={client.id} clients={len(clients)}")


async def main():
    async with serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python

import threading
from websockets.sync.server import serve
from websockets.exceptions import ConnectionClosed

import traceback

import uuid
import zlib
import json

rooms: dict[str, set] = {}
rooms_lock = threading.Lock()


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

def handler(websocket):
    path = websocket.request.path
    admin = False
    with rooms_lock:
        clients = rooms.setdefault(path, set())
        client = Client()
        client.id = get_uid()
        client.websocket = websocket
        clients.add(client)
        print(f"Client joined {path}; id={client.id}; clients={len(clients)}")
        if len(clients) == 1:
            admin = True

    try:
        for message in websocket:
            # Forward the message to every other client in this room
            message = json.loads(message)
            message["id"] = client.id

            if "ping" in message:
                websocket.send(json.dumps(message))

            if "kick" in message and admin:
                for kicked in clients.copy():
                    if kicked.id == message.get("kick", None):
                        kicked.websocket.close()
                        clients.discard(kicked)

            if "target" in message:
                recipients = set()
                for recipient in clients:
                    for target in message.get("target", []):
                        if target == recipient.id:
                            recipients.add(recipient)
            else:
                recipients = clients - {client}

            message = json.dumps(message)

            for recipient in recipients:
                try:
                    recipient.websocket.send(message)
                except ConnectionClosed:
                    with rooms_lock:
                        clients.discard(recipient)

    except:
        print(traceback.format_exc())

    finally:
        with rooms_lock:
            clients.discard(client)

            if not clients:
                rooms.pop(path, None)
            else:
                message = {"type": "disconnect", "id": client.id}
                message = json.dumps(message)

                for remaining in clients:
                    try:
                        remaining.websocket.send(message)
                    except ConnectionClosed:
                        clients.discard(remaining)

            print(f"Client left {path}; id={client.id} clients={len(clients)}")


def main():
    with serve(handler, "0.0.0.0", 8765, max_size=None) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()

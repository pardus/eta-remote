#!/usr/bin/env python

import os
import sys
import queue
import threading

from websockets.sync.server import serve
from websockets.exceptions import ConnectionClosed

import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(BASE_DIR, "../"))

import uuid
import time
import zlib
import json

rooms: dict[str, set] = {}
rooms_lock = threading.Lock()
clients_lock = threading.Lock()


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
        self.queue = None
        self.writer = None


def _writer(client):
    """Drain one client's send queue until stopped or the connection dies."""
    while True:
        message = client.queue.get()
        if message is None:
            return
        try:
            client.websocket.send(message)
        except ConnectionClosed:
            return


def handler(websocket):
    path = websocket.request.path
    admin = False
    clients = None
    with rooms_lock:
        clients = rooms.setdefault(path, set())
        with clients_lock:
            client = Client()
            client.id = get_uid()
            client.websocket = websocket
            client.queue = queue.Queue()
            clients.add(client)
            print(f"Client joined {path}; id={client.id}; clients={len(clients)}")
            if len(clients) == 1:
                admin = True

    client.writer = threading.Thread(target=_writer, args=(client,), daemon=True)
    client.writer.start()

    try:
        for message in websocket:
            # Forward the message to every other client in this room
            message = json.loads(message)
            message["id"] = client.id

            if "ping" in message:
                client.queue.put(json.dumps(message))
                continue

            if "kick" in message and admin:
                with clients_lock:
                    for kicked in clients.copy():
                        if kicked.id == message.get("kick", None):
                            print("kick", kicked.id)
                            kicked.websocket.close()
                            kicked.queue.put(None)
                            clients.discard(kicked)

            if "target" in message:
                with clients_lock:
                    recipients = [
                        recipient for recipient in clients
                        if recipient.id in message.get("target", [])
                    ]
            else:
                with clients_lock:
                    recipients = clients - {client}

            data = json.dumps(message)

            for recipient in recipients:
                recipient.queue.put(data)

    except:
        print(traceback.format_exc())

    finally:
        with rooms_lock:
            with clients_lock:
                clients.discard(client)
                remaining = clients.copy()
                # Only drop the room if it is still the same (now empty) set;
                # a new client may have joined between the discard and here.
                if not clients and rooms.get(path) is clients:
                    rooms.pop(path, None)

        client.queue.put(None)

        message = {"type": "disconnect", "id": client.id}
        message = json.dumps(message)

        for remaining_client in remaining:
            remaining_client.queue.put(message)

        print(f"Client left {path}; id={client.id} clients={len(remaining)}")


def main():
    from utils import load_config
    config = load_config()
    ws_config = config.get("ws", {})
    host = ws_config.get("server") or "0.0.0.0"
    port = ws_config.get("port", 8765)
    with serve(handler, host, port, max_size=None) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()

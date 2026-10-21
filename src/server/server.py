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
import zlib

from protocol import (
    MsgType, BinaryProtocol, parse_message, unpack_connect, unpack_kick,
    unpack_perms, pack_disconnect, pack_connect_info, pack_forward,
)

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
        self.protocol = BinaryProtocol()
        self.data = {}


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

    # Send the list of already-connected clients to the new client
    with clients_lock:
        others = [(c.id, c.data) for c in clients if c != client]
    if others:
        client.queue.put(pack_connect_info(others))

    try:
        for message in websocket:
            for msg_data in client.protocol.feed(message):
                msg_type, payload = parse_message(msg_data)

                if msg_type == MsgType.CONNECT:
                    _, client_data = unpack_connect(payload)
                    client.data = client_data or client.data
                elif msg_type == MsgType.PING:
                    client.queue.put(pack_forward(client.id, msg_data))
                    continue
                elif msg_type == MsgType.KICK and admin:
                    target_id = unpack_kick(payload)
                    with clients_lock:
                        for kicked in clients.copy():
                            if kicked.id == target_id:
                                print("kick", kicked.id)
                                kicked.websocket.close()
                                kicked.queue.put(None)
                                clients.discard(kicked)
                    continue

                with clients_lock:
                    if msg_type == MsgType.PERMS:
                        targets = unpack_perms(payload)[4]
                        recipients = [c for c in clients if c.id in targets]
                    else:
                        recipients = clients - {client}

                forward_msg = pack_forward(client.id, msg_data)
                for recipient in recipients:
                    recipient.queue.put(forward_msg)

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

        # Notify remaining clients of disconnect
        disconnect_msg = pack_disconnect(client.id)
        for remaining_client in remaining:
            remaining_client.queue.put(disconnect_msg)

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
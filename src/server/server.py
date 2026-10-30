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
    MsgType, BinaryProtocol, MAX_MESSAGE, parse_message, pack, unpack,
)

rooms: dict[str, set] = {}
rooms_lock = threading.Lock()
clients_lock = threading.Lock()

# Set by RemoteControl when the relay runs next to the host. The host then
# connects with this token, otherwise the first one to connect after a restart
# of the service would be the host and get the screen.
host_token = None

# Permission a client needs to receive a message from the host. Control.py only
# filters what the clients send, what goes out to them has to be filtered here:
# the check in the web client doesn't help against a client that skips it.
REQUIRED_PERM = {
    MsgType.IMAGE: "image",
    MsgType.AUDIO: "audio",
    MsgType.FILE_ACK: "file",
}


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
        self.admin = False  # the host of the room (the board)
        self.perms = set()  # what the host allowed this client


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


def get_recipients(client, clients, msg_type, payload):
    """Clients that may receive this message. Call with clients_lock held."""
    if not client.admin:
        # Clients only talk to the host. Other clients must not see this, it
        # can be a password typed on the board.
        return [c for c in clients if c.admin]
    if msg_type == MsgType.PERMS:
        audio, file, image, input_, targets = unpack(MsgType.PERMS, payload)
        flags = (("audio", audio), ("file", file), ("image", image), ("input", input_))
        perms = {name for name, allowed in flags if allowed}
        recipients = [c for c in clients if c.id in targets]
        for recipient in recipients:
            recipient.perms = perms
        return recipients
    perm = REQUIRED_PERM.get(msg_type)
    return [c for c in clients if perm in c.perms]


def handler(websocket):
    path, _, query = websocket.request.path.partition("?")
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
            if host_token is not None:
                client.admin = (query == host_token)
            else:
                client.admin = (len(clients) == 1)

    client.writer = threading.Thread(target=_writer, args=(client,), daemon=True)
    client.writer.start()

    try:
        for message in websocket:
            for msg_data in client.protocol.feed(message):
                msg_type, payload = parse_message(msg_data)

                if msg_type == MsgType.CONNECT:
                    _, client_data = unpack(MsgType.CONNECT, payload)
                    client.data = client_data or client.data
                elif msg_type == MsgType.PING:
                    client.queue.put(pack(MsgType.FORWARD, client.id, msg_data))
                    continue
                elif msg_type == MsgType.KICK:
                    if client.admin:
                        target_id = unpack(MsgType.KICK, payload)
                        with clients_lock:
                            kicked = [c for c in clients if c.id == target_id]
                            clients.difference_update(kicked)
                        # close() waits for the client, don't hold the lock
                        for c in kicked:
                            print("kick", c.id)
                            c.queue.put(None)
                            c.websocket.close()
                    continue

                with clients_lock:
                    recipients = get_recipients(client, clients, msg_type, payload)

                forward_msg = pack(MsgType.FORWARD, client.id, msg_data)
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
                # A room without its host goes too, nobody could approve
                # anything there and the host wouldn't be the first client
                # when it comes back.
                if (client.admin or not clients) and rooms.get(path) is clients:
                    rooms.pop(path, None)

        client.queue.put(None)

        if client.admin:
            for remaining_client in remaining:
                remaining_client.websocket.close()
        else:
            # Notify the host of disconnect
            disconnect_msg = pack(MsgType.DISCONNECT, client.id)
            for remaining_client in remaining:
                if remaining_client.admin:
                    remaining_client.queue.put(disconnect_msg)

        print(f"Client left {path}; id={client.id} clients={len(remaining)}")


def main():
    from utils import load_config
    config = load_config()
    ws_config = config.get("ws", {})
    host = ws_config.get("server") or "0.0.0.0"
    port = ws_config.get("port", 8765)
    with serve(handler, host, port, max_size=MAX_MESSAGE) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
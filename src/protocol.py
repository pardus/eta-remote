#!/usr/bin/env python
import json
import struct
from enum import IntEnum


class MsgType(IntEnum):
    """Message type IDs for binary protocol."""
    CONNECT = 0x01
    DISCONNECT = 0x02
    TOUCH = 0x03
    TOUCHPAD = 0x04
    MOUSE = 0x05
    MOUSE_REL = 0x06
    WHEEL = 0x07
    KEY = 0x08
    PING = 0x09
    KICK = 0x0A
    REQUEST_FULL = 0x0B
    QUALITY = 0x0C
    FILE = 0x0D
    FILE_ACK = 0x0E
    IMAGE = 0x0F
    AUDIO = 0x10
    PERMS = 0x11
    CONNECT_INFO = 0x12  # Server -> client: list of connected clients
    FORWARD = 0x20  # Server -> client: wrapped message with sender ID


# Message header: [type:1][length:4] = 5 bytes
HEADER_FMT = ">BI"  # big-endian: uint8, uint32
HEADER_SIZE = 5
MAX_PAYLOAD = 0xFFFFFFFF  # 4GB max payload

INPUT_TYPES = {
    MsgType.TOUCH,
    MsgType.TOUCHPAD,
    MsgType.MOUSE,
    MsgType.MOUSE_REL,
    MsgType.WHEEL,
    MsgType.KEY,
}


def pack_header(msg_type, payload_len):
    """Pack message header."""
    return struct.pack(HEADER_FMT, msg_type, payload_len)


def unpack_header(data):
    """Unpack message header. Returns (msg_type, payload_len)."""
    if len(data) < HEADER_SIZE:
        raise ValueError("Incomplete header")
    msg_type, payload_len = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
    return MsgType(msg_type), payload_len


def pack_str(s):
    """Pack a string as [length:2][utf-8 bytes]."""
    encoded = s.encode("utf-8")
    if len(encoded) > 65535:
        raise ValueError("String too long")
    return struct.pack(">H", len(encoded)) + encoded


def unpack_str(data, offset=0):
    """Unpack a string. Returns (string, new_offset)."""
    if len(data) < offset + 2:
        raise ValueError("Incomplete string length")
    length = struct.unpack(">H", data[offset:offset+2])[0]
    offset += 2
    if len(data) < offset + length:
        raise ValueError("Incomplete string data")
    s = data[offset:offset+length].decode("utf-8")
    return s, offset + length


def pack_bytes(b):
    """Pack bytes as [length:4][bytes]."""
    if len(b) > MAX_PAYLOAD:
        raise ValueError("Bytes too long")
    return struct.pack(">I", len(b)) + b


def unpack_bytes(data, offset=0):
    """Unpack bytes. Returns (bytes, new_offset)."""
    if len(data) < offset + 4:
        raise ValueError("Incomplete bytes length")
    length = struct.unpack(">I", data[offset:offset+4])[0]
    offset += 4
    if len(data) < offset + length:
        raise ValueError("Incomplete bytes data")
    return data[offset:offset+length], offset + length


def pack_json(value):
    """Pack a JSON object as [length:4][utf-8 JSON]."""
    return pack_bytes(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def pack(msg_type, *args, **kwargs):
    """Pack a message of the given type."""
    if msg_type == MsgType.CONNECT:
        client_id = args[0]
        client_data = args[1] if len(args) > 1 else kwargs.get("client_data")
        payload = pack_str(client_id)
        payload += pack_json(client_data) if client_data else pack_bytes(b"")
    elif msg_type == MsgType.DISCONNECT:
        client_id = args[0]
        payload = pack_str(client_id)
    elif msg_type == MsgType.KICK:
        target_id = args[0]
        payload = pack_str(target_id)
    elif msg_type == MsgType.FILE_ACK:
        name, chunk, complete = args
        payload = pack_str(name)
        payload += struct.pack(">I?", chunk, complete)
    elif msg_type == MsgType.IMAGE:
        x, y, width, height, screen_width, screen_height, jpeg_data = args
        payload = struct.pack(">ffHHff", x, y, width, height, screen_width, screen_height)
        payload += pack_bytes(jpeg_data)
    elif msg_type == MsgType.AUDIO:
        audio_data = args[0]
        payload = pack_bytes(audio_data)
    elif msg_type == MsgType.PERMS:
        audio, file, image, input_ = args[:4]
        target_ids = args[4] if len(args) > 4 else kwargs.get("target_ids")
        flags = (audio << 3) | (file << 2) | (image << 1) | input_
        payload = struct.pack(">B", flags)
        if target_ids:
            payload += struct.pack(">H", len(target_ids))
            for tid in target_ids:
                payload += pack_str(tid)
        else:
            payload += struct.pack(">H", 0)
    elif msg_type == MsgType.CONNECT_INFO:
        clients = args[0]
        payload = struct.pack(">H", len(clients))
        for client_id, client_data in clients:
            payload += pack_str(client_id)
            payload += pack_json(client_data)
    elif msg_type == MsgType.FORWARD:
        sender_id, original_msg = args
        payload = pack_str(sender_id)
        payload += pack_bytes(original_msg)
    else:
        raise ValueError(f"Unsupported pack message type: {msg_type}")
    return pack_header(msg_type, len(payload)) + payload


def unpack(msg_type, data):
    """Unpack a message payload of the given type."""
    if msg_type == MsgType.CONNECT:
        offset = 0
        client_id, offset = unpack_str(data, offset)
        client_data_bytes, offset = unpack_bytes(data, offset)
        client_data = None
        if client_data_bytes:
            client_data = json.loads(client_data_bytes.decode("utf-8"))
        return client_id, client_data
    elif msg_type == MsgType.DISCONNECT:
        client_id, _ = unpack_str(data, 0)
        return client_id
    elif msg_type == MsgType.TOUCH:
        offset = 0
        action_len = data[offset]
        offset += 1
        action = data[offset:offset+action_len].decode("ascii")
        offset += action_len
        num_touches = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
        touches = []
        for _ in range(num_touches):
            identifier, x, y, w, h, f = struct.unpack(">HiiHHH", data[offset:offset+16])
            offset += 16
            touches.append({
                "identifier": identifier,
                "x": x, "y": y,
                "w": w, "h": h,
                "f": f
            })
        return {"type": "touch", "action": action, "touches": touches}
    elif msg_type == MsgType.TOUCHPAD:
        raw, _ = unpack_bytes(data)
        d = json.loads(raw.decode("utf-8"))
        d["type"] = "touchpad"
        return d
    elif msg_type == MsgType.MOUSE:
        offset = 0
        action_len = data[offset]
        offset += 1
        action = data[offset:offset+action_len].decode("ascii")
        offset += action_len
        x, y, button, w, h = struct.unpack(">ffHii", data[offset:offset+18])
        return {"type": "mouse", "action": action, "x": x, "y": y, "button": button, "w": w, "h": h}
    elif msg_type == MsgType.MOUSE_REL:
        offset = 0
        action_len = data[offset]
        offset += 1
        action = data[offset:offset+action_len].decode("ascii")
        offset += action_len
        rel_x, rel_y, button = struct.unpack(">iiH", data[offset:offset+10])
        return {"type": "mouse_rel", "action": action, "rel_x": rel_x, "rel_y": rel_y, "button": button}
    elif msg_type == MsgType.WHEEL:
        dx, dy = struct.unpack(">ii", data)
        return {"type": "wheel", "dx": dx, "dy": dy}
    elif msg_type == MsgType.KEY:
        offset = 0
        code_len = data[offset]
        offset += 1
        code = data[offset:offset+code_len].decode("utf-8")
        offset += code_len
        action_len = data[offset]
        offset += 1
        action = data[offset:offset+action_len].decode("ascii")
        return {"type": "key", "code": code, "action": action}
    elif msg_type == MsgType.KICK:
        return unpack_str(data, 0)[0]
    elif msg_type == MsgType.FILE:
        offset = 0
        name, offset = unpack_str(data, offset)
        mimetype, offset = unpack_str(data, offset)
        chunk, total_chunks = struct.unpack(">II", data[offset:offset+8])
        offset += 8
        file_data, _ = unpack_bytes(data, offset)
        return name, mimetype, chunk, total_chunks, file_data
    elif msg_type == MsgType.FILE_ACK:
        offset = 0
        name, offset = unpack_str(data, offset)
        chunk, complete = struct.unpack(">I?", data[offset:offset+5])
        return name, chunk, complete
    elif msg_type == MsgType.IMAGE:
        offset = 0
        x, y, width, height, screen_width, screen_height = struct.unpack(">ffHHff", data[offset:offset+20])
        offset += 20
        jpeg_data, _ = unpack_bytes(data, offset)
        return x, y, width, height, screen_width, screen_height, jpeg_data
    elif msg_type == MsgType.AUDIO:
        audio_data, _ = unpack_bytes(data, 0)
        return audio_data
    elif msg_type == MsgType.PERMS:
        offset = 0
        flags = data[offset]
        offset += 1
        audio = bool(flags & 0x08)
        file = bool(flags & 0x04)
        image = bool(flags & 0x02)
        input_ = bool(flags & 0x01)
        num_targets = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
        targets = []
        for _ in range(num_targets):
            tid, offset = unpack_str(data, offset)
            targets.append(tid)
        return audio, file, image, input_, targets
    elif msg_type == MsgType.CONNECT_INFO:
        offset = 0
        num_clients = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
        clients = []
        for _ in range(num_clients):
            client_id, offset = unpack_str(data, offset)
            client_data_bytes, offset = unpack_bytes(data, offset)
            client_data = json.loads(client_data_bytes.decode("utf-8")) if client_data_bytes else {}
            clients.append((client_id, client_data))
        return clients
    elif msg_type == MsgType.FORWARD:
        offset = 0
        sender_id, offset = unpack_str(data, offset)
        original_msg, _ = unpack_bytes(data, offset)
        return sender_id, original_msg
    elif msg_type == MsgType.REQUEST_FULL:
        return {"type": "request_full"}
    elif msg_type == MsgType.PING:
        return {"type": "ping"}
    else:
        raise ValueError(f"Unsupported unpack message type: {msg_type}")


class BinaryProtocol:
    """Helper class for reading/writing framed binary messages over a stream."""

    def __init__(self):
        self._buffer = bytearray()

    def feed(self, data):
        """Feed incoming data, return list of complete messages."""
        self._buffer.extend(data)
        messages = []
        while len(self._buffer) >= HEADER_SIZE:
            msg_type, payload_len = unpack_header(self._buffer)
            total_len = HEADER_SIZE + payload_len
            if len(self._buffer) < total_len:
                break  # wait for more data
            message = bytes(self._buffer[:total_len])
            messages.append(message)
            del self._buffer[:total_len]
        return messages


def parse_message(data):
    """Parse a complete message. Returns (msg_type, payload)."""
    msg_type, payload_len = unpack_header(data)
    if len(data) != HEADER_SIZE + payload_len:
        raise ValueError(f"Message length mismatch: expected {HEADER_SIZE + payload_len}, got {len(data)}")
    return msg_type, data[HEADER_SIZE:]

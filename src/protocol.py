#!/usr/bin/env python
import json
import struct
from typing import Optional, List, Tuple, Dict
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


def pack_header(msg_type: MsgType, payload_len: int) -> bytes:
    """Pack message header."""
    return struct.pack(HEADER_FMT, msg_type, payload_len)


def unpack_header(data: bytes) -> Tuple[MsgType, int]:
    """Unpack message header. Returns (msg_type, payload_len)."""
    if len(data) < HEADER_SIZE:
        raise ValueError("Incomplete header")
    msg_type, payload_len = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
    return MsgType(msg_type), payload_len


def pack_str(s: str) -> bytes:
    """Pack a string as [length:2][utf-8 bytes]."""
    encoded = s.encode("utf-8")
    if len(encoded) > 65535:
        raise ValueError("String too long")
    return struct.pack(">H", len(encoded)) + encoded


def unpack_str(data: bytes, offset: int = 0) -> Tuple[str, int]:
    """Unpack a string. Returns (string, new_offset)."""
    if len(data) < offset + 2:
        raise ValueError("Incomplete string length")
    length = struct.unpack(">H", data[offset:offset+2])[0]
    offset += 2
    if len(data) < offset + length:
        raise ValueError("Incomplete string data")
    s = data[offset:offset+length].decode("utf-8")
    return s, offset + length


def pack_bytes(b: bytes) -> bytes:
    """Pack bytes as [length:4][bytes]."""
    if len(b) > MAX_PAYLOAD:
        raise ValueError("Bytes too long")
    return struct.pack(">I", len(b)) + b


def unpack_bytes(data: bytes, offset: int = 0) -> Tuple[bytes, int]:
    """Unpack bytes. Returns (bytes, new_offset)."""
    if len(data) < offset + 4:
        raise ValueError("Incomplete bytes length")
    length = struct.unpack(">I", data[offset:offset+4])[0]
    offset += 4
    if len(data) < offset + length:
        raise ValueError("Incomplete bytes data")
    return data[offset:offset+length], offset + length


def pack_json(value: Dict) -> bytes:
    """Pack a JSON object as [length:4][utf-8 JSON]."""
    return pack_bytes(json.dumps(value, separators=(",", ":")).encode("utf-8"))


# --- Specific message packers/unpackers ---

def pack_connect(client_id: str, client_data: Optional[Dict] = None) -> bytes:
    """Pack CONNECT message."""
    # client_id + optional JSON client_data
    payload = pack_str(client_id)
    payload += pack_json(client_data) if client_data else pack_bytes(b"")
    return pack_header(MsgType.CONNECT, len(payload)) + payload


def unpack_connect(data: bytes) -> Tuple[str, Optional[Dict]]:
    """Unpack CONNECT message. Returns (client_id, client_data)."""
    offset = 0
    client_id, offset = unpack_str(data, offset)
    client_data_bytes, offset = unpack_bytes(data, offset)
    client_data = None
    if client_data_bytes:
        client_data = json.loads(client_data_bytes.decode("utf-8"))
    return client_id, client_data


def pack_disconnect(client_id: str) -> bytes:
    payload = pack_str(client_id)
    return pack_header(MsgType.DISCONNECT, len(payload)) + payload


def unpack_disconnect(data: bytes) -> str:
    client_id, _ = unpack_str(data, 0)
    return client_id


def pack_touch(action: str, touches: List[Dict]) -> bytes:
    """Pack TOUCH message.
    touches: list of {identifier, x, y, w, h, f}
    """
    action_bytes = action.encode("ascii")
    payload = struct.pack(">B", len(action_bytes)) + action_bytes
    payload += struct.pack(">H", len(touches))
    for t in touches:
        identifier = t.get("identifier", 0) & 0xFFFF
        x = int(t.get("x", 0))
        y = int(t.get("y", 0))
        w = int(t.get("w", 3840))
        h = int(t.get("h", 2160))
        f = max(0, min(int(t.get("f", 512)), 1023))
        payload += struct.pack(">HiiHHH", identifier, x, y, w, h, f)
    return pack_header(MsgType.TOUCH, len(payload)) + payload


def unpack_touch(data: bytes) -> Tuple[str, List[Dict]]:
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
    return action, touches


def pack_touchpad(data: Dict) -> bytes:
    """Pack TOUCHPAD message (gesture data as JSON)."""
    payload = pack_json(data)
    return pack_header(MsgType.TOUCHPAD, len(payload)) + payload


def unpack_touchpad(data: bytes) -> Dict:
    raw, _ = unpack_bytes(data)
    return json.loads(raw.decode("utf-8"))


def pack_mouse(action: str, x: float, y: float, button: int, w: int, h: int) -> bytes:
    """Pack MOUSE message."""
    action_bytes = action.encode("ascii")
    payload = struct.pack(">B", len(action_bytes)) + action_bytes
    payload += struct.pack(">ffHii", x, y, button, w, h)
    return pack_header(MsgType.MOUSE, len(payload)) + payload


def unpack_mouse(data: bytes) -> Dict:
    offset = 0
    action_len = data[offset]
    offset += 1
    action = data[offset:offset+action_len].decode("ascii")
    offset += action_len
    x, y, button, w, h = struct.unpack(">ffHii", data[offset:offset+18])
    return {"action": action, "x": x, "y": y, "button": button, "w": w, "h": h}


def pack_mouse_rel(action: str, rel_x: int, rel_y: int, button: int) -> bytes:
    action_bytes = action.encode("ascii")
    payload = struct.pack(">B", len(action_bytes)) + action_bytes
    payload += struct.pack(">iiH", rel_x, rel_y, button)
    return pack_header(MsgType.MOUSE_REL, len(payload)) + payload


def unpack_mouse_rel(data: bytes) -> Dict:
    offset = 0
    action_len = data[offset]
    offset += 1
    action = data[offset:offset+action_len].decode("ascii")
    offset += action_len
    rel_x, rel_y, button = struct.unpack(">iiH", data[offset:offset+10])
    return {"action": action, "rel_x": rel_x, "rel_y": rel_y, "button": button}


def pack_wheel(dx: int, dy: int) -> bytes:
    payload = struct.pack(">ii", dx, dy)
    return pack_header(MsgType.WHEEL, len(payload)) + payload


def unpack_wheel(data: bytes) -> Tuple[int, int]:
    return struct.unpack(">ii", data)


def pack_key(code: str, action: str) -> bytes:
    code_bytes = code.encode("utf-8")
    action_bytes = action.encode("ascii")
    payload = struct.pack(">B", len(code_bytes)) + code_bytes
    payload += struct.pack(">B", len(action_bytes)) + action_bytes
    return pack_header(MsgType.KEY, len(payload)) + payload


def unpack_key(data: bytes) -> Tuple[str, str]:
    offset = 0
    code_len = data[offset]
    offset += 1
    code = data[offset:offset+code_len].decode("utf-8")
    offset += code_len
    action_len = data[offset]
    offset += 1
    action = data[offset:offset+action_len].decode("ascii")
    return code, action


def unpack_touch_dict(data: bytes) -> Dict:
    """Unpack TOUCH message to dict compatible with existing handler."""
    action, touches = unpack_touch(data)
    return {"type": "touch", "action": action, "touches": touches}


def unpack_mouse_dict(data: bytes) -> Dict:
    """Unpack MOUSE message to dict."""
    event = unpack_mouse(data)
    event["type"] = "mouse"
    return event


def unpack_mouse_rel_dict(data: bytes) -> Dict:
    """Unpack MOUSE_REL message to dict."""
    event = unpack_mouse_rel(data)
    event["type"] = "mouse_rel"
    return event


def unpack_wheel_dict(data: bytes) -> Dict:
    """Unpack WHEEL message to dict."""
    dx, dy = unpack_wheel(data)
    return {"type": "wheel", "dx": dx, "dy": dy}


def unpack_key_dict(data: bytes) -> Dict:
    """Unpack KEY message to dict."""
    code, action = unpack_key(data)
    return {"type": "key", "code": code, "action": action}


def unpack_touchpad_dict(data: bytes) -> Dict:
    """Unpack TOUCHPAD message to dict."""
    d = unpack_touchpad(data)
    d["type"] = "touchpad"
    return d


INPUT_PARSERS = {
    MsgType.TOUCH: unpack_touch_dict,
    MsgType.MOUSE: unpack_mouse_dict,
    MsgType.MOUSE_REL: unpack_mouse_rel_dict,
    MsgType.WHEEL: unpack_wheel_dict,
    MsgType.KEY: unpack_key_dict,
    MsgType.TOUCHPAD: unpack_touchpad_dict,
}


def pack_ping(timestamp: float = 0.0) -> bytes:
    payload = struct.pack(">d", timestamp)
    return pack_header(MsgType.PING, len(payload)) + payload


def unpack_ping(data: bytes) -> float:
    return struct.unpack(">d", data[:8])[0]


def pack_kick(target_id: str) -> bytes:
    payload = pack_str(target_id)
    return pack_header(MsgType.KICK, len(payload)) + payload


def unpack_kick(data: bytes) -> str:
    return unpack_str(data, 0)[0]


def pack_request_full() -> bytes:
    return pack_header(MsgType.REQUEST_FULL, 0)


def pack_quality(quality: int) -> bytes:
    payload = struct.pack(">B", max(0, min(100, quality)))
    return pack_header(MsgType.QUALITY, len(payload)) + payload


def unpack_quality(data: bytes) -> int:
    return data[0]


def pack_file(name: str, chunk: int, total_chunks: int, data: bytes, mimetype: str = "") -> bytes:
    """Pack FILE message with raw binary data (no base64)."""
    payload = pack_str(name)
    payload += pack_str(mimetype)
    payload += struct.pack(">II", chunk, total_chunks)
    payload += pack_bytes(data)
    return pack_header(MsgType.FILE, len(payload)) + payload


def unpack_file(data: bytes) -> Tuple[str, str, int, int, bytes]:
    """Unpack FILE message. Returns (name, mimetype, chunk, total_chunks, data)."""
    offset = 0
    name, offset = unpack_str(data, offset)
    mimetype, offset = unpack_str(data, offset)
    chunk, total_chunks = struct.unpack(">II", data[offset:offset+8])
    offset += 8
    file_data, _ = unpack_bytes(data, offset)
    return name, mimetype, chunk, total_chunks, file_data


def pack_file_ack(name: str, chunk: int, complete: bool) -> bytes:
    payload = pack_str(name)
    payload += struct.pack(">I?", chunk, complete)
    return pack_header(MsgType.FILE_ACK, len(payload)) + payload


def unpack_file_ack(data: bytes) -> Tuple[str, int, bool]:
    offset = 0
    name, offset = unpack_str(data, offset)
    chunk, complete = struct.unpack(">I?", data[offset:offset+5])
    return name, chunk, complete


def pack_image(x: float, y: float, width: int, height: int,
               screen_width: float, screen_height: float, jpeg_data: bytes) -> bytes:
    """Pack IMAGE message with raw JPEG data."""
    payload = struct.pack(">ffHHff", x, y, width, height, screen_width, screen_height)
    payload += pack_bytes(jpeg_data)
    return pack_header(MsgType.IMAGE, len(payload)) + payload


def unpack_image(data: bytes) -> Tuple[float, float, int, int, float, float, bytes]:
    offset = 0
    x, y, width, height, screen_width, screen_height = struct.unpack(">ffHHff", data[offset:offset+20])
    offset += 20
    jpeg_data, _ = unpack_bytes(data, offset)
    return x, y, width, height, screen_width, screen_height, jpeg_data


def pack_audio(audio_data: bytes) -> bytes:
    """Pack AUDIO message with raw compressed audio data."""
    payload = pack_bytes(audio_data)
    return pack_header(MsgType.AUDIO, len(payload)) + payload


def unpack_audio(data: bytes) -> bytes:
    audio_data, _ = unpack_bytes(data, 0)
    return audio_data


def pack_perms(audio: bool, file: bool, image: bool, input_: bool, target_ids: Optional[List[str]] = None) -> bytes:
    """Pack PERMS message."""
    flags = (audio << 3) | (file << 2) | (image << 1) | input_
    payload = struct.pack(">B", flags)
    if target_ids:
        payload += struct.pack(">H", len(target_ids))
        for tid in target_ids:
            payload += pack_str(tid)
    else:
        payload += struct.pack(">H", 0)
    return pack_header(MsgType.PERMS, len(payload)) + payload


def unpack_perms(data: bytes) -> Tuple[bool, bool, bool, bool, List[str]]:
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


def pack_connect_info(clients: List[Tuple[str, Dict]]) -> bytes:
    """Pack CONNECT_INFO message (server -> client): list of connected clients."""
    payload = struct.pack(">H", len(clients))
    for client_id, client_data in clients:
        payload += pack_str(client_id)
        payload += pack_json(client_data)
    return pack_header(MsgType.CONNECT_INFO, len(payload)) + payload


def unpack_connect_info(data: bytes) -> List[Tuple[str, Dict]]:
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


def pack_forward(sender_id: str, original_msg: bytes) -> bytes:
    """Pack a FORWARD message wrapping an original message with sender ID."""
    payload = pack_str(sender_id)
    payload += pack_bytes(original_msg)
    return pack_header(MsgType.FORWARD, len(payload)) + payload


def unpack_forward(data: bytes) -> Tuple[str, bytes]:
    """Unpack a FORWARD message. Returns (sender_id, original_message)."""
    offset = 0
    sender_id, offset = unpack_str(data, offset)
    original_msg, _ = unpack_bytes(data, offset)
    return sender_id, original_msg


# --- Framing helpers for streaming ---

class BinaryProtocol:
    """Helper class for reading/writing framed binary messages over a stream."""

    def __init__(self):
        self._buffer = bytearray()

    def feed(self, data: bytes) -> List[bytes]:
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


def parse_message(data: bytes) -> Tuple[MsgType, bytes]:
    """Parse a complete message. Returns (msg_type, payload)."""
    msg_type, payload_len = unpack_header(data)
    if len(data) != HEADER_SIZE + payload_len:
        raise ValueError(f"Message length mismatch: expected {HEADER_SIZE + payload_len}, got {len(data)}")
    return msg_type, data[HEADER_SIZE:]

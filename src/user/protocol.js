// Binary protocol for JavaScript - matches Python protocol.py

const MsgType = {
    CONNECT: 0x01,
    DISCONNECT: 0x02,
    TOUCH: 0x03,
    TOUCHPAD: 0x04,
    MOUSE: 0x05,
    MOUSE_REL: 0x06,
    WHEEL: 0x07,
    KEY: 0x08,
    PING: 0x09,
    KICK: 0x0A,
    REQUEST_FULL: 0x0B,
    QUALITY: 0x0C,
    FILE: 0x0D,
    FILE_ACK: 0x0E,
    IMAGE: 0x0F,
    AUDIO: 0x10,
    PERMS: 0x11,
    CONNECT_INFO: 0x12,
    FORWARD: 0x20
};

const HEADER_SIZE = 5; // 1 byte type + 4 bytes length (big-endian)

class BinaryProtocol {
    constructor() {
        this.buffer = new Uint8Array(0);
    }

    feed(data) {
        const newBuffer = new Uint8Array(this.buffer.length + data.length);
        newBuffer.set(this.buffer);
        newBuffer.set(data, this.buffer.length);
        this.buffer = newBuffer;
    }

    getMessages() {
        const messages = [];
        while (this.buffer.length >= HEADER_SIZE) {
            const view = new DataView(this.buffer.buffer, this.buffer.byteOffset, this.buffer.byteLength);
            const msgType = view.getUint8(0);
            const payloadLen = view.getUint32(1);
            const totalLen = HEADER_SIZE + payloadLen;
            
            if (this.buffer.length < totalLen) {
                break;
            }
            
            const msgData = this.buffer.slice(0, totalLen);
            messages.push({ type: msgType, data: msgData });
            this.buffer = this.buffer.slice(totalLen);
        }
        return messages;
    }
}

// Helper functions for packing/unpacking

function createDataView(buffer) {
    return new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
}

function readString(view, offset) {
    const len = view.getUint16(offset);
    offset += 2;
    const decoder = new TextDecoder();
    const str = decoder.decode(new Uint8Array(view.buffer, view.byteOffset + offset, len));
    return [str, offset + len];
}

function writeString(str) {
    const encoder = new TextEncoder();
    const encoded = encoder.encode(str);
    const buffer = new ArrayBuffer(2 + encoded.length);
    const view = new DataView(buffer);
    view.setUint16(0, encoded.length);
    new Uint8Array(buffer, 2).set(encoded);
    return buffer;
}

function readBytes(view, offset) {
    const len = view.getUint32(offset);
    offset += 4;
    const data = new Uint8Array(view.buffer, view.byteOffset + offset, len);
    return [data, offset + len];
}

function writeBytes(data) {
    const buffer = new ArrayBuffer(4 + data.length);
    const view = new DataView(buffer);
    view.setUint32(0, data.length);
    new Uint8Array(buffer, 4).set(data);
    return buffer;
}

function concat(...parts) {
    const out = new Uint8Array(parts.reduce((size, part) => size + part.byteLength, 0));
    let offset = 0;
    for (const part of parts) {
        out.set(part instanceof Uint8Array ? part : new Uint8Array(part), offset);
        offset += part.byteLength;
    }
    return out;
}

function packHeader(msgType, payloadLen) {
    const buffer = new ArrayBuffer(HEADER_SIZE);
    const view = new DataView(buffer);
    view.setUint8(0, msgType);
    view.setUint32(1, payloadLen);
    return buffer;
}

function createMessage(msgType, payload) {
    return concat(packHeader(msgType, payload.byteLength), payload);
}

function unpackHeader(data) {
    const view = createDataView(data);
    return { type: view.getUint8(0), payloadLen: view.getUint32(1) };
}

// Pack a message based on its type
function pack(msgType, ...args) {
    switch (msgType) {
        case MsgType.CONNECT: {
            const [clientId, clientData] = args;
            return createMessage(msgType, concat(
                writeString(clientId),
                writeBytes(new TextEncoder().encode(JSON.stringify(clientData || {})))
            ));
        }
        case MsgType.TOUCH: {
            const [action, touches] = args;
            const actionBuf = new TextEncoder().encode(action);
            const payload = new Uint8Array(1 + actionBuf.length + 2 + touches.length * 16);
            const view = new DataView(payload.buffer);
            let offset = 0;
            payload[offset++] = actionBuf.length;
            payload.set(actionBuf, offset);
            offset += actionBuf.length;
            view.setUint16(offset, touches.length);
            offset += 2;
            for (const t of touches) {
                view.setUint16(offset, t.identifier & 0xFFFF);
                view.setInt32(offset + 2, t.x | 0);
                view.setInt32(offset + 6, t.y | 0);
                view.setUint16(offset + 10, t.w | 0);
                view.setUint16(offset + 12, t.h | 0);
                view.setUint16(offset + 14, Math.max(0, Math.min(1023, t.f | 0)));
                offset += 16;
            }
            return createMessage(msgType, payload);
        }
        case MsgType.TOUCHPAD: {
            const [data] = args;
            return createMessage(msgType, writeBytes(new TextEncoder().encode(JSON.stringify(data))));
        }
        case MsgType.MOUSE: {
            const [action, x, y, button, w, h] = args;
            const actionBuf = new TextEncoder().encode(action);
            const payload = new ArrayBuffer(1 + actionBuf.length + 18);
            const view = new DataView(payload);
            let offset = 0;
            view.setUint8(offset, actionBuf.length);
            offset += 1;
            new Uint8Array(payload, offset).set(actionBuf);
            offset += actionBuf.length;
            view.setFloat32(offset, x);
            offset += 4;
            view.setFloat32(offset, y);
            offset += 4;
            view.setUint16(offset, button);
            offset += 2;
            view.setInt32(offset, w);
            offset += 4;
            view.setInt32(offset, h);
            return createMessage(msgType, new Uint8Array(payload));
        }
        case MsgType.MOUSE_REL: {
            const [action, relX, relY, button] = args;
            const actionBuf = new TextEncoder().encode(action);
            const payload = new ArrayBuffer(1 + actionBuf.length + 10);
            const view = new DataView(payload);
            let offset = 0;
            view.setUint8(offset, actionBuf.length);
            offset += 1;
            new Uint8Array(payload, offset).set(actionBuf);
            offset += actionBuf.length;
            view.setInt32(offset, relX);
            offset += 4;
            view.setInt32(offset, relY);
            offset += 4;
            view.setUint16(offset, button);
            return createMessage(msgType, new Uint8Array(payload));
        }
        case MsgType.WHEEL: {
            const [dx, dy] = args;
            const payload = new ArrayBuffer(8);
            const view = new DataView(payload);
            view.setInt32(0, dx);
            view.setInt32(4, dy);
            return createMessage(msgType, new Uint8Array(payload));
        }
        case MsgType.KEY: {
            const [code, action] = args;
            const codeBuf = new TextEncoder().encode(code);
            const actionBuf = new TextEncoder().encode(action);
            const payload = new Uint8Array(1 + codeBuf.length + 1 + actionBuf.length);
            let offset = 0;
            payload[offset++] = codeBuf.length;
            payload.set(codeBuf, offset);
            offset += codeBuf.length;
            payload[offset++] = actionBuf.length;
            payload.set(actionBuf, offset);
            return createMessage(msgType, payload);
        }
        case MsgType.PING: {
            const [timestamp = 0] = args;
            const payload = new ArrayBuffer(8);
            new DataView(payload).setFloat64(0, timestamp);
            return createMessage(msgType, new Uint8Array(payload));
        }
        case MsgType.REQUEST_FULL:
            return createMessage(msgType, new Uint8Array(0));
        case MsgType.QUALITY: {
            const [quality] = args;
            const payload = new Uint8Array([Math.max(0, Math.min(100, quality))]);
            return createMessage(msgType, payload);
        }
        case MsgType.FILE: {
            const [name, chunk, totalChunks, data, mimetype = ""] = args;
            const chunkBuf = new ArrayBuffer(8);
            const chunkView = new DataView(chunkBuf);
            chunkView.setUint32(0, chunk);
            chunkView.setUint32(4, totalChunks);
            return createMessage(msgType, concat(
                writeString(name),
                writeString(mimetype),
                chunkBuf,
                writeBytes(data)
            ));
        }
        default:
            throw new Error("Unsupported pack message type: " + msgType);
    }
}

// Unpack a message payload based on its type
function unpack(msgType, payload) {
    const view = createDataView(payload);
    switch (msgType) {
        case MsgType.IMAGE: {
            let offset = 0;
            const x = view.getFloat32(offset); offset += 4;
            const y = view.getFloat32(offset); offset += 4;
            const width = view.getUint16(offset); offset += 2;
            const height = view.getUint16(offset); offset += 2;
            const screenWidth = view.getFloat32(offset); offset += 4;
            const screenHeight = view.getFloat32(offset); offset += 4;
            const [jpegData] = readBytes(view, offset);
            return { x, y, width, height, screenWidth, screenHeight, jpegData };
        }
        case MsgType.AUDIO:
            return readBytes(view, 0)[0];
        case MsgType.DISCONNECT:
            return readString(view, 0)[0];
        case MsgType.CONNECT_INFO: {
            let offset = 0;
            const numClients = view.getUint16(offset); offset += 2;
            const clients = [];
            for (let i = 0; i < numClients; i++) {
                const [clientId, newOffset] = readString(view, offset);
                offset = newOffset;
                const [clientDataBytes, newOffset2] = readBytes(view, offset);
                offset = newOffset2;
                const clientData = clientDataBytes.length > 0 ? JSON.parse(new TextDecoder().decode(clientDataBytes)) : {};
                clients.push({ id: clientId, data: clientData });
            }
            return clients;
        }
        case MsgType.FILE_ACK: {
            let offset = 0;
            const [name, newOffset] = readString(view, offset);
            offset = newOffset;
            const chunk = view.getUint32(offset); offset += 4;
            const complete = view.getUint8(offset) !== 0;
            return { name, chunk, complete };
        }
        case MsgType.PERMS: {
            let offset = 0;
            const flags = view.getUint8(offset); offset += 1;
            const audio = (flags & 0x08) !== 0;
            const file = (flags & 0x04) !== 0;
            const image = (flags & 0x02) !== 0;
            const input = (flags & 0x01) !== 0;
            const numTargets = view.getUint16(offset); offset += 2;
            const targets = [];
            for (let i = 0; i < numTargets; i++) {
                const [tid, newOffset] = readString(view, offset);
                offset = newOffset;
                targets.push(tid);
            }
            return { audio, file, image, input, targets };
        }
        case MsgType.FORWARD: {
            let offset = 0;
            const [senderId, newOffset] = readString(view, offset);
            offset = newOffset;
            const [innerMsg, _] = readBytes(view, offset);
            return { senderId, innerMsg };
        }
        case MsgType.PING:
            return view.getFloat64(0);
        default:
            throw new Error("Unsupported unpack message type: " + msgType);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        MsgType, HEADER_SIZE, BinaryProtocol,
        pack, unpack, unpackHeader
    };
}

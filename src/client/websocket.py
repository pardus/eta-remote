import queue
import copy
import platform
import threading
import time
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed

import traceback

from protocol import (
    BinaryProtocol, MsgType, pack, unpack, unpack_header, HEADER_SIZE,
    INPUT_TYPES,
)

from capture import main as capture_main, request_full
from pulse import main as pulse_main, pulse_stop, pulse_start


class context:
    def __init__(self):
        self.allow = False
        self.websocket = None
        self.message = None
        self.wait = True


class WebSocketClient:
    def __init__(self, address, handler=print, control=print):
        self.address = address
        self.handler = handler
        self.control = control
        self._wait_last = True
        self._stop_event = threading.Event()
        self._go_event = threading.Event()
        self._data_queue = queue.Queue()
        self._audio_queue = queue.Queue(maxsize=10)
        self.ctx = context()
        self._protocol = BinaryProtocol()

    def _process_message(self, ctx, msg_type, msg_data, sender_id=None):
        ctx.message = self._parse_message(msg_type, msg_data[HEADER_SIZE:])
        # A client can send any type, some of them don't unpack to a dict.
        # Raising here would drop the connection of the board.
        if not isinstance(ctx.message, dict):
            return
        if sender_id is not None:
            ctx.message["id"] = sender_id

        if self.control(ctx):
            if ctx.message.get("type") == "request_full":
                request_full()
            elif msg_type in INPUT_TYPES:
                self.handler(msg_data)
            else:
                self.handler(ctx.message)

        if self._wait_last != ctx.wait:
            self.ctx.wait = ctx.wait
            if not ctx.wait:
                self._start()
            else:
                self._stop()
            self._wait_last = ctx.wait

    def client(self):
        try:
            ctx = copy.copy(self.ctx)
            while not self._stop_event.is_set():
                try:
                    message = self.ctx.websocket.recv()
                except ConnectionClosed:
                    return

                for msg_data in self._protocol.feed(message):
                    msg_type, _ = unpack_header(msg_data)
                    if msg_type == MsgType.FORWARD:
                        sender_id, inner = unpack(MsgType.FORWARD, msg_data[HEADER_SIZE:])
                        inner_type, _ = unpack_header(inner)
                        self._process_message(ctx, inner_type, inner, sender_id)
                    else:
                        self._process_message(ctx, msg_type, msg_data)
        except ConnectionClosed:
            pass
        except:
            print(traceback.format_exc())

    def _parse_message(self, msg_type, payload):
        """Parse binary message payload into a dict for the control/handler."""
        try:
            result = unpack(msg_type, payload)
            if msg_type == MsgType.IMAGE:
                x, y, width, height, sw, sh, jpeg_data = result
                return {
                    "type": "image",
                    "x": x, "y": y,
                    "width": width, "height": height,
                    "screen_width": sw, "screen_height": sh,
                    "pixels": jpeg_data,
                }
            if msg_type == MsgType.AUDIO:
                return {"type": "audio", "data": result}
            if msg_type == MsgType.DISCONNECT:
                return {"type": "disconnect", "id": result}
            if msg_type == MsgType.CONNECT_INFO:
                return {"type": "connect_info", "clients": result}
            if msg_type == MsgType.FILE_ACK:
                name, chunk, complete = result
                return {"type": "file_ack", "name": name, "chunk": chunk, "complete": complete}
            if msg_type == MsgType.PERMS:
                audio, file, image, input_, targets = result
                return {
                    "type": "perms",
                    "audio": audio, "file": file, "image": image, "input": input_,
                    "target": targets,
                }
            if msg_type == MsgType.FILE:
                name, mimetype, chunk, total_chunks, data = result
                return {
                    "type": "file",
                    "name": name,
                    "mimetype": mimetype,
                    "chunk": chunk,
                    "totalChunks": total_chunks,
                    "data": data,
                }
            if msg_type == MsgType.CONNECT:
                _, client_data = result
                return {**(client_data or {}), "type": "connect"}
            return result
        except:
            print(traceback.format_exc())
            return None

    def sender(self, q):
        while not self._stop_event.is_set():
            if self.ctx.websocket is None:
                return
            try:
                message = q.get(timeout=0.1)
            except queue.Empty:
                continue
            if message is None:
                return
            try:
                self.ctx.websocket.send(message)
            except ConnectionClosed:
                return
            except:
                print(traceback.format_exc())

    def streamer(self):
        def data_handler(message):
            if self._stop_event.is_set():
                return
            if self.ctx.wait:
                self._go_event.wait()
                if self._stop_event.is_set():
                    return
            self._data_queue.put(message)

        def audio_handler(message):
            if self._stop_event.is_set():
                return
            if self.ctx.wait:
                self._go_event.wait()
                if self._stop_event.is_set():
                    return
            try:
                self._audio_queue.put_nowait(message)
            except queue.Full:
                pass

        capture_thread = threading.Thread(
            target=capture_main, args=(data_handler,),
            kwargs={"stop_event": self._stop_event}, daemon=True
        )
        audio_thread = threading.Thread(
            target=pulse_main, args=(audio_handler,),
            kwargs={"stop_event": self._stop_event}, daemon=True
        )

        capture_thread.start()
        audio_thread.start()

        try:
            while not self._stop_event.is_set():
                while not self._stop_event.is_set() and self.ctx.websocket is None:
                    time.sleep(0.05)
                if self._stop_event.is_set():
                    break
                sender_thread_1 = threading.Thread(
                    target=self.sender, args=(self._data_queue,), daemon=True
                )
                sender_thread_2 = threading.Thread(
                    target=self.sender, args=(self._audio_queue,), daemon=True
                )
                sender_thread_1.start()
                sender_thread_2.start()
                sender_thread_1.join()
                sender_thread_2.join()
        finally:
            capture_thread.join()
            audio_thread.join()

    def _start(self):
        self._go_event.set()
        pulse_start()

    def _stop(self):
        self._go_event.clear()
        pulse_stop()

    def stop(self):
        self._stop_event.set()
        self._go_event.set()
        try:
            self._data_queue.put_nowait(None)
        except:
            pass
        try:
            self._audio_queue.put_nowait(None)
        except:
            pass
        pulse_stop()
        try:
            if self.ctx.websocket is not None:
                self.ctx.websocket.close()
        except:
            pass

    def run(self):
        streamer_thread = threading.Thread(target=self.streamer, daemon=True)
        streamer_thread.start()
        try:
            while not self._stop_event.is_set():
                try:
                    with connect(self.address, max_size=None) as websocket:
                        self.ctx = context()
                        self.ctx.websocket = websocket
                        self._protocol = BinaryProtocol()
                        websocket.send(pack(MsgType.CONNECT, "client", {
                            "useragent": "eta-remote-client",
                            "platform": platform.platform(),
                            "language": "en",
                            "mobile": False,
                        }))
                        client_thread = threading.Thread(target=self.client)
                        client_thread.start()
                        client_thread.join()
                        self.ctx.websocket = None
                except (OSError, ConnectionClosed):
                    if self._stop_event.is_set():
                        return
                    print("connection failed, retrying", self.address)
                    time.sleep(1)
        finally:
            streamer_thread.join()


if __name__ == "__main__":
    ws = WebSocketClient("ws://localhost:8765/room1")
    ws.run()
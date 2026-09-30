import json
import queue
import copy
import threading
import time
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed

import traceback

from capture import main as capture_main, request_full, set_quality
from pulse import main as pulse_main, pulse_stop, pulse_start


class context:
    def __init__(self):
        self.allow = False
        self.websocket = None
        self.message = ""
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

    def client(self):
        try:
            ctx = copy.copy(self.ctx)
            for message in self.ctx.websocket:
                ctx.message = message
                if self.control(ctx):
                    if "request_full" in message:
                        request_full()
                    elif "quality" in message:
                        data = json.loads(message)
                        set_quality(data.get("quality", 80))
                    else:
                        self.handler(message)
                if self._wait_last != ctx.wait:
                    self.ctx.wait = ctx.wait
                    if not ctx.wait:
                        self._start()
                    else:
                        self._stop()
                    self._wait_last = ctx.wait
        except ConnectionClosed:
            pass
        except:
            print(traceback.format_exc())

    def sender(self, q):
        ctx = copy.copy(self.ctx)
        while not self._stop_event.is_set():
            # run() clears ctx.websocket when the connection drops
            if self.ctx.websocket is None:
                return
            try:
                message = q.get(timeout=0.1)
            except queue.Empty:
                continue
            if message is None:
                return
            ctx.message = message
            if self.control(ctx):
                try:
                    ctx.websocket.send(ctx.message)
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
                # wait until a connection is available
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
                # senders exited: either the connection dropped (loop and
                # wait for the next one) or stop() was called (loop exits)
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
        # unblock data/audio handlers waiting on the go event
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
                        client_thread = threading.Thread(target=self.client)
                        client_thread.start()
                        client_thread.join()
                        # connection dropped: tell the senders and loop to
                        # reconnect instead of leaving them blocked
                        self.ctx.websocket = None
                except (OSError, ConnectionClosed):
                    if self._stop_event.is_set():
                        return
                    print("connection failed, retrying")
                    time.sleep(1)
        finally:
            streamer_thread.join()


if __name__ == "__main__":
    ws = WebSocketClient("ws://localhost:8765/room1")
    ws.run()

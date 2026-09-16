import json
import queue
import threading
import time
from websockets.sync.client import connect

import traceback

from capture import main as capture_main, request_full, set_quality
from pulse import main as pulse_main, pulse_stop, pulse_start

lock = {"data":threading.Condition(), "audio":threading.Condition()}

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

    def client(self):
        for message in self.ctx.websocket:
            self.ctx.message = message
            if self.control(self.ctx):
                if "request_full" in message:
                    request_full()
                elif "quality" in message:
                    data = json.loads(message)
                    set_quality(data.get("quality", 80))
                else:
                    self.handler(message)
            if self._wait_last != self.ctx.wait:
                if not self.ctx.wait:
                    self._start()
                else:
                    self._stop()
                self._wait_last = self.ctx.wait


    def sender(self, q):
        while True:
            try:
                message = q.get()
                self.ctx.message = message
                if self.control(self.ctx):
                    self.ctx.websocket.send(self.ctx.message)
            except:
                print(traceback.format_exc())

    def streamer(self):
        data_queue = queue.Queue()
        audio_queue = queue.Queue()

        def data_handler(message):
            if self.ctx.wait:
                with lock["data"]:
                    lock["data"].wait()
            data_queue.put(message)

        def audio_handler(message):
            if self.ctx.wait:
                with lock["audio"]:
                    lock["audio"].wait()
            audio_queue.put(message)

        capture_thread = threading.Thread(
            target=capture_main, args=(data_handler,), daemon=True
        )
        audio_thread = threading.Thread(
            target=pulse_main, args=(audio_handler,), daemon=True
        )

        sender_thread_1 = threading.Thread(
            target=self.sender, args=(data_queue,), daemon=True
        )
        sender_thread_2 = threading.Thread(
            target=self.sender, args=(audio_queue,), daemon=True
        )

        capture_thread.start()
        audio_thread.start()
        sender_thread_1.start()
        sender_thread_2.start()

        capture_thread.join()
        audio_thread.join()
        sender_thread_1.join()
        sender_thread_2.join()

    def _start(self):
        with lock["data"]:
            lock["data"].notify()
        with lock["audio"]:
            lock["audio"].notify()
        pulse_start()

    def _stop(self):
        pulse_stop()

    def run(self):
        while True:
            try:
                with connect(self.address, max_size=None) as websocket:
                    self.ctx = context()
                    self.ctx.websocket = websocket
                    client_thread = threading.Thread(target=self.client)
                    streamer_thread = threading.Thread(target=self.streamer)
                    client_thread.start()
                    streamer_thread.start()
                    client_thread.join()
                    streamer_thread.join()
                return
            except OSError:
                print("connection failed, retrying")
                time.sleep(1)


if __name__ == "__main__":
    ws = WebSocketClient("ws://localhost:8765/room1")
    ws.run()

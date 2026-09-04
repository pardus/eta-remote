#!/usr/bin/env python
"""Starts the relay server, http server, and client service."""

import os
import sys
import signal
import json
import asyncio
import threading

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for sub in ("client", "server", "gui"):
    sys.path.insert(0, os.path.join(BASE_DIR, sub))

from websocket import WebSocketClient
from main import PipeUInputHandler
from keymap import build_keymap

from MainWindow import MainWindow

class RemoteControl:
    def __init__(self, address="ws://localhost:8765/room1", port=8000, user_dir=None):
        self.address = address
        self.port = port
        self.user_dir = user_dir or os.path.join(BASE_DIR, "user")
        self.httpd = None
        self.threads = []

    def _serve_http(self):
        user_dir = self.user_dir

        class Handler(SimpleHTTPRequestHandler):
            def do_GET(self):
                if self.path.split("?")[0] == "/keymap.json":
                    body = json.dumps(build_keymap(), ensure_ascii=False).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                return super().do_GET()

        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), lambda *a, **kw: Handler(*a, directory=user_dir, **kw))
        print(f"http server on http://0.0.0.0:{self.port} serving {user_dir}")
        self.httpd.serve_forever()


    def _run_server(self):
        import server
        asyncio.run(server.main())

    def _run_client(self):
        window = MainWindow()
        def _run():
            ws = WebSocketClient(self.address, PipeUInputHandler().handle, window.control)
            asyncio.run(ws.run())
        threading.Thread(target=_run).start()
        window.run()

    def _spawn(self, target):
        pid = os.fork()
        if pid == 0:
            target()
            sys.exit(0)
        self.threads.append(pid)

    def start(self):
        self._spawn(self._run_server)
        self._spawn(self._serve_http)
        self._spawn(self._run_client)

    def stop(self):
        for pid in self.threads:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.threads.clear()


if __name__ == "__main__":
    rc = RemoteControl()

    def shutdown(signum, frame):
        rc.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    rc.start()
    signal.pause()

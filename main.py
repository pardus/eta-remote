#!/usr/bin/env python
"""Starts the relay server, http server, and client service."""

import os
import sys
import signal

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for sub in ("client", "server"):
    sys.path.insert(0, os.path.join(BASE_DIR, sub))

from websocket import WebSocketClient
from main import PipeUInputHandler


class RemoteControl:
    def __init__(self, address="ws://localhost:8765/room1", port=8000, user_dir=None):
        self.address = address
        self.port = port
        self.user_dir = user_dir or os.path.join(BASE_DIR, "user")
        self.httpd = None
        self.threads = []

    def _serve_http(self):
        handler = lambda *a, **kw: SimpleHTTPRequestHandler(  # noqa: E731
            *a, directory=self.user_dir, **kw
        )
        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), handler)
        print(f"http server on http://0.0.0.0:{self.port} serving {self.user_dir}")
        self.httpd.serve_forever()

    def _run_server(self):
        import asyncio
        import server
        asyncio.run(server.main())

    def _run_client(self):
        ws = WebSocketClient(self.address, PipeUInputHandler().handle)
        ws.run()

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

#!/usr/bin/env python
"""Starts the relay server, http server, and client service."""

import os
import sys
import signal
import json
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for sub in ("client", "server", "gui", "user"):
    sys.path.insert(0, os.path.join(BASE_DIR, sub))

from websocket import WebSocketClient
from main import PipeUInputHandler
from keymap import build_keymap

from translate import gen_translate

from Control import Control

class RemoteControl:
    def __init__(self, address="ws://localhost:8765/room1", port=8000, user_dir=None, clients=None):
        self.address = address
        self.port = port
        self.user_dir = user_dir or os.path.join(BASE_DIR, "user")
        self.httpd = None
        self.threads = []
        self.window = None
        self.ws_server = None
        self.client = None
        self.pipe_uinput = None
        self.clients_box = clients

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
                elif self.path.split("?")[0] == "/translate.js":
                    client_language = self.headers.get('Accept-Language')
                    body = gen_translate(client_language).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/javascript; charset=utf-8")
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
        with server.serve(server.handler, "0.0.0.0", 8765, max_size=None) as ws_server:
            self.ws_server = ws_server
            ws_server.serve_forever()

    def _run_client(self):
        self.pipe_uinput = PipeUInputHandler()
        self.client = WebSocketClient(self.address, self.pipe_uinput.handle, self.window.control)
        self.client.run()

    def _spawn(self, target):
        t = threading.Thread(target=target, daemon=True)
        t.start()
        self.threads.append(t)

    def _shutdown(self, *_args):
        self.stop()
        return GLib.SOURCE_REMOVE

    def start(self):
        self.window = Control(clients=self.clients_box)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._shutdown)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._shutdown)
        self._spawn(self._run_server)
        self._spawn(self._serve_http)
        self._spawn(self._run_client)

    def stop(self):
        if self.client:
            self.client.stop()
        if self.httpd:
            self.httpd.shutdown()
        if self.ws_server:
            self.ws_server.shutdown()
        self.pipe_uinput.stop()
        self.ws_server = None
        self.httpd = None
        self.client = None
        del self.pipe_uinput
        self.threads.clear()

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
from utils import load_config

from translate import gen_translate

from Control import Control

class RemoteControl:
    def __init__(self, address=None, room="room1", port=None, user_dir=None, clients=None):
        config = load_config()
        ws_config = config.get("ws", {})
        httpd_config = config.get("httpd", {})
        if address is None:
            host = ws_config.get("address", "ws://127.0.0.1")
            ws_port = ws_config.get("port", 8765)
            address = f"{host}:{ws_port}"
        if port is None:
            port = httpd_config.get("port", 8000)
        self.address = address + "/"+ room
        self.room = room
        self.port = port
        self.httpd_address = httpd_config.get("address") or "0.0.0.0"
        self.ws_host = ws_config.get("server") or "0.0.0.0"
        self.ws_port = ws_config.get("port", 8765)
        self.user_dir = user_dir or os.path.join(BASE_DIR, "user")
        self.httpd = None
        self.threads = []
        self.window = None
        self.ws_server = None
        self.client = None
        self.pipe_uinput = None
        self.clients_box = clients

        print(config)

    def _make_http_server(self):
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
                if self.path.split("?")[0] == "/config.json":
                    body = json.dumps(load_config(), ensure_ascii=False).encode()
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

        print(f"http server on http://{self.httpd_address}:{self.port} serving {user_dir}")
        return ThreadingHTTPServer((self.httpd_address, self.port), lambda *a, **kw: Handler(*a, directory=user_dir, **kw))

    def _serve_http(self):
        self.httpd.serve_forever()

    def _run_server(self):
        with self.ws_server:
            self.ws_server.serve_forever()

    def _run_client(self):
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
        # Create every long-lived object here, before any thread is spawned,
        # so stop() can never observe a half-initialized service.
        import server
        try:
            if self.ws_host == "0.0.0.0":
                self.ws_server = server.serve(server.handler, self.ws_host, self.ws_port, max_size=None)
            if self.httpd_address == "0.0.0.0":
                self.httpd = self._make_http_server()
            self.pipe_uinput = PipeUInputHandler()
            self.client = WebSocketClient(self.address, self.pipe_uinput.handle, self.window.control)
        except:
            self.stop()
            raise
        if self.ws_host == "0.0.0.0":
            self._spawn(self._run_server)
        if self.httpd_address == "0.0.0.0":
            self._spawn(self._serve_http)
        self._spawn(self._run_client)

    def stop(self):
        if self.client:
            self.client.stop()
        if self.httpd:
            self.httpd.shutdown()
        if self.ws_server:
            self.ws_server.shutdown()
        if self.pipe_uinput:
            self.pipe_uinput.stop()
        if self.window:
            self.window.stop()
        self.ws_server = None
        self.httpd = None
        self.client = None
        self.pipe_uinput = None
        for t in self.threads:
            t.join(timeout=5)
        self.threads.clear()

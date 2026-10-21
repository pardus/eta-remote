import gi
import time
import threading
import traceback

gi.require_version("Gtk", "3.0")

from file import handle_file

from websockets.exceptions import ConnectionClosed

from gi.repository import Gtk, GLib, Gio

from NewConnection import NewConnection
from Clients import Clients

from protocol import pack_perms, pack_file_ack, pack_kick

allow_lock = threading.RLock()

all_permissions = {
    "audio": ["audio"],
    "input": [
        "mouse", "key", "touch", "wheel", "touchpad"
    ],
    "image": ["image", "request_full"],
    "misc": ["quality"],
    "file": ["file"]
}


class Control:
    def __init__(self, clients=None):
        self.settings = Gio.Settings.new("tr.org.pardus.eta-remote")
        self.allows = {}
        self.ncs = {}
        self.clients = clients or Clients(self)
        self.clients.Controller = self
        self.ws = None
        self.ws_lock = threading.Lock()

    def _stack(self):
        return self.clients.get_parent()

    def _show_clients(self):
        stack = self._stack()
        if stack is not None:
            stack.set_visible_child(self.clients)
        toplevel = self.clients.get_toplevel()
        if isinstance(toplevel, Gtk.Window):
            toplevel.show_all()
            toplevel.present()

    def _show_main(self):
        stack = self._stack()
        if stack is not None:
            stack.set_visible_child_name("main")

    def _update_ui(self):
        if threading.current_thread() is not threading.main_thread():
            GLib.idle_add(self._update_ui)
            return
        self.clients._update()

    def send_ws(self, message):
        """Thread-safe websocket send; safe from any thread."""
        with self.ws_lock:
            ws = self.ws
        if ws is None:
            return
        try:
            ws.send(message)
        except ConnectionClosed:
            with self.ws_lock:
                if self.ws is ws:
                    self.ws = None
        except:
            print(traceback.format_exc())

    def stop(self):
        self.allows = {}
        with self.ws_lock:
            if self.ws:
                self.ws.close()
            self.ws = None
        self._update_ui()

    def is_user_input(self):
        with allow_lock:
            for cl in self.allows.keys():
                if (time.time() - self.allows[cl]["time"] < 0.3):
                    return True
        return False

    def set_permission(self, perm, client_id, status):
        if perm not in all_permissions:
            return
        with allow_lock:
            if status:
                if perm not in self.allows[client_id]["perm"]:
                    self.allows[client_id]["perm"].append(perm)
            else:
                if perm in self.allows[client_id]["perm"]:
                    self.allows[client_id]["perm"].remove(perm)
        self._update_ui()
        self._notify_perms(client_id)

    def _notify_perms(self, client_id):
        with allow_lock:
            perms = self.allows.get(client_id, {}).get("perm", [])
        msg = pack_perms(
            "audio" in perms,
            "file" in perms,
            "image" in perms,
            "input" in perms,
            target_ids=[client_id],
        )
        self.send_ws(msg)

    def _connect(self, data, client_id):
        with allow_lock:
            self.allows[client_id] = {"perm": [], "data": data, "time": time.time(), "new-connection": None}
        self._show_clients()
        if self.settings.get_boolean("auto-allow"):
            self.set_permission("image", client_id, True)
        else:
            nc = NewConnection(self, data)
            self.ncs[client_id] = nc
            nc.show_all()
        self._notify_perms(client_id)

    def _disconnect(self, client_id):
        with allow_lock:
            if client_id in self.allows.keys():
                nc = self.ncs.get(client_id)
                if nc:
                    nc.destroy()
                self.allows.pop(client_id)
        if not self.allows:
            self._show_main()
        self._update_ui()

    def control(self, ctx):
        """Filter and route one parsed websocket message."""
        with self.ws_lock:
            self.ws = ctx.websocket
        try:
            data = ctx.message
            if data is None:
                return False
            client_id = data.get("id")
            kind = data.get("type")
            if kind == "connect":
                ctx.wait = False
                GLib.idle_add(self._connect, data, client_id)
            elif kind == "disconnect":
                ctx.wait = (len(self.allows.keys()) == 0)
                GLib.idle_add(self._disconnect, client_id)

            with allow_lock:
                data["target"] = []
                for cl in list(self.allows.keys()):
                    for perm in self.allows[cl].get("perm", []) + ["misc"]:
                        if kind in all_permissions.get(perm, []):
                            data["target"].append(cl)
                            break
            ctx.message = data
        except:
            print(traceback.format_exc())
            return False

        with allow_lock:
            if client_id in self.allows.keys() and kind in all_permissions["input"]:
                self.allows[client_id]["time"] = time.time()

        allowed = (client_id is None or client_id in data["target"] or kind in ["connect", "disconnect"])
        with allow_lock:
            if len(self.allows.keys()) == 0:
                allowed = False

        if not allowed:
            return False

        if kind == "file":
            def file_ack(name, chunk, complete):
                try:
                    ack = pack_file_ack(name, chunk, complete)
                    self.send_ws(ack)
                except:
                    print(traceback.format_exc())
            threading.Thread(target=handle_file, args=(data, file_ack), daemon=True).start()
        else:
            return True

        return False

    def kick_client(self, client_id):
        """Kick a client by ID."""
        msg = pack_kick(client_id)
        self.send_ws(msg)
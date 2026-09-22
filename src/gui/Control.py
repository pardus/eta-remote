import gi
import json
import time
import threading
import traceback

gi.require_version("Gtk", "3.0")

from file import handle_file

from websockets.exceptions import ConnectionClosed

from gi.repository import Gtk, GLib, Gio

from NewConnection import NewConnection
from Clients import Clients

allow_lock = threading.RLock()

all_permissions = {
    "audio":["audio"],
    "input":[
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
        self.clients = clients or Clients(self)
        self.clients.Controller = self
        self.ws = None

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
        print(json.dumps(self.allows, indent=2))
        self.clients._update()

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
        if self.ws is None:
            return
        perms = {"audio": "audio" in perms, "file": "file" in perms, "image": "image" in perms, "input": "input" in perms}
        msg = json.dumps({
            "type": "perms",
            "target": [client_id],
            **perms
        })
        try:
            self.ws.send(msg)
        except ConnectionClosed:
            self.ws = None
        except:
            print(traceback.format_exc())

    def _connect(self, data, client_id):
        with allow_lock:
            self.allows[client_id] = {"perm":[], "data":data, "time": time.time()}
        self._show_clients()
        if self.settings.get_boolean("auto-allow"):
            self.set_permission("image", client_id, True)
        else:
            NewConnection(self, data).show_all()
        self._notify_perms(client_id)

    def _disconnect(self, client_id):
        with allow_lock:
            if client_id in self.allows.keys():
                self.allows.pop(client_id)
        if not self.allows:
            self._show_main()
        self._update_ui()

    def control(self, ctx):
        """control and filter websocket context"""
        self.ws = ctx.websocket
        try:
            data = json.loads(ctx.message)
            client_id = data.get("id")
            type = data.get("type")
            if type == "connect":
                ctx.wait = False
                GLib.idle_add(self._connect, data, client_id)
            elif type == "disconnect":
                ctx.wait = (len(self.allows.keys()) == 0)
                GLib.idle_add(self._disconnect, client_id)

            with allow_lock:
                data["target"] = []
                for cl in list(self.allows.keys()):
                    for perm in self.allows[cl].get("perm",[]) + ["misc"]:
                        if type in all_permissions.get(perm, []):
                            data["target"].append(cl)
                            break
            ctx.message = json.dumps(data)
        except:
            print(traceback.format_exc())
            return False

        with allow_lock:
            if client_id in self.allows.keys() and type in all_permissions["input"]:
                self.allows[client_id]["time"] = time.time()

        allowed = (client_id == None or client_id in data["target"] or type in ["connect", "disconnect"])
        with allow_lock:
            if len(self.allows.keys()) == 0:
                allowed = False

        if not allowed:
            return False

        if type == "file":
            def file_ack(name, chunk, complete):
                try:
                    ack = json.dumps({"type": "file_ack", "name": name, "chunk": chunk, "complete": complete})
                    if self.ws:
                        self.ws.send(ack)
                except:
                    print(traceback.format_exc())
            threading.Thread(target=handle_file, args=(data, file_ack), daemon=True).start()
        else:
            return True

        return False

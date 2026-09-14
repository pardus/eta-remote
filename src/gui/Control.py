import gi
import json
import traceback

gi.require_version("Gtk", "3.0")

from file import handle_file

from gi.repository import Gtk, GLib, Gio

from NewConnection import NewConnection

default_allow = [
    "image", "mouse", "key", "touch", "request_full",
    "wheel", "quality", "permission", "file"
]

class Control(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.settings = Gio.Settings.new("tr.org.pardus.eta-remote")
        self.allows = {}

    def _allow(self, client_id):
        if client_id:
            self.allows[client_id] = default_allow.copy()

    def control(self, ctx):
        """control and filter websocket context"""
        try:
            data = json.loads(ctx.message)
            client_id = data.get("id")
            type = data.get("type")
            if type == "connect":
                ctx.wait = False
                if self.settings.get_boolean("auto-allow"):
                    GLib.idle_add(self._allow, client_id)
                else:
                    GLib.idle_add(lambda: NewConnection(data, self._allow).show_all())
            elif type == "disconnect":
                if client_id in self.allows:
                    self.allows.pop(client_id)
                ctx.wait = (len(self.allows.keys()) == 0)

            data["target"] = []
            for cl in self.allows.keys():
                if type in self.allows.get(cl):
                    data["target"].append(cl)
            ctx.message = json.dumps(data)
        except:
            print(traceback.format_exc())
            return False

        allowed = (client_id == None or client_id in data["target"])
        if len(self.allows.keys()) == 0:
            allowed = False

        if not allowed:
            return False

        if type == "permission":
            for perm in data.keys():
                if perm == "type":
                    continue
                if data[perm]:
                    if perm not in self.allows[client_id]:
                        self.allows[client_id].append(perm)
                elif perm in self.allows[client_id]:
                    self.allows[client_id].remove(perm)

        if type == "file":
            handle_file(data)
        else:
            return True

        return False

    def run(self):
        Gtk.main()

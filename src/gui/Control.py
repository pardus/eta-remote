import gi
import json
import traceback

gi.require_version("Gtk", "3.0")

from file import handle_file

from gi.repository import Gtk, GLib, Gio

from NewConnection import NewConnection

all_permissions = {
    "audio":["audio"],
    "input":[
        "mouse", "key", "touch", "wheel"
    ],
    "image": ["image", "request_full"],
    "misc": ["quality", "permission", "file"]
}

class Control(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.settings = Gio.Settings.new("tr.org.pardus.eta-remote")
        self.allows = {}
        self.kick = None

    def _update_ui(self):
        print(json.dumps(self.allows, indent=2))

    def set_permission(self, perm, client_id, status):
        if perm not in all_permissions:
            return
        if status:
            if perm not in self.allows[client_id]["perm"]:
                self.allows[client_id]["perm"].append(perm)
        else:
            if perm in self.allows[client_id]["perm"]:
                self.allows[client_id]["perm"].remove(perm)
        self._update_ui()

    def _connect(self, data, client_id):
        self.allows[client_id] = {"perm":[], "data":data}
        if self.settings.get_boolean("auto-allow"):
            self.set_permission("input", client_id, True)
            self.set_permission("image", client_id, True)
        else:
            NewConnection(self, data).show_all()

    def _disconnect(self, client_id):
        if client_id in self.allows.keys():
            self.allows.pop(client_id)
        self._update_ui()

    def control(self, ctx):
        """control and filter websocket context"""
        try:
            data = json.loads(ctx.message)
            client_id = data.get("id")
            type = data.get("type")
            if self.kick:
                ctx.data.append({"kick":self.kick})
            if type == "connect":
                ctx.wait = False
                GLib.idle_add(self._connect, data, client_id)
            elif type == "disconnect":
                ctx.wait = (len(self.allows.keys()) == 1)
                GLib.idle_add(self._disconnect, client_id)

            data["target"] = []
            for cl in self.allows.keys():
                for perm in self.allows[cl].get("perm",[]) + ["misc"]:
                    if type in all_permissions.get(perm, []):
                        data["target"].append(cl)
                        break
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
                self.set_permission(perm, client_id, data.get(perm, False))
            GLib.idle_add(self._update_ui)

        if type == "file":
            handle_file(data)
        else:
            return True

        return False

    def run(self):
        Gtk.main()

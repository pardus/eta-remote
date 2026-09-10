import gi
import json
import traceback

gi.require_version("Gtk", "3.0")

from file import handle_file

from gi.repository import Gtk, GLib, Gio

default_allow = [
    "image", "mouse", "key", "touch", "request_full",
    "wheel", "quality", "permission", "file"
]

class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.label=Gtk.Label()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.settings = Gio.Settings.new("tr.org.pardus.eta-remote")
        button = Gtk.Button(label="Allow")
        button.connect("clicked", self._allow)
        box.pack_start(self.label, True, True, 0)
        box.pack_start(button, False, False, 0)
        self._client_id = None
        self.add(box)
        self.allows = {}

    def _allow(self, widget):
        if self._client_id:
            self.allows[self._client_id] = default_allow.copy()
            self.hide()

    def control(self, ctx):
        """control and filter websocket context"""
        try:
            data = json.loads(ctx.message)
            client_id = data.get("id")
            type = data.get("type")
            if type == "connect":
                GLib.idle_add(self.label.set_text, json.dumps(data, indent=4))
                self._client_id = client_id
                if self.settings.get_boolean("auto-allow"):
                    GLib.idle_add(self._allow, None)
                else:
                    self.show_all()
            elif type == "disconnect":
                if client_id in self.allows:
                    self.allows.pop(client_id)

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

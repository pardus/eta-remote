import gi
import json
import traceback

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib

class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.label=Gtk.Label()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        button = Gtk.Button(label="Allow")
        button.connect("clicked", self._allow)
        box.pack_start(self.label, True, True, 0)
        box.pack_start(button, False, False, 0)
        self._client_id = None
        self.add(box)
        self.allows = []

    def _allow(self, widget):
        if self._client_id:
            self.allows.append(self._client_id)
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
                self.show_all()
            elif type == "disconnect":
                self.allows.remove(client_id)

            data["target"] = self.allows
            ctx.message = json.dumps(data)
        except:
            print(traceback.format_exc())
            return False
        return client_id == None or client_id in self.allows

    def run(self):
        Gtk.main()

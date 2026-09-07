import gi
import json

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib

class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.label=Gtk.Label()
        self.add(self.label)
        self.allows = []

    def control(self, ctx):
        """control and filter websocket context"""
        try:
            data = json.loads(ctx.message)
            client_id = data.get("id")
            type = data.get("type")
            if type == "connect":
                GLib.idle_add(self.label.set_text, json.dumps(data, indent=4))
                self.show_all()

            # TODO: remove auto allow
            if client_id not in self.allows:
                self.allows.append(client_id)

            data["target"] = self.allows
            ctx.message = json.dumps(data)
        except Exception as e:
            print(e)
            return False
        return client_id in self.allows

    def run(self):
        Gtk.main()

import gi
import json

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib

class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.label=Gtk.Label()
        self.add(self.label)

    def control(self, ctx):
        """control and filter websocket context"""
        try:
            data = json.loads(ctx.message)
            if data.get("type") == "connect":
                GLib.idle_add(self.label.set_text, json.dumps(data, indent=4))
                self.show_all()
            if "type" in data:
                print(data.get("type"), data.get("id"))
        except Exception as e:
            print(e)
            return False
        return True

    def run(self):
        Gtk.main()

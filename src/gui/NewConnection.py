import gi
import json

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gio

class NewConnection(Gtk.Window):
    def __init__(self, data, allow):
        super().__init__()

        client_id = data.get("id")

        self.label=Gtk.Label()
        self.label.set_text(json.dumps(data, indent=4))

        def _allow(widget):
            allow(client_id)
            self.destroy()
        button = Gtk.Button(label="Allow")
        button.connect("clicked", _allow)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self.label, True, True, 0)
        box.pack_start(button, False, False, 0)
        self.add(box)



import gi
import json

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gio

class NewConnection(Gtk.Window):
    def __init__(self, Controller, data):
        super().__init__()

        client_id = data.get("id")
        self.allowed = False

        self.label=Gtk.Label()
        self.label.set_text(json.dumps(data, indent=4))

        def _allow(*args):
            Controller.set_permission("input", client_id, True)
            Controller.set_permission("image", client_id, True)
            self.allowed = True
            self.destroy()
        button = Gtk.Button(label="Allow")
        button.connect("clicked", _allow)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self.label, True, True, 0)
        box.pack_start(button, False, False, 0)


        def _destroy(*args):
            if not self.allowed:
                Controller.kick = client_id

        self.connect("destroy", _destroy)

        self.add(box)



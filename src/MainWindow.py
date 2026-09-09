import sys
import os
import signal
import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gdk, GLib, Gio

import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

if os.path.isfile(f"{BASE_DIR}/../data/gschemas.compiled"):
    os.environ["GSETTINGS_SCHEMA_DIR"] = f"{BASE_DIR}/../data/"

from remote import RemoteControl

class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Remote Control")
        self.set_default_size(360, 280)
        self.set_resizable(False)

        self.pid = 0
        self.settings = Gio.Settings.new("tr.org.pardus.eta-remote")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.get_style_context().add_class("window")

        title = Gtk.Label(label="Remote Control")
        title.get_style_context().add_class("title")
        outer.pack_start(title, False, False, 0)

        addr_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        addr_box.set_margin_top(12)
        host_label = Gtk.Label(label=f"Address: 0.0.0.0")
        host_label.get_style_context().add_class("address")
        port_label = Gtk.Label(label=f"HTTP Port: 8000")
        port_label.get_style_context().add_class("address")
        addr_box.pack_start(host_label, False, False, 0)
        addr_box.pack_start(port_label, False, False, 0)
        outer.pack_start(addr_box, False, False, 0)

        self.status_label = Gtk.Label(label="Status: Stopped")
        self.status_label.get_style_context().add_class("status")
        self.status_label.set_margin_top(16)
        outer.pack_start(self.status_label, False, False, 0)

        autostart_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        autostart_box.set_halign(Gtk.Align.CENTER)
        autostart_box.set_margin_top(16)
        autostart_label = Gtk.Label(label="Autostart on boot")
        self.autostart_switch = Gtk.Switch()
        self.autostart_switch.set_active(self.settings.get_boolean("autostart"))
        self.autostart_switch.connect("state-set", self._on_autostart_toggled)
        autostart_box.pack_start(autostart_label, False, False, 0)
        autostart_box.pack_start(self.autostart_switch, False, False, 4)
        outer.pack_start(autostart_box, False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(16)

        self.start_btn = Gtk.Button(label="  Start  ")
        self.start_btn.get_style_context().add_class("start-btn")
        self.start_btn.connect("clicked", self._on_start)

        self.stop_btn = Gtk.Button(label="  Stop  ")
        self.stop_btn.get_style_context().add_class("stop-btn")
        self.stop_btn.set_sensitive(False)
        self.stop_btn.connect("clicked", self._on_stop)

        btn_box.pack_start(self.start_btn, True, True, 0)
        btn_box.pack_start(self.stop_btn, True, True, 0)
        outer.pack_start(btn_box, False, False, 0)

        self.add(outer)
        self.connect("destroy", self._on_destroy)
        self._setup_status_icon()

    def _setup_status_icon(self):
        self.tray = Gtk.StatusIcon()
        self.tray.set_from_icon_name("network-transmit-receive")
        self.tray.set_tooltip_text("Remote Control")
        self.tray.connect("popup-menu", self._on_tray_menu)
        self.tray.connect("activate", self._on_tray_activate)

    def _on_tray_menu(self, _icon, button, time):
        menu = Gtk.Menu()

        start_item = Gtk.MenuItem(label="Start")
        start_item.connect("activate", lambda _: self._on_start(None))
        menu.append(start_item)

        stop_item = Gtk.MenuItem(label="Stop")
        stop_item.connect("activate", lambda _: self._on_stop(None))
        menu.append(stop_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda _: self._on_destroy(None))
        menu.append(quit_item)

        menu.show_all()
        menu.popup_at_pointer(None)

    def _on_tray_activate(self, _icon):
        if self.get_visible():
            self.hide()
        else:
            self.show_all()

    def _on_destroy(self, _widget):
        self._on_stop(_widget)
        Gtk.main_quit()

    def _on_start(self, _btn):
        if self.pid == 0:
            process = subprocess.Popen(
                [sys.executable, f"{BASE_DIR}/__main__.py"],
                start_new_session=True,
            )
            self.pid = process.pid
        self.start_btn.set_sensitive(False)
        self.stop_btn.set_sensitive(True)
        self.status_label.set_text("Status: Running")
        self.tray.set_tooltip_text("Remote Control - Running")

    def _on_stop(self, _btn):
        if self.pid != 0:
            try:
                os.killpg(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.pid = 0
        self.start_btn.set_sensitive(True)
        self.stop_btn.set_sensitive(False)
        self.status_label.set_text("Status: Stopped")
        self.tray.set_tooltip_text("Remote Control")

    def _on_autostart_toggled(self, _switch, state):
        self.settings.set_boolean("autostart", state)
        return True

    def run(self):
        Gtk.main()

if __name__ == "__main__":
    main = MainWindow()
    if "autostart" in sys.argv:
        if not main.settings.get_boolean("autostart"):
            sys.exit(0)
    if "show" in sys.argv:
        main.show_all()
    main.run()


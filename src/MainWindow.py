import sys
import os
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf

try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as appindicator
except:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3 as appindicator



import utils

from i18n import _

from remote import RemoteControl

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

if os.path.isfile(f"{BASE_DIR}/../data/gschemas.compiled"):
    os.environ["GSETTINGS_SCHEMA_DIR"] = f"{BASE_DIR}/../data/"

class MainWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title=_("Eta Remote Control"), application=app)
        self.set_default_size(360, 360)
        self.set_resizable(False)

        header = Gtk.HeaderBar()
        self.set_titlebar(header)
        header.set_show_close_button(True)
        header.set_title(_("Remote Control"))

        self.settings = Gio.Settings.new("tr.org.pardus.eta-remote")
        self.remote = None
        self.started = False

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.addr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.addr_box.set_margin_top(12)
        outer.pack_start(self.addr_box, False, False, 0)


        self.status_label = Gtk.Label(label=_("Status: Stopped"))
        self.status_label.set_margin_top(16)
        outer.pack_start(self.status_label, False, False, 0)


        options = [
            {"name": "autostart", "label": _("Autostart on boot")},
            {"name": "auto-allow", "label":_("Allow all new connections")}
        ]
        for option in options:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_halign(Gtk.Align.CENTER)
            box.set_margin_top(16)

            switch = Gtk.Switch()
            switch.set_active(self.settings.get_boolean(option["name"]))
            switch.connect("state-set", self._on_settings_toggled, option["name"])

            box.pack_start(Gtk.Label(label=option["label"]), False, False, 0)
            box.pack_start(switch, False, False, 4)
            outer.pack_start(box, False, False, 0)


        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(16)

        self.start_btn = Gtk.Button(label="  {}  ".format(_("Start")))
        self.start_btn.connect("clicked", self.on_start)

        self.stop_btn = Gtk.Button(label="  {}  ".format(_("Stop")))
        self.stop_btn.set_sensitive(False)
        self.stop_btn.connect("clicked", self._on_stop)

        btn_box.pack_start(self.start_btn, True, True, 0)
        btn_box.pack_start(self.stop_btn, True, True, 0)

        outer.pack_start(Gtk.Label(), True, True, 0)
        outer.pack_start(btn_box, False, False, 0)

        outer.pack_start(Gtk.Label(), True, True, 0)
        outer.pack_start(Gtk.Separator(), False, False, 0)
        outer.pack_start(Gtk.Label(label="© TÜBİTAK BİLGEM"), False, False, 0)


        self.add(outer)
        self.connect("delete-event", self._on_delete_event)
        self._setup_status_icon()
        self._refresh_addr_box()

    def _make_qr(self, data):
        import io
        import qrcode
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        loader = GdkPixbuf.PixbufLoader.new_with_type("png")
        loader.write(buffer.read())
        loader.close()
        return loader.get_pixbuf()

    def _refresh_addr_box(self, *_args):
        for child in self.addr_box.get_children():
            self.addr_box.remove(child)
        for ip, dev in utils.get_local_ip():
            url = f"http://{ip}:8000"
            qr_img = Gtk.Image.new_from_pixbuf(self._make_qr(url))
            qr_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            qr_img.set_margin_bottom(2)
            qr_box.pack_start(Gtk.Label(label=dev), False, False, 0)
            qr_box.pack_start(qr_img, False, False, 0)
            qr_box.pack_start(Gtk.Label(label=url), False, False, 0)
            self.addr_box.pack_start(qr_box, True, True, 0)
        self.addr_box.show_all()

    def _setup_status_icon(self):
        self.indicator = appindicator.Indicator.new(
            "eta-remote", "tr.org.pardus.eta-remote-stopped", appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.indicator.set_title(_("Remote Control"))

        self.indicator.set_menu(self._on_tray_menu())

    def _on_tray_menu(self):
        menu = Gtk.Menu()

        show_item = Gtk.MenuItem(label=_("Show"))
        show_item.connect("activate", lambda _: self.show_and_present())
        menu.append(show_item)

        menu.append(Gtk.SeparatorMenuItem())

        if not self.started:
            start_item = Gtk.MenuItem(label=_("Start"))
            start_item.connect("activate", lambda _: self.on_start(None))
            menu.append(start_item)
        else:
            stop_item = Gtk.MenuItem(label=_("Stop"))
            stop_item.connect("activate", lambda _: self._on_stop(None))
            menu.append(stop_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label=_("Quit"))
        quit_item.connect("activate", self._on_quit)
        menu.append(quit_item)

        menu.show_all()
        return menu

    def _on_quit(self, widget):
        self._on_stop(widget)
        self.get_application().quit()

    def show_and_present(self):
        self.show_all()
        self.present()
        self._refresh_addr_box()

    def _on_tray_activate(self, _icon):
        self.show_and_present()

    def _on_delete_event(self, _widget, _event):
        self.hide()
        return True

    def on_start(self, _btn):
        if self.remote is None:
            self.remote = RemoteControl()
            self.remote.start()
        self.started = True
        self.start_btn.set_sensitive(False)
        self.stop_btn.set_sensitive(True)
        self.status_label.set_text(_("Status: Running"))
        self.indicator.set_title(_("Remote Control - Running"))
        self.indicator.set_icon(("tr.org.pardus.eta-remote-started"))

    def _on_stop(self, _btn):
        if self.remote is not None:
            self.remote.stop()
            self.remote = None
        self.started = False
        self.start_btn.set_sensitive(True)
        self.stop_btn.set_sensitive(False)
        self.status_label.set_text(_("Status: Stopped"))
        self.indicator.set_title(_("Remote Control"))
        self.indicator.set_icon(("tr.org.pardus.eta-remote-stopped"))

    def _on_settings_toggled(self, _switch, state, name=""):
        self.settings.set_boolean(name, state)
        return True


import io
import os
import sys

import uuid
import qrcode

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as appindicator
except (ImportError, ValueError):
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3 as appindicator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "..", "data")
if os.path.isfile(os.path.join(DATA_DIR, "gschemas.compiled")):
    os.environ["GSETTINGS_SCHEMA_DIR"] = DATA_DIR

GUI_DIR = os.path.join(BASE_DIR, "gui")

import utils

from gui.Clients import Clients
from i18n import _
from remote import RemoteControl


class MainWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title=_("Eta Remote Control"), application=app)
        self.set_default_size(720, 560)
        self.set_icon_name("tr.org.pardus.eta-remote")

        header = Gtk.HeaderBar()
        header.set_title(_("Eta Remote Control"))
        self.set_titlebar(header)
        header.set_show_close_button(True)

        self.settings = Gio.Settings.new("tr.org.pardus.eta-remote")
        self.remote = None
        self.started = False

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        self.stack.add_titled(self._build_connect_page(), "main", _("Remote Control"))
        self.registry = Clients()
        self.stack.add_titled(self.registry, "clients", _("Connected Clients"))

        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_halign(Gtk.Align.CENTER)
        header.set_custom_title(switcher)

        self.add(self.stack)
        self.connect("delete-event", self._on_delete_event)
        self._room = utils.get_uid()
        self._setup_status_icon()
        self._refresh_addr_box()

    def _build_connect_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_top(16)
        header.set_margin_start(16)
        header.set_margin_end(16)
        header.set_margin_bottom(10)

        title = Gtk.Label()
        app_name = GLib.markup_escape_text(_("Eta Remote Control"))
        title.set_markup(f"<span size='xx-large' weight='bold'>{app_name}</span>")
        title.set_halign(Gtk.Align.START)
        header.pack_start(title, True, True, 0)

        subtitle = Gtk.Label()
        subtitle.set_markup(
            f"<span size='small' foreground='#888888'>{GLib.markup_escape_text(_('Scan a QR code with your phone or tablet to connect'))}</span>"
        )
        subtitle.set_halign(Gtk.Align.END)
        subtitle.set_valign(Gtk.Align.CENTER)
        header.pack_end(subtitle, False, False, 0)

        page.pack_start(header, False, False, 0)
        page.pack_start(Gtk.Separator(), False, False, 3)

        self.addr_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.addr_box.set_homogeneous(True)
        self.addr_box.set_halign(Gtk.Align.CENTER)
        self.addr_box.set_valign(Gtk.Align.CENTER)
        self.addr_box.set_size_request(680, -1)
        self.addr_box.set_margin_top(16)
        self.addr_box.set_margin_bottom(16)
        self.addr_box.set_margin_start(16)
        self.addr_box.set_margin_end(16)
        
        page.pack_start(self.addr_box, False, False, 0)
        page.pack_start(Gtk.Label(), True, True, 0)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        bottom.set_margin_start(16)
        bottom.set_margin_end(16)
        bottom.set_margin_top(6)
        bottom.set_margin_bottom(12)

        bottom.pack_start(self._build_settings_box(), False, False, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_valign(Gtk.Align.CENTER)

        self.start_btn = Gtk.Button(label=_("Start"))
        self.start_btn.set_size_request(110, 40)
        self.start_btn.connect("clicked", self.on_start)

        self.stop_btn = Gtk.Button(label=_("Stop"))
        self.stop_btn.set_size_request(110, 40)
        self.stop_btn.set_sensitive(False)
        self.stop_btn.connect("clicked", self._on_stop)

        btn_box.pack_start(self.start_btn, False, False, 0)
        btn_box.pack_start(self.stop_btn, False, False, 0)
        bottom.pack_end(btn_box, True, True, 0)

        page.pack_start(bottom, False, False, 0)

        footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        footer.pack_start(Gtk.Separator(), False, False, 3)
        footer_label = Gtk.Label()
        footer_label.set_markup(f"<span size='small' foreground='#888888'>© TÜBİTAK BİLGEM</span>")
        footer_label.set_margin_top(4)
        footer_label.set_margin_bottom(4)
        footer.pack_start(footer_label, False, False, 0)
        page.pack_start(footer, False, False, 0)

        return page

    def _build_settings_box(self):
        holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        holder.set_halign(Gtk.Align.CENTER)

        options = [
            {"name": "autostart", "label": _("Autostart on boot")},
            {"name": "auto-allow", "label": _("Allow all new connections")},
        ]
        for option in options:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
            label = Gtk.Label(label=option["label"])
            label.set_halign(Gtk.Align.START)

            switch = Gtk.Switch()
            switch.set_active(self.settings.get_boolean(option["name"]))
            switch.connect("state-set", self._on_settings_toggled, option["name"])

            row.pack_start(label, True, True, 0)
            row.pack_start(switch, False, False, 0)
            holder.pack_start(row, False, False, 0)

        return holder

    def _make_qr(self, data):
        qr = qrcode.QRCode(box_size=5, border=2)
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

        addrs = utils.get_local_ip()
        if not addrs:
            label = Gtk.Label()
            label.set_markup(f"<span foreground='#888888'>{GLib.markup_escape_text(_('No active network connection found'))}</span>")
            self.addr_box.pack_start(label, True, True, 0)

        for ip, dev in addrs:
            box_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            url = f"http://{ip}:8000#{self._room}"

            qr_img = Gtk.Image.new_from_pixbuf(self._make_qr(url))
            qr_img.set_pixel_size(256)
            box.pack_start(qr_img, False, False, 0)

            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

            connect_label = Gtk.Label()
            connect_label.set_halign(Gtk.Align.START)
            connect_label.set_markup("<b>{}</b>".format(_("Connect to control this device remotely")))
            info_box.pack_start(connect_label, False, False, 0)

            info_box.pack_start(Gtk.Label(), True, True, 0)

            scan_label = Gtk.Label(label=_("Scan or copy this address:"))
            scan_label.set_halign(Gtk.Align.START)
            info_box.pack_start(scan_label, False, False, 5)

            url_label = Gtk.Entry()
            url_label.set_editable(False)
            url_label.set_can_focus(False)
            url_label.set_text(url)
            info_box.pack_start(url_label, False, False, 5)

            box.pack_start(info_box, True, True, 13)
            
            box_main.pack_start(box, True, True, 0)
            box_main.pack_start(Gtk.Separator(), False, False, 5)
            
            dev_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            dev_box.pack_start(Gtk.Label(label=_("Interface:")), False, False, 0)

            dev_label = Gtk.Label()
            dev_label.set_markup(f"<span foreground='#888888'>{GLib.markup_escape_text(dev)}</span>")
            dev_box.pack_start(dev_label, False, False, 21)

            box_main.pack_start(dev_box, False, False, 0)

            self.addr_box.pack_start(box_main, False, False, 0)
            

        self.addr_box.show_all()

    def _setup_status_icon(self):
        self.indicator = appindicator.Indicator.new(
            "eta-remote",
            "tr.org.pardus.eta-remote-stopped",
            appindicator.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.indicator.set_title(_("Remote Control"))
        self.indicator.set_menu(self._on_tray_menu())

    def _on_tray_menu(self):
        menu = Gtk.Menu()

        show_item = Gtk.MenuItem(label=_("Show"))
        show_item.connect("activate", lambda _: self.show_and_present())
        menu.append(show_item)

        menu.append(Gtk.SeparatorMenuItem())

        self.start_item = Gtk.MenuItem(label=_("Start"))
        self.start_item.connect("activate", lambda _: self.on_start(None))
        menu.append(self.start_item)

        self.stop_item = Gtk.MenuItem(label=_("Stop"))
        self.stop_item.connect("activate", lambda _: self._on_stop(None))
        menu.append(self.stop_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label=_("Quit"))
        quit_item.connect("activate", self._on_quit)
        menu.append(quit_item)

        menu.show_all()

        self.start_item.set_visible(not self.started)
        self.stop_item.set_visible(self.started)

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

    def _set_status(self, running):
        self.started = running
        self.start_btn.set_sensitive(not running)
        self.stop_btn.set_sensitive(running)

        if running:
            self.indicator.set_title(_("Remote Control - Running"))
            self.indicator.set_icon("tr.org.pardus.eta-remote-started")
        else:
            self.indicator.set_title(_("Remote Control"))
            self.indicator.set_icon("tr.org.pardus.eta-remote-stopped")

        self.start_item.set_visible(not self.started)
        self.stop_item.set_visible(self.started)


    def on_start(self, _btn):
        if self.remote is None:
            self.remote = RemoteControl(clients=self.registry, address="ws://127.0.0.1:8765", room=self._room)
            self.remote.start()
        self._set_status(True)

    def _on_stop(self, _btn):
        if self.remote is not None:
            self.remote.stop()
            self.remote = None
        self._set_status(False)

    def _on_settings_toggled(self, _switch, state, name):
        self.settings.set_boolean(name, state)

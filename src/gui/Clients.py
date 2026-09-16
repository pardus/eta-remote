import os
import re
import json
import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib, Gdk

from i18n import _

ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

PERMISSION_LABELS = {
    "input": _("Input"),
    "image": _("Image"),
    "audio": _("Audio"),
    "file": _("File")
}

PERMISSION_ICONS = {
    "input": "input.svg",
    "image": "image.svg",
    "audio": "audio.svg",
    "file": "file.svg",
}

def icon(name, size=None):
    path = os.path.join(ICONS_DIR, name)
    image = Gtk.Image.new_from_file(path)
    if size is not None:
        image.set_pixel_size(size)
    return image

def load_css():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clients.css")
    if not os.path.exists(path):
        return
    provider = Gtk.CssProvider()
    provider.load_from_path(path)
    screen = Gdk.Screen.get_default()
    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

def get_os(useragent, platform=None):
    ua = (useragent or "").lower()
    if "android" in ua:
        match = re.search(r"android ([\d.]+)", ua)
        if match:
            return f"Android {match.group(1)}"
        return "Android"
    if "iphone" in ua or "ipad" in ua or "ipod" in ua:
        return "iOS"
    if "cros" in ua or "crkey" in ua or "chromium os" in ua:
        return "Chrome OS"
    if "windows" in ua:
        match = re.search(r"windows nt (\d+\.\d+)", ua)
        if match:
            versions = {
                "10.0": "Windows 10/11",
                "6.3": "Windows 8.1",
                "6.2": "Windows 8",
                "6.1": "Windows 7",
                "6.0": "Windows Vista",
                "5.1": "Windows XP",
            }
            return versions.get(match.group(1), "Windows")
        return "Windows"
    if "mac os x" in ua or "macintosh" in ua:
        match = re.search(r"mac os x ([\d._]+)", ua)
        if match:
            return f"macOS {match.group(1).replace('_', '.')}"
        return "macOS"
    if "linux" in ua or "x11" in ua:
        return "Linux"
    if platform:
        return str(platform)
    return _("Unknown")

def get_browser(useragent):
    ua = useragent or ""
    browsers = [
        ("edg/", "Edge"),
        ("opr/", "Opera"),
        ("opera/", "Opera"),
        ("samsungbrowser/", "Samsung Internet"),
        ("vivaldi/", "Vivaldi"),
        ("firefox/", "Firefox"),
        ("fxios/", "Firefox"),
        ("crios/", "Chrome"),
        ("chrome/", "Chrome"),
        ("safari/", "Safari"),
        ("trident/", "Internet Explorer"),
    ]
    for token, name in browsers:
        if token in ua.lower():
            return name
    return None

class Clients(Gtk.Window):
    def __init__(self, Controller):
        super().__init__(title=_("Connected Clients"))
        load_css()
        self.set_name("clients-window")
        self.Controller = Controller
        self.set_default_size(600, 300)

        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(False)
        self.header.set_title(_("Connected Clients"))
        self.set_titlebar(self.header)

        self.grid = Gtk.Grid()
        self.grid.set_column_spacing(0)
        self.grid.set_row_spacing(4)
        self.grid.set_margin_top(8)
        self.grid.set_margin_bottom(8)
        self.grid.set_margin_start(8)
        self.grid.set_margin_end(8)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.grid)

        self.add(scrolled)
        self.connect("delete-event", self._on_delete_event)
        self.connect("map", lambda _w: GLib.idle_add(self._move_bottom_right))

    def _move_bottom_right(self):
        display = self.get_display()
        monitor = display.get_primary_monitor()
        if monitor is None:
            return
        geometry = monitor.get_geometry()
        width, height = self.get_size()
        self.move(
            geometry.x + geometry.width - width,
            geometry.y + geometry.height - height,
        )
        return GLib.SOURCE_REMOVE

    def _on_delete_event(self, _widget, _event):
        return True

    def _update(self):
        if not self.Controller.allows:
            self.header.set_subtitle("")
            self.hide()
            return

        self.header.set_subtitle(_("%d connected") % len(self.Controller.allows))

        for child in self.grid.get_children():
            self.grid.remove(child)

        row = 0
        if "WAYLAND_DISPLAY" in os.environ:
            warning_label = Gtk.Label(label=_("Warning: Wayland support is experimental and may be unstable."))
            warning_label.get_style_context().add_class("warning-label")
            self.grid.attach(warning_label, 0, row, 1, 1)
            row += 1
            self.grid.attach(Gtk.Separator(), 0, row, 1, 1)
            row += 1
        for client_id, info in self.Controller.allows.items():
            self.grid.attach(self._build_row(client_id, info), 0, row, 1, 1)
            row += 1
            self.grid.attach(Gtk.Separator(), 0, row, 1, 1)
            row += 1

        self.grid.show_all()

    def _build_row(self, client_id, info):
        data = info.get("data", {})
        perms = info.get("perm", [])

        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        card.get_style_context().add_class("client-card")

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        avatar_name = "smartphone.svg" if data.get("mobile") else "computer.svg"
        avatar = icon(avatar_name, 44)
        avatar.set_valign(Gtk.Align.CENTER)
        avatar.get_style_context().add_class("client-avatar")
        header.pack_start(avatar, False, False, 0)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        info_box.set_hexpand(True)
        info_box.set_valign(Gtk.Align.CENTER)

        os_name = get_os(data.get("useragent"), data.get("platform"))
        os_label = Gtk.Label()
        os_label.set_markup(f"<b>{GLib.markup_escape_text(os_name)}</b>")
        os_label.set_halign(Gtk.Align.START)
        os_label.get_style_context().add_class("client-name")

        detail = []
        browser = get_browser(data.get("useragent"))
        if browser:
            detail.append(browser)
        if data.get("mobile"):
            detail.append(_("Mobile"))
        if data.get("language"):
            detail.append(data["language"])
        detail_label = Gtk.Label(label=" · ".join(detail))
        detail_label.set_halign(Gtk.Align.START)
        detail_label.get_style_context().add_class("client-detail")

        id_label = Gtk.Label(label=client_id)
        id_label.set_halign(Gtk.Align.START)
        id_label.set_selectable(True)
        id_label.get_style_context().add_class("client-id")

        info_box.pack_start(os_label, False, False, 0)
        info_box.pack_start(detail_label, False, False, 0)
        info_box.pack_start(id_label, False, False, 0)
        header.pack_start(info_box, True, True, 0)

        card.pack_start(header, True, True, 0)
        card.pack_start(Gtk.Separator(), False, False, 0)

        perm_grid = Gtk.Grid()
        perm_grid.set_column_spacing(8)
        perm_grid.set_row_spacing(6)
        perm_grid.set_halign(Gtk.Align.CENTER)
        for i, (perm, label) in enumerate(PERMISSION_LABELS.items()):
            toggle_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            toggle_box.get_style_context().add_class("perm-box")
            toggle_box.pack_start(icon(PERMISSION_ICONS[perm], 16), False, False, 0)
            switch = Gtk.Switch()
            switch.set_active(perm in perms)
            switch.set_valign(Gtk.Align.CENTER)
            switch.set_tooltip_text(label)
            switch.connect("state-set", self._on_permission, client_id, perm)
            toggle_box.pack_start(switch, False, False, 0)
            perm_grid.attach(toggle_box, i, 0, 1, 1)
        card.pack_start(perm_grid, False, False, 0)
        card.pack_start(Gtk.Separator(), False, False, 0)

        kick_btn = Gtk.Button()
        kick_btn.set_image(icon("kick.svg", 16))
        kick_btn.set_tooltip_text(_("Kick"))
        kick_btn.set_valign(Gtk.Align.CENTER)
        kick_btn.get_style_context().add_class("kick-btn")
        kick_btn.connect("clicked", self._on_kick, client_id)
        card.pack_start(kick_btn, False, False, 0)

        return card

    def _on_permission(self, _switch, state, client_id, perm):
        self.Controller.set_permission(perm, client_id, state)
        return True

    def _on_kick(self, _btn, client_id):
        self.Controller.ws.send(json.dumps({"kick": client_id}))
        GLib.idle_add(self.Controller._disconnect, client_id)
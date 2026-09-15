import re
import json
import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib

PERMISSION_LABELS = {
    "input": "Input",
    "image": "Image",
    "audio": "Audio",
}

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
    return "Unknown"

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
        super().__init__(title="Connected Clients")
        self.Controller = Controller
        self.set_default_size(400, 320)

        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(False)
        self.header.set_title("Connected Clients")
        self.set_titlebar(self.header)
        self.set_resizable(False)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.list_box.set_margin_top(8)
        self.list_box.set_margin_bottom(8)
        self.list_box.set_margin_start(8)
        self.list_box.set_margin_end(8)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.list_box)

        self.add(scrolled)
        self.connect("delete-event", self._on_delete_event)
        self.connect("map", lambda _w: GLib.idle_add(self._move_bottom_right))

    def _move_bottom_right(self):
        display = self.get_display()
        monitor = display.get_primary_monitor()
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

        self.header.set_subtitle(f"{len(self.Controller.allows)} connected")

        for child in self.list_box.get_children():
            self.list_box.remove(child)

        for client_id, info in self.Controller.allows.items():
            self.list_box.pack_start(self._build_row(client_id, info), False, False, 0)
            self.list_box.pack_start(Gtk.Separator(), False, False, 0)

        self.list_box.show_all()

    def _build_row(self, client_id, info):
        data = info.get("data", {})
        perms = info.get("perm", [])

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_bottom(4)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        os_name = get_os(data.get("useragent"), data.get("platform"))
        os_name += " - "+ client_id
        os_label = Gtk.Label()
        os_label.set_markup(f"<b>{GLib.markup_escape_text(os_name)}</b>")
        os_label.set_halign(Gtk.Align.START)

        detail = []
        browser = get_browser(data.get("useragent"))
        if browser:
            detail.append(browser)
        if data.get("mobile"):
            detail.append("Mobile")
        if data.get("language"):
            detail.append(data["language"])
        detail_label = Gtk.Label(label=" · ".join(detail))
        detail_label.set_halign(Gtk.Align.START)

        info_box.pack_start(os_label, False, False, 0)
        info_box.pack_start(detail_label, False, False, 0)
        row.pack_start(info_box, True, True, 0)

        toggles = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        for perm, label in PERMISSION_LABELS.items():
            toggle_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            toggle_box.pack_start(Gtk.Label(label=label), False, False, 0)
            switch = Gtk.Switch()
            switch.set_active(perm in perms)
            switch.connect("state-set", self._on_permission, client_id, perm)
            toggle_box.pack_start(switch, False, False, 0)
            toggles.pack_start(toggle_box, False, False, 0)
        row.pack_start(toggles, False, False, 0)

        kick_btn = Gtk.Button(label="Kick")
        kick_btn.connect("clicked", self._on_kick, client_id)
        row.pack_start(kick_btn, False, False, 0)

        return row

    def _on_permission(self, _switch, state, client_id, perm):
        self.Controller.set_permission(perm, client_id, state)
        return True

    def _on_kick(self, _btn, client_id):
        self.Controller.ws.send(json.dumps({"kick": client_id}))
        GLib.idle_add(self.Controller._disconnect, client_id)
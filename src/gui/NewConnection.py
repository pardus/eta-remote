import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from i18n import _
from Clients import get_os, get_browser, PERMISSION_LABELS

class NewConnection(Gtk.Dialog):
    def __init__(self, Controller, data):
        client_id = data.get("id")
        super().__init__(title=_("New Connection") + " - " + client_id)
        self.set_default_size(320, 300)
        self.set_resizable(False)
        self.set_modal(True)
        self.set_icon_name("tr.org.pardus.eta-remote")

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
            detail.append(_("Mobile"))
        if data.get("language"):
            detail.append(data["language"])
        detail_label = Gtk.Label(label=" · ".join(detail))
        detail_label.set_halign(Gtk.Align.START)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.pack_start(os_label, False, False, 0)
        info_box.pack_start(detail_label, False, False, 0)

        self.check_buttons = {}
        perm_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        perm_box.set_margin_top(8)
        for perm, label in PERMISSION_LABELS.items():
            check = Gtk.CheckButton(label=label)
            check.set_active(perm in ("input", "image"))
            self.check_buttons[perm] = check
            perm_box.pack_start(check, False, False, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.pack_start(info_box, False, False, 0)
        box.pack_start(Gtk.Separator(), False, False, 0)
        box.pack_start(perm_box, False, False, 0)

        self.get_content_area().add(box)

        self.add_button(_("Deny"), Gtk.ResponseType.REJECT)
        self.add_button(_("Allow"), Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.connect("response", self._on_response, Controller, client_id)

    def _on_response(self, _dialog, response, Controller, client_id):
        if response == Gtk.ResponseType.OK:
            for perm, check in self.check_buttons.items():
                if check.get_active():
                    Controller.set_permission(perm, client_id, True)
        elif response in (Gtk.ResponseType.REJECT, Gtk.ResponseType.DELETE_EVENT):
            Controller.kick_client(client_id)
        self.destroy()
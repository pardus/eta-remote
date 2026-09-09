#!/usr/bin/env python3
import sys

import gi

from MainWindow import MainWindow

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="tr.org.pardus.eta-remote",
                         flags=Gio.ApplicationFlags(8), **kwargs)
        self.window = None
        GLib.set_prgname("tr.org.pardus.eta-remote")

        self.add_main_option(
            "autostart",
            ord("a"),
            GLib.OptionFlags(0),
            GLib.OptionArg(0),
            "Start application on autostart",
            None,
        )

        self.add_main_option(
            "show",
            ord("s"),
            GLib.OptionFlags(0),
            GLib.OptionArg(0),
            "Start application and show window",
            None,
        )


    def do_activate(self):
        if not self.window:
            self.window = MainWindow(self)
        if "show" in self.args.keys():
            self.window.show_all()
            self.window.present()
        if "autostart" in self.args.keys():
            if not self.window.settings.get_boolean("autostart"):
                self.quit()
            else:
                self.window.on_start(self.window)

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()
        self.args = options
        self.activate()
        return 0


app = Application()
app.run(sys.argv)

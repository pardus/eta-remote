import time

from gi.repository import GLib, Gio

from screencast import (
    DBUS_IFACE, DBUS_PATH, PipeWireCaptureBase, ScreenCastUnavailableError)


MUTTER_NAME = "org.gnome.Mutter.ScreenCast"
MUTTER_PATH = "/org/gnome/Mutter/ScreenCast"
MUTTER_SESSION_IFACE = "org.gnome.Mutter.ScreenCast.Session"
MUTTER_STREAM_IFACE = "org.gnome.Mutter.ScreenCast.Stream"

DISPLAY_CONFIG_NAME = "org.gnome.Mutter.DisplayConfig"
DISPLAY_CONFIG_PATH = "/org/gnome/Mutter/DisplayConfig"
DISPLAY_CONFIG_IFACE = "org.gnome.Mutter.DisplayConfig"


class GnomeCapture(PipeWireCaptureBase):
    def __init__(self):
        super().__init__()
        self._mutter_session = None
        self._mutter_stream = None

    def _find_primary_connector(self):
        def first(value):
            if isinstance(value, (tuple, list)):
                return str(value[0]) if value else None
            return str(value)

        try:
            replied = self._dbus_call(
                DISPLAY_CONFIG_NAME, DISPLAY_CONFIG_PATH,
                DISPLAY_CONFIG_IFACE, "GetCurrentState")
            _, physical, logical, _ = replied
            for logical_monitor in logical:
                _, _, _, _, is_primary, monitors, _ = logical_monitor
                if is_primary and monitors:
                    return first(monitors[0])
        except GLib.Error:
            pass
        return None

    def _stop_mutter_session(self):
        if self._mutter_stream is not None:
            try:
                self._dbus_call(
                    MUTTER_NAME, self._mutter_stream, MUTTER_STREAM_IFACE,
                    "Stop", timeout=2000)
            except Exception:
                pass
        if self._mutter_session is not None:
            try:
                self._dbus_call(
                    MUTTER_NAME, self._mutter_session, MUTTER_SESSION_IFACE,
                    "Stop", timeout=2000)
            except Exception:
                pass

    def _open_stream(self):
        self._push_ctx()
        try:
            if self._connection is None:
                self._connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            if self._connection is None:
                raise ScreenCastUnavailableError("no session bus available")

            owned = self._dbus_call(
                DBUS_IFACE, DBUS_PATH, DBUS_IFACE, "NameHasOwner",
                GLib.Variant("(s)", (MUTTER_NAME,)))
            if not owned or not owned[0]:
                raise ScreenCastUnavailableError(
                    "GNOME screen cast is unavailable: "
                    f"{MUTTER_NAME} is not owned")

            created = self._dbus_call(
                MUTTER_NAME, MUTTER_PATH, "org.gnome.Mutter.ScreenCast",
                "CreateSession", GLib.Variant("(a{sv})", ({},)))
            self._mutter_session = str(created[0])

            opts = {
                "cursor-mode": GLib.Variant("u", 2),   # embedded cursor
                "is-recording": GLib.Variant("b", False),
            }
            connector = self._find_primary_connector()
            if connector is not None:
                stream = self._dbus_call(
                    MUTTER_NAME, self._mutter_session, MUTTER_SESSION_IFACE,
                    "RecordMonitor",
                    GLib.Variant("(sa{sv})", (connector, opts)))
            else:
                stream = self._dbus_call(
                    MUTTER_NAME, self._mutter_session, MUTTER_SESSION_IFACE,
                    "RecordVirtual", GLib.Variant("(a{sv})", (opts,)))
            self._mutter_stream = str(stream[0])

            node = {"id": -1}

            def on_pipewire_stream(conn, sender, path, iface, sig, p, udata):
                node["id"] = int(p[0])
                return None

            self._connection.signal_subscribe(
                MUTTER_NAME, MUTTER_STREAM_IFACE, "PipeWireStreamAdded",
                self._mutter_stream, None, Gio.DBusSignalFlags.NONE,
                on_pipewire_stream, None)

            self._dbus_call(
                MUTTER_NAME, self._mutter_session, MUTTER_SESSION_IFACE,
                "Start")

            deadline = time.monotonic() + 15
            while node["id"] < 0 and time.monotonic() < deadline:
                self._ctx.iteration(True)

            if node["id"] < 0:
                raise ScreenCastUnavailableError(
                    "Mutter did not provide a PipeWire node")

            return f"path={node['id']}"
        except (GLib.Error, RuntimeError) as e:
            self._stop_mutter_session()
            if isinstance(e, ScreenCastUnavailableError):
                raise
            raise ScreenCastUnavailableError(
                f"GNOME screen cast failed: {e}") from e
        finally:
            self._pop_ctx()

    def _close_session(self):
        self._stop_mutter_session()
        self._mutter_stream = None
        self._mutter_session = None


_capture = GnomeCapture()


def grab_rgb():
    return _capture.grab_rgb()


def wait_event():
    _capture.wait_event()


def display_close():
    _capture.display_close()
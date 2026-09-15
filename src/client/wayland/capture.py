import os
import threading
import time

from PIL import Image

from gi import require_version
require_version("Gst", "1.0")
require_version("GstApp", "1.0")
require_version("GLib", "2.0")
require_version("Gio", "2.0")
from gi.repository import GLib, Gio, Gst, GstApp


MUTTER_NAME = "org.gnome.Mutter.ScreenCast"
MUTTER_PATH = "/org/gnome/Mutter/ScreenCast"
MUTTER_SESSION_IFACE = "org.gnome.Mutter.ScreenCast.Session"
MUTTER_STREAM_IFACE = "org.gnome.Mutter.ScreenCast.Stream"

DISPLAY_CONFIG_NAME = "org.gnome.Mutter.DisplayConfig"
DISPLAY_CONFIG_PATH = "/org/gnome/Mutter/DisplayConfig"
DISPLAY_CONFIG_IFACE = "org.gnome.Mutter.DisplayConfig"

SCREEN_CAST_IFACE = "org.freedesktop.portal.ScreenCast"
SCREEN_CAST_PATH = "/org/freedesktop/portal/desktop"
PORTAL_NAME = "org.freedesktop.portal.Desktop"
REQUEST_IFACE = "org.freedesktop.portal.Request"
SESSION_IFACE = "org.freedesktop.portal.Session"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
DBUS_IFACE = "org.freedesktop.DBus"
DBUS_PATH = "/org/freedesktop/DBus"

_token_counter = 0
_gst_initialized = False


class ScreenCastUnavailableError(RuntimeError):
    pass


def _next_request(connection, ctx, method, params, extra_options=None):
    global _token_counter
    _token_counter += 1
    handle_token = f"eta_{_token_counter}"

    if method == "CreateSession":
        args = {"handle_token": GLib.Variant("s", handle_token)}
        if extra_options:
            args.update(extra_options)
        call = GLib.Variant("(a{sv})", (args,))
    elif method == "Start":
        call = GLib.Variant(
            "(ssa{sv})", (params, "", {"handle_token":
                                       GLib.Variant("s", handle_token)}))
    else:
        opts = {"handle_token": GLib.Variant("s", handle_token)}
        if extra_options:
            opts.update(extra_options)
        call = GLib.Variant("(oa{sv})", (params, opts))

    result = connection.call_sync(
        PORTAL_NAME, SCREEN_CAST_PATH, SCREEN_CAST_IFACE, method, call,
        None, Gio.DBusCallFlags.NONE, -1, None)

    request_path = str(result)

    state = {"response": None}

    def on_response(conn, sender, path, iface_name, signal_name, p,
                    user_data):
        state["response"] = p
        return None

    connection.signal_subscribe(
        None, REQUEST_IFACE, "Response", request_path, None,
        Gio.DBusSignalFlags.NONE, on_response, None)

    deadline = time.monotonic() + 120
    while state["response"] is None and time.monotonic() < deadline:
        ctx.iteration(True)

    if state["response"] is None:
        raise RuntimeError(f"Portal {method} timed out")

    code = state["response"][0]
    results = state["response"][1] if len(state["response"]) > 1 else {}
    return code, results


class WaylandCapture:
    def __init__(self, portal_timeout=10):
        self._portal_timeout = portal_timeout
        self._connection = None
        self._ctx = None
        self._backend = None
        self._session_handle = None
        self._mutter_session = None
        self._mutter_stream = None
        self._pipe = None
        self._sink = None
        self._reader = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest = None
        self._frame_event = threading.Event()
        self._known_size = (800, 600)
        self._fallback = None
        self._logged_fallback = False

    def _push_ctx(self):
        self._ctx = GLib.MainContext.new()
        GLib.MainContext.push_thread_default(self._ctx)

    def _pop_ctx(self):
        GLib.MainContext.pop_thread_default(self._ctx)

    def _dbus_call(self, destination, path, interface, method, params=None,
                   flags=Gio.DBusCallFlags.NONE, timeout=-1):
        if params is None:
            params = GLib.Variant("()", ())
        return self._connection.call_sync(
            destination, path, interface, method, params, None,
            flags, timeout, None)

    # ---------- GNOME / Mutter backend ----------

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

    def _open_mutter(self):
        self._push_ctx()
        try:
            self._connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            if self._connection is None:
                return None

            owned = self._dbus_call(
                DBUS_IFACE, DBUS_PATH, DBUS_IFACE, "NameHasOwner",
                GLib.Variant("(s)", (MUTTER_NAME,)))
            if not owned or not owned[0]:
                return None

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
                raise RuntimeError("Mutter did not provide a PipeWire node")

            self._backend = "mutter"
            return node["id"]
        except (GLib.Error, RuntimeError):
            self._stop_mutter_session()
            return None
        finally:
            self._pop_ctx()

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

    # ---------- xdg-desktop-portal backend ----------

    def _read_screencast_version(self):
        reply = self._connection.call_sync(
            PORTAL_NAME, SCREEN_CAST_PATH, PROPERTIES_IFACE, "Get",
            GLib.Variant("(ss)", (SCREEN_CAST_IFACE, "version")),
            GLib.VariantType("(v)"), Gio.DBusCallFlags.NONE, 1000, None)
        return int(reply[0].unpack())

    def _wait_for_screencast(self):
        deadline = time.monotonic() + self._portal_timeout
        while time.monotonic() < deadline:
            try:
                return self._read_screencast_version()
            except GLib.Error:
                time.sleep(0.5)
        return None

    def _open_portal(self):
        self._push_ctx()
        try:
            if self._connection is None:
                self._connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            if self._connection is None:
                return None

            version = self._wait_for_screencast()
            if version is None:
                return None

            code, results = _next_request(
                self._connection, self._ctx, "CreateSession", None,
                extra_options={"session_handle_token":
                               GLib.Variant("s", "eta_session")})
            if code != 0:
                return None
            self._session_handle = results.get("session_handle")
            if not self._session_handle:
                return None

            code, _ = _next_request(
                self._connection, self._ctx, "SelectSources",
                GLib.Variant("o", self._session_handle),
                extra_options={
                    "types": GLib.Variant("u", 1 | 2),
                    "multiple": GLib.Variant("b", False),
                })
            if code != 0:
                return None

            code, results = _next_request(
                self._connection, self._ctx, "Start",
                GLib.Variant("o", self._session_handle))
            if code != 0:
                return None

            streams = results.get("streams", [])
            if not streams:
                return None

            node_id = int(streams[0][0])
            props = streams[0][1] if len(streams[0]) > 1 else {}
            serial = str(props.get("pipewire-serial") or "").strip()

            pw_fd = -1
            if version >= 6:
                try:
                    fd_result, out_fd_list = (
                        self._connection.call_with_unix_fd_list_sync(
                            PORTAL_NAME, SCREEN_CAST_PATH, SCREEN_CAST_IFACE,
                            "OpenPipeWireRemote",
                            GLib.Variant(
                                "(oa{sv})",
                                (GLib.Variant("o", self._session_handle), {})),
                            None, Gio.DBusCallFlags.NONE, -1, None, None))
                    if out_fd_list is not None and out_fd_list.get_size() >= 1:
                        fds = out_fd_list.steal_fds()
                        pw_fd = fds[int(fd_result[0])]
                except GLib.Error:
                    pw_fd = -1

            if pw_fd < 0:
                legacy_fds = results.get("fds")
                if legacy_fds:
                    pw_fd = int(legacy_fds[0])

            if pw_fd < 0:
                return None

            self._backend = "portal"
            return {"node_id": node_id, "serial": serial, "pw_fd": pw_fd}
        finally:
            self._pop_ctx()

    # ---------- GStreamer ----------

    def _init_stream(self):
        global _gst_initialized
        if not _gst_initialized:
            Gst.init(None)
            _gst_initialized = True

        node = self._open_mutter()
        target = f"path={node}"
        if node is None:
            result = self._open_portal()
            if result is None:
                raise ScreenCastUnavailableError(
                    "Neither Mutter nor the ScreenCast portal is available")
            node = result["node_id"]
            if result["serial"]:
                target = f"fd={result['pw_fd']} target-object={result['serial']}"
            else:
                target = f"fd={result['pw_fd']} path={node}"

        desc = (
            f"pipewiresrc {target} "
            "! videoconvert ! video/x-raw,format=RGB "
            "! appsink name=eta_sink max-buffers=2 drop=true sync=false"
        )
        pipe = Gst.parse_launch(desc)
        self._pipe = pipe
        self._sink = pipe.get_by_name("eta_sink")

        pipe.set_state(Gst.State.PLAYING)

    def _read_loop(self):
        while not self._stop.is_set():
            sample = self._sink.try_pull_sample(int(0.5 * Gst.SECOND))
            if sample is None:
                continue

            buffer = sample.get_buffer()
            ok, info = buffer.map(Gst.MapFlags.READ)
            if not ok:
                continue
            frame = bytes(info.data)
            buffer.unmap(info)

            caps = sample.get_caps()
            structure = caps.get_structure(0) if caps else None
            width = height = 0
            if structure is not None:
                ok_w, width = structure.get_int("width")
                ok_h, height = structure.get_int("height")
                if not ok_w or not ok_h:
                    width, height = 0, 0
            if width == 0 or height == 0:
                continue

            self._known_size = (width, height)
            with self._lock:
                self._latest = (width, height, frame)
            self._frame_event.set()

    # ---------- contract ----------

    def _setup_fallback(self):
        if not self._logged_fallback:
            print("eta wayland capture: PipeWire unavailable, "
                  "using alternate capture backend")
            self._logged_fallback = True

        if "DISPLAY" in os.environ:
            try:
                from X11.capture import grab_rgb, wait_event, display_close
            except Exception:
                from pillow.capture import grab_rgb, wait_event, display_close
        else:
            from pillow.capture import grab_rgb, wait_event, display_close

        self._fallback = (grab_rgb, wait_event, display_close)

    def _ensure_running(self):
        if self._fallback is not None:
            return

        if self._pipe is None:
            try:
                self._stop.clear()
                self._latest = None
                self._frame_event.clear()
                self._init_stream()
            except Exception as e:
                print(f"eta wayland capture: PipeWire via native screen "
                      f"capture failed: {e}")
                self._setup_fallback()
                return

        if self._reader is None or not self._reader.is_alive():
            self._reader = threading.Thread(
                target=self._read_loop, daemon=True)
            self._reader.start()

    def _black(self):
        return Image.new("RGB", self._known_size, color="black")

    def grab_rgb(self):
        try:
            self._ensure_running()
        except Exception as e:
            print(f"eta wayland capture: init failed: {e}")
            return self._black()

        if self._fallback is not None:
            try:
                img = self._fallback[0]()
                self._known_size = img.size
                return img
            except Exception:
                return self._black()

        with self._lock:
            latest = self._latest
        if latest is None:
            return self._black()

        self._frame_event.clear()
        width, height, frame = latest
        self._known_size = (width, height)
        return Image.frombytes("RGB", (width, height), frame)

    def _current_size(self):
        return self._known_size

    def wait_event(self):
        if self._fallback is not None:
            try:
                self._fallback[1]()
            except Exception:
                time.sleep(0.02)
            return
        if self._pipe is None:
            return
        self._frame_event.wait()

    def _close_session(self):
        if self._backend == "mutter" and self._mutter_session is not None:
            self._stop_mutter_session()
            self._mutter_stream = None
            self._mutter_session = None
        elif self._backend == "portal" and self._session_handle is not None:
            try:
                self._dbus_call(
                    PORTAL_NAME, self._session_handle, SESSION_IFACE, "Close",
                    timeout=2000)
            except Exception:
                pass
            self._session_handle = None

    def display_close(self):
        if self._fallback is not None:
            try:
                self._fallback[2]()
            except Exception:
                pass
            self._fallback = None
            return

        self._stop.set()
        if self._pipe is not None:
            self._pipe.set_state(Gst.State.NULL)
            self._pipe = None
            self._sink = None
        self._close_session()
        if self._connection is not None:
            try:
                self._connection.close_sync(None)
            except Exception:
                pass
            self._connection = None


_capture = WaylandCapture()


def grab_rgb():
    return _capture.grab_rgb()


def wait_event():
    _capture.wait_event()


def display_close():
    _capture.display_close()
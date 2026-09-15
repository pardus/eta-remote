import threading
import time

from PIL import Image

from gi import require_version
require_version("Gst", "1.0")
require_version("GstApp", "1.0")
require_version("GLib", "2.0")
require_version("Gio", "2.0")
from gi.repository import GLib, Gio, Gst, GstApp


DBUS_IFACE = "org.freedesktop.DBus"
DBUS_PATH = "/org/freedesktop/DBus"

_gst_initialized = False


class ScreenCastUnavailableError(RuntimeError):
    pass


class PipeWireCaptureBase:
    def __init__(self, portal_timeout=10):
        self._portal_timeout = portal_timeout
        self._connection = None
        self._ctx = None
        self._pipe = None
        self._sink = None
        self._reader = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._latest = None
        self._frame_event = threading.Event()
        self._known_size = (800, 600)

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

    # ---------- backend contract ----------

    def _open_stream(self):
        raise NotImplementedError("backend must implement _open_stream()")

    def _close_session(self):
        pass

    # ---------- GStreamer ----------

    def _init_stream(self):
        global _gst_initialized
        if not _gst_initialized:
            Gst.init(None)
            _gst_initialized = True

        target = self._open_stream()
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

    def _ensure_running(self):
        if self._pipe is None:
            self._stop.clear()
            self._latest = None
            self._frame_event.clear()
            self._init_stream()
        if self._reader is None or not self._reader.is_alive():
            self._reader = threading.Thread(
                target=self._read_loop, daemon=True)
            self._reader.start()

    # ---------- contract ----------

    def _black(self):
        return Image.new("RGB", self._known_size, color="black")

    def grab_rgb(self):
        self._ensure_running()
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
        if self._pipe is None:
            return
        self._frame_event.wait()

    def display_close(self):
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
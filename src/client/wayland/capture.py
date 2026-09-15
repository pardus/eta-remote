import time

from gi.repository import GLib, Gio

from screencast import (
    PipeWireCaptureBase, ScreenCastUnavailableError)


SCREEN_CAST_IFACE = "org.freedesktop.portal.ScreenCast"
SCREEN_CAST_PATH = "/org/freedesktop/portal/desktop"
PORTAL_NAME = "org.freedesktop.portal.Desktop"
REQUEST_IFACE = "org.freedesktop.portal.Request"
SESSION_IFACE = "org.freedesktop.portal.Session"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"

_token_counter = 0


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
            "(osa{sv})", (params, "", {"handle_token":
                                       GLib.Variant("s", handle_token)}))
    else:
        opts = {"handle_token": GLib.Variant("s", handle_token)}
        if extra_options:
            opts.update(extra_options)
        call = GLib.Variant("(oa{sv})", (params, opts))

    result = connection.call_sync(
        PORTAL_NAME, SCREEN_CAST_PATH, SCREEN_CAST_IFACE, method, call,
        None, Gio.DBusCallFlags.NONE, -1, None)

    request_path = result.unpack()
    if isinstance(request_path, (tuple, list)):
        request_path = request_path[0]

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


class PortalCapture(PipeWireCaptureBase):
    def __init__(self):
        super().__init__()
        self._session_handle = None

    def _read_screencast_version(self):
        reply = self._connection.call_sync(
            PORTAL_NAME, SCREEN_CAST_PATH, PROPERTIES_IFACE, "Get",
            GLib.Variant("(ss)", (SCREEN_CAST_IFACE, "version")),
            GLib.VariantType("(v)"), Gio.DBusCallFlags.NONE, 1000, None)
        value = reply[0]
        if hasattr(value, "unpack"):
            value = value.unpack()
        if isinstance(value, tuple):
            value = value[0] if value else 0
        return int(value)

    def _wait_for_screencast(self):
        deadline = time.monotonic() + self._portal_timeout
        while time.monotonic() < deadline:
            try:
                return self._read_screencast_version()
            except GLib.Error:
                time.sleep(0.5)
        return None

    def _open_stream(self):
        self._push_ctx()
        try:
            if self._connection is None:
                self._connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            if self._connection is None:
                raise ScreenCastUnavailableError("no session bus available")

            version = self._wait_for_screencast()
            if version is None:
                raise ScreenCastUnavailableError(
                    "ScreenCast portal is not available")
            print(f"eta wayland capture: ScreenCast portal version {version}")

            code, results = _next_request(
                self._connection, self._ctx, "CreateSession", None,
                extra_options={"session_handle_token":
                               GLib.Variant("s", "eta_session")})
            if code != 0:
                raise ScreenCastUnavailableError(
                    f"CreateSession rejected (code {code})")
            self._session_handle = results.get("session_handle")
            if not self._session_handle:
                raise ScreenCastUnavailableError(
                    "CreateSession returned no session_handle")

            code, _ = _next_request(
                self._connection, self._ctx, "SelectSources",
                self._session_handle,
                extra_options={
                    "types": GLib.Variant("u", 1 | 2),
                    "multiple": GLib.Variant("b", False),
                })
            if code != 0:
                raise ScreenCastUnavailableError(
                    f"SelectSources rejected (code {code})")

            code, results = _next_request(
                self._connection, self._ctx, "Start",
                self._session_handle)
            if code != 0:
                raise ScreenCastUnavailableError(
                    f"Start rejected (code {code})")

            streams = results.get("streams", [])
            if not streams:
                raise ScreenCastUnavailableError(
                    "Start returned no streams")

            node_id = int(streams[0][0])
            props = streams[0][2] if len(streams[0]) > 2 else {}
            serial = str(props.get("pipewire-serial") or "").strip()

            pw_fd = -1
            try:
                fd_result, out_fd_list = (
                    self._connection.call_with_unix_fd_list_sync(
                        PORTAL_NAME, SCREEN_CAST_PATH, SCREEN_CAST_IFACE,
                        "OpenPipeWireRemote",
                        GLib.Variant(
                            "(oa{sv})",
                            (self._session_handle, {})),
                        None, Gio.DBusCallFlags.NONE, -1, None, None))
                if out_fd_list is not None:
                    fds = out_fd_list.steal_fds()
                    value = fd_result
                    if hasattr(value, "unpack"):
                        value = value.unpack()
                    if isinstance(value, (tuple, list)):
                        value = value[0]
                    pw_fd = fds[int(value)]
            except (GLib.Error, IndexError, ValueError) as e:
                pw_fd = -1
                print(f"eta wayland capture: OpenPipeWireRemote "
                      f"failed: {e}")

            if pw_fd < 0:
                legacy_fds = results.get("fds")
                if legacy_fds:
                    pw_fd = int(legacy_fds[0])

            if pw_fd < 0:
                raise ScreenCastUnavailableError(
                    "no PipeWire fd obtained")

            if serial:
                return f"fd={pw_fd} target-object={serial}"
            return f"fd={pw_fd} path={node_id}"
        finally:
            self._pop_ctx()

    def _close_session(self):
        if self._session_handle is not None:
            try:
                self._dbus_call(
                    PORTAL_NAME, self._session_handle, SESSION_IFACE, "Close",
                    timeout=2000)
            except Exception:
                pass
            self._session_handle = None


_capture = PortalCapture()


def grab_rgb():
    return _capture.grab_rgb()


def wait_event():
    _capture.wait_event()


def display_close():
    _capture.display_close()
import gi

from gi.repository import GLib

import os
import threading
import traceback

Downloads = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
if not Downloads:
    Downloads = os.path.expanduser("~/Downloads")
open_files = {}
files_lock = threading.Lock()


def safe_path(name):
    parts = []
    for part in name.replace("\\", "/").split("/"):
        if part in ("", ".", ".."):
            continue
        parts.append(part)
    if not parts:
        return None
    return os.path.join(Downloads, *parts)


def handle_file(data, on_complete=None):
    name = data.get("name")
    chunk = data.get("chunk", 0)
    total_chunks = data.get("totalChunks", 1)
    file_data = data.get("data", b"")
    complete = False

    path = safe_path(name)
    if path is None:
        if on_complete:
            on_complete(name, chunk, False)
        return

    try:
        with files_lock:
            if chunk == 0:
                parent = os.path.dirname(path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                open_files[name] = open(path, "wb")
            open_files[name].write(file_data)
            if chunk + 1 == total_chunks:
                open_files[name].close()
                del open_files[name]
                complete = True
    except:
        print(traceback.format_exc())
        with files_lock:
            if name in open_files:
                try:
                    open_files[name].close()
                except:
                    pass
                del open_files[name]

    if on_complete:
        on_complete(name, chunk, complete)
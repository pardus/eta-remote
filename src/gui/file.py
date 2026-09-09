import gi

from gi.repository import GLib

import base64 as b64

Downloads = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
open_files = {}

def handle_file(data):
    name = data.get("name")
    chunk = data.get("chunk", 0)
    total_chunks = data.get("totalChunks", 1)
    file_data = b64.b64decode(data.get("data", ""))

    path = f"{Downloads}/{name}"

    if chunk == 0:
        open_files[name] = open(path, "wb")

    open_files[name].write(file_data)

    if chunk + 1 == total_chunks:
        open_files[name].close()
        del open_files[name]
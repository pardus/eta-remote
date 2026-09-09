import gi

from gi.repository import GLib

import base64 as b64

file_chunks = {}

def handle_file(data):
    global file_chunks
    name = data.get("name")
    chunk = data.get("chunk", 0)
    total_chunks = data.get("totalChunks", 1)
    file_data = b64.b64decode(data.get("data", ""))

    if name not in file_chunks:
        file_chunks[name] = bytearray()
    file_chunks[name].extend(file_data)

    if chunk + 1 == total_chunks:
        downloads = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        with open(f"{downloads}/{name}", "wb") as f:
            f.write(file_chunks[name])
        del file_chunks[name]

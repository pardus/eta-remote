import os
import time
import traceback
from collections import namedtuple
from io import BytesIO

from PIL import Image, ImageChops

from protocol import pack_image


Patch = namedtuple(
    "Patch",
    "x y width height screen_width screen_height jpeg"
)


def _mutter_running():
    try:
        from gi.repository import GLib, Gio
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        if connection is None:
            return False
        result = connection.call_sync(
            "org.freedesktop.DBus", "/org/freedesktop/DBus",
            "org.freedesktop.DBus", "NameHasOwner",
            GLib.Variant("(s)", ("org.gnome.Mutter.ScreenCast",)),
            None, Gio.DBusCallFlags.NONE, -1, None)
        return bool(result.unpack()[0])
    except Exception:
        return False


if "DISPLAY" in os.environ and "WAYLAND_DISPLAY" not in os.environ:
    from X11.capture import grab_rgb, display_close, wait_event
elif "WAYLAND_DISPLAY" in os.environ:
    if _mutter_running():
        from gnome.capture import grab_rgb, display_close, wait_event
    else:
        from wayland.capture import grab_rgb, display_close, wait_event
else:
    from pillow.capture import grab_rgb, display_close, wait_event

SPEED = 60

img_width = 0
img_height = 0


def image_diff_patch(previous, current):
    """Return a Patch describing the changed region and its JPEG data, or None."""
    if previous.size != current.size:
        raise ValueError("Images must have the same dimensions")

    difference = ImageChops.difference(previous, current)
    bounding_box = difference.getbbox()

    if bounding_box is None:
        return None

    x1, y1, x2, y2 = bounding_box
    patch = current.crop(bounding_box)

    scale = img_width / 1920
    if int(scale) <= 1:
        scale = 1
    else:
        new_w = int(patch.width / scale)
        new_h = int(patch.height / scale)
        if new_w > 0 and new_h > 0:
            patch = patch.resize(
                (new_w, new_h),
                resample=Image.Resampling.NEAREST,
                reducing_gap=2.0
            )
        else:
            return None

    img_size = img_width * img_height
    patch_size = patch.width * patch.height
    ratio = 0.8
    if img_size > 0:
        ratio = 1.0 - (patch_size / img_size)
    if ratio > 0.8:
        ratio = 0.8
    elif ratio < 0.2:
        ratio = 0.2

    buffer = BytesIO()

    patch.save(
        buffer,
        format="JPEG",
        optimize=True,
        quality=int(ratio * 100),
    )

    return Patch(
        x1 / scale,
        y1 / scale,
        patch.width,
        patch.height,
        img_width / scale,
        img_height / scale,
        buffer.getvalue(),
    )


req_full = False


def request_full():
    global req_full
    req_full = True


def _should_stop(stop_event):
    return stop_event is not None and stop_event.is_set()


def main(handler=None, stop_event=None):
    global req_full
    global img_width
    global img_height

    while True:
        try:
            previous_image = grab_rgb()
            break
        except KeyboardInterrupt:
            print("\nStopped.")
            display_close()
            return
        except:
            if _should_stop(stop_event):
                display_close()
                return
            print(traceback.format_exc())
            display_close()
            time.sleep(3)

    img_width = previous_image.width
    img_height = previous_image.height

    while not _should_stop(stop_event):
        try:
            cur = time.time()
            current_image = grab_rgb()
            if req_full:
                previous_image = Image.new('RGB', (img_width, img_height), color='black')
                req_full = False

            if current_image.size != (img_width, img_height):
                img_width = current_image.width
                img_height = current_image.height
                previous_image = Image.new('RGB', (img_width, img_height), color='black')

            patch = image_diff_patch(previous_image, current_image)

            if patch is not None and handler:
                handler(pack_image(*patch))

            previous_image = current_image

            delay = len(patch.jpeg) / (921600 * SPEED) if patch else 0
            wait_event()
            now = time.time()
            if now - cur < delay:
                time.sleep(delay - (cur - now))

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except:
            if _should_stop(stop_event):
                break
            print(traceback.format_exc())
            display_close()
            time.sleep(3)

    display_close()


if __name__ == "__main__":
    main(print)
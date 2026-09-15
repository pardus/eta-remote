import os
import base64
import json
import time
import traceback
from io import BytesIO

from PIL import Image, ImageChops, ImageGrab


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
QUALITY = 70

img_width = 0
img_height = 0

def image_diff_patch_json(previous, current):

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
        new_w = int(patch.width/scale)
        new_h = int(patch.height/scale)
        if new_w > 0 and new_h > 0:
            patch = patch.resize(
                (new_w, new_h),
                resample=Image.Resampling.NEAREST,
                reducing_gap=2.0
            )
        else:
            return None


    buffer = BytesIO()

    patch.save(
        buffer,
        format="JPEG",
        optimize=True,
        quality=QUALITY,
    )

    encoded_pixels = base64.b64encode(
        buffer.getvalue()
    ).decode("ascii")

    result = {
        "type": "image",
        "x": x1/scale,
        "y": y1/scale,
        "width": patch.width,
        "height": patch.height,
        "screen_width": img_width/scale,
        "screen_height": img_height/scale,
        "pixels": encoded_pixels,
    }

    return json.dumps(
        result,
        separators=(",", ":"),
    )



req_full = False
def request_full():
    global req_full
    req_full = True

def set_quality(quality):
    global QUALITY
    q = int(quality)
    if q > 80:
        q = 80
    if q < 10:
        q = 10
    QUALITY = q
    request_full()

def main(handler=None):
    global req_full
    global img_width
    global img_height
    previous_image = grab_rgb()
    img_width = previous_image.width
    img_height = previous_image.height

    while True:
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

            patch_json = image_diff_patch_json(
                previous_image,
                current_image,
            )

            if patch_json != None:
                if handler:
                    handler(patch_json)

            previous_image = current_image

            delay = len(str(patch_json)) / (921600*SPEED)
            wait_event()
            now = time.time()
            if now - cur < delay:
                time.sleep(delay - (cur - now))

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except:
            print(traceback.format_exc())
            display_close()
            time.sleep(3)

    display_close()



if __name__ == "__main__":
    main(print)

import os
import base64
import json
import time
import traceback
from io import BytesIO

from PIL import Image, ImageChops, ImageGrab

if "DISPLAY" in os.environ and "WAYLAND_DISPLAY" not in os.environ:
    from X11.capture import grab_rgb, display_close
else:
    def grab_rgb():
        ImageGrab.grab()

    def display_close():
        pass

SPEED = 60

img_width = 0
img_height = 0

def image_diff_patch_json(previous, current):

    if previous.size != current.size:
        raise ValueError("Images must have the same dimensions")

    difference = ImageChops.difference(previous, current)
    bounding_box = difference.getbbox()

    if bounding_box is None:
        return "null"

    x1, y1, x2, y2 = bounding_box
    patch = current.crop(bounding_box)

    buffer = BytesIO()

    patch.save(
        buffer,
        format="JPEG",
        optimize=True,
        quality=80,
    )

    encoded_pixels = base64.b64encode(
        buffer.getvalue()
    ).decode("ascii")

    result = {
        "x": x1,
        "y": y1,
        "width": patch.width,
        "height": patch.height,
        "screen_width": img_width,
        "screen_height": img_height,
        "format": "JPEG",
        "pixels": encoded_pixels,
    }

    return json.dumps(
        result,
        separators=(",", ":"),
    )


def image_grab():
    img = grab_rgb()
    if img.width > 1920:
        return img.resize((1920, 1080), resample=Image.Resampling.NEAREST, reducing_gap=2.0)
    return img

req_full = False
def request_full():
    global req_full
    req_full = True

def main(handler=None):
    global req_full
    global img_width
    global img_height
    previous_image = image_grab()
    img_width = previous_image.width
    img_height = previous_image.height

    try:
        while True:
            current_image = image_grab()
            if req_full:
                previous_image = Image.new('RGB', (img_width, img_height), color='black')
                req_full = False

            patch_json = image_diff_patch_json(
                previous_image,
                current_image,
            )

            if patch_json != "null":
                if handler:
                    handler(patch_json)

            previous_image = current_image

            time.sleep(len(patch_json) / (921600*SPEED))

    except KeyboardInterrupt:
        print("\nStopped.")
    except:
        print(traceback.format_exc())

    finally:
        display_close()


if __name__ == "__main__":
    main(print)

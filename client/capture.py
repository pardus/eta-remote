import base64
import json
import time
from io import BytesIO

from PIL import Image, ImageChops
from Xlib import X, display


display_connection = display.Display()
root = display_connection.screen().root

screen_geometry = root.get_geometry()
SCREEN_WIDTH = screen_geometry.width
SCREEN_HEIGHT = screen_geometry.height


def capture_screen():
    print("Capture")
    raw = root.get_image(
        0,
        0,
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        X.ZPixmap,
        0xFFFFFFFF,
    )

    return Image.frombytes(
        "RGB",
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        raw.data,
        "raw",
        "BGRX",
    )


def image_diff_patch_json(previous, current):
    previous = previous.convert("RGB")
    current = current.convert("RGB")

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
    )

    encoded_pixels = base64.b64encode(
        buffer.getvalue()
    ).decode("ascii")

    result = {
        "x": x1,
        "y": y1,
        "width": patch.width,
        "height": patch.height,
        "screen_width": SCREEN_WIDTH,
        "screen_height": SCREEN_HEIGHT,
        "format": "JPEG",
        "pixels": encoded_pixels,
    }

    return json.dumps(
        result,
        separators=(",", ":"),
    )


def main(handler=None):
    previous_image = capture_screen()

    try:
        while True:
            current_image = capture_screen()

            patch_json = image_diff_patch_json(
                previous_image,
                current_image,
            )

            if patch_json != "null":
                if handler:
                    handler(patch_json)

            previous_image = current_image

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nStopped.")

    finally:
        display_connection.close()


if __name__ == "__main__":
    main(print)

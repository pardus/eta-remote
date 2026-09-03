import base64
import json
import time
from io import BytesIO

from PIL import Image, ImageChops, ImageGrab

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


def main(handler=None):
    global img_width
    global img_height
    previous_image = ImageGrab.grab().resize((1280, 720))
    img_width = previous_image.width
    img_height = previous_image.height

    try:
        while True:
            current_image = ImageGrab.grab().resize((1280, 720))

            patch_json = image_diff_patch_json(
                previous_image,
                current_image,
            )

            if patch_json != "null":
                if handler:
                    handler(patch_json)

            previous_image = current_image

            time.sleep(len(patch_json) / 1000000)

    except KeyboardInterrupt:
        print("\nStopped.")

    finally:
        display_connection.close()


if __name__ == "__main__":
    main(print)

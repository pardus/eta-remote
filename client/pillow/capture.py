import time

from PIL import ImageChops, ImageGrab

def grab_rgb():
    ImageGrab.grab()

def diff_bbox(previous, current, coords=None):
    bounding_box = ImageChops.difference(previous, current).getbbox()
    if bounding_box is None:
        return None
    return bounding_box

def wait_damage(timeout_ms=0):
    time.sleep(1 / 60)
    return False

def display_close():
    pass
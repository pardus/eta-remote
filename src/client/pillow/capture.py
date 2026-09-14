import time

from PIL import ImageGrab, Image

def grab_rgb():
    try:
        return ImageGrab.grab().copy()
    except:
        return Image.new('RGB', (800, 600), color='black')

def wait_event():
    pass

def display_close():
    pass

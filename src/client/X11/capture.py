import ctypes
import os

from Xlib import display, X
from Xlib.ext import damage

from PIL import Image

# Load the shared library
_lib_path = os.path.join(os.path.dirname(__file__), "libcapture.so")
if not os.path.isfile(_lib_path):
    # from source
    _lib_path = os.path.join(os.getcwd(), "build", "libcapture.so")
_lib = ctypes.CDLL(_lib_path)

# X11 types
class Display(ctypes.Structure):
    pass

class XImage(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("xoffset", ctypes.c_int),
        ("format", ctypes.c_int),
        ("data", ctypes.c_char_p),
    ]

class XShmSegmentInfo(ctypes.Structure):
    _fields_ = [
        ("shmid", ctypes.c_ulong),
        ("shmaddr", ctypes.c_char_p),
        ("readOnly", ctypes.c_int),
        ("_pad", ctypes.c_byte * 12),
    ]

class ShmImage(ctypes.Structure):
    _fields_ = [
        ("shminfo", XShmSegmentInfo),
        ("ximage", ctypes.POINTER(XImage)),
        ("data", ctypes.POINTER(ctypes.c_uint)),
    ]

_display_p = ctypes.POINTER(Display)

# Bind C functions
_lib.opendisplay.argtypes = []
_lib.opendisplay.restype = ctypes.c_void_p

_lib.closedisplay.argtypes = [_display_p]
_lib.closedisplay.restype = None

_lib.screensize.argtypes = [_display_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
_lib.screensize.restype = None

_lib.initimage.argtypes = [ctypes.POINTER(ShmImage)]
_lib.initimage.restype = None

_lib.destroyimage.argtypes = [_display_p, ctypes.POINTER(ShmImage)]
_lib.destroyimage.restype = None

_lib.createimage.argtypes = [
    _display_p,
    ctypes.POINTER(ShmImage),
    ctypes.c_int,
    ctypes.c_int,
]
_lib.createimage.restype = ctypes.c_int

_lib.getrootwindow.argtypes = [_display_p, ctypes.POINTER(ShmImage)]
_lib.getrootwindow.restype = None

_display = None # from Ctypes
_image = None
_d = None # from XLib

def grab_rgb():
    global _display
    global _image

    if _display is None:
        _display = ctypes.cast(_lib.opendisplay(), _display_p)
        if not _display:
            raise RuntimeError("XOpenDisplay failed")

        width = ctypes.c_int()
        height = ctypes.c_int()
        _lib.screensize(_display, ctypes.byref(width), ctypes.byref(height))

        _image = ShmImage()
        _lib.initimage(ctypes.byref(_image))
        if not _lib.createimage(
            _display,
            ctypes.byref(_image),
            width.value,
            height.value,
        ):
            raise RuntimeError("createimage failed")

    _lib.getrootwindow(_display, ctypes.byref(_image))
    buf = ctypes.string_at(
        _image.data,
        _image.ximage.contents.width * _image.ximage.contents.height * 4,
    )
    img = Image.frombytes(
        "RGB",
        (_image.ximage.contents.width, _image.ximage.contents.height),
        buf,
        "raw",
        "BGRX",
    )
    return img

def display_close():
    global _display
    global _image
    global _d
    if _display is not None and _image is not None:
        _lib.destroyimage(_display, ctypes.byref(_image))
        _lib.closedisplay(_display)
        _image = None
        _display = None
    if _d is not None:
        _d.close()
        _d = None


def _xdamage_init():
    global _d
    if _d is not None:
        return
    _d = display.Display()
    root = _d.screen().root

    _d.damage_query_version()

    root.damage_create(damage.DamageReportRawRectangles)

def wait_event():
    _xdamage_init()
    while True:
        event = _d.next_event()
        if event.type == _d.extension_event.DamageNotify:
            return event

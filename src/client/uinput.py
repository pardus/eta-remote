#!/usr/bin/env python
import json
import time
import os
import sys
import traceback
from evdev import UInput, AbsInfo
from evdev import ecodes as E

sys.path.insert(0, os.path.dirname(__file__))

from touchpad import touchpad

SCREEN_WIDTH = int(os.environ.get("REMOTE_SCREEN_WIDTH", 3840))
SCREEN_HEIGHT = int(os.environ.get("REMOTE_SCREEN_HEIGHT", 2160))
MAX_TOUCHES = int(os.environ.get("REMOTE_MAX_TOUCHES", 11))
TRACKING_ID_MAX = 0xFFFF
PRESSURE_MAX = 1023

RESOLUTION_X = int(os.environ.get("REMOTE_SCREEN_RESOLUTION_X", 10))
RESOLUTION_Y = int(os.environ.get("REMOTE_SCREEN_RESOLUTION_Y", 10))

# linux/input-event-codes.h MT_TOOL_* values for ABS_MT_TOOL_TYPE
MT_TOOL_FINGER = 0

NO_FUZZ = 0
NO_FLAT = 0
NO_RESOLUTION = 0

PRESSURE_INFO = AbsInfo(0, 0, PRESSURE_MAX, NO_FUZZ, NO_FLAT, NO_RESOLUTION)
TOOL_INFO = AbsInfo(0, MT_TOOL_FINGER, MT_TOOL_FINGER, NO_FUZZ, NO_FLAT, NO_RESOLUTION)
DISTANCE_INFO = AbsInfo(0, 0, 255, NO_FUZZ, NO_FLAT, NO_RESOLUTION)

KEYS = {}

for i in range(10):
    KEYS[str(i)] = getattr(E, f"KEY_{i}")

for c in "abcdefghijklmnopqrstuvwxyz":
    KEYS[c] = getattr(E, f"KEY_{c.upper()}")

MODIFIERS = {
    "ShiftLeft": E.KEY_LEFTSHIFT,
    "ControlLeft": E.KEY_LEFTCTRL,
    "AltLeft": E.KEY_LEFTALT,
    "MetaLeft": E.KEY_LEFTMETA,
    "CapsLock": E.KEY_CAPSLOCK,
    "AltRight": E.KEY_RIGHTALT,
}

NAVIGATION = {
    "Enter": E.KEY_ENTER,
    "Backspace": E.KEY_BACKSPACE,
    "Tab": E.KEY_TAB,
    "Escape": E.KEY_ESC,
    "Space": E.KEY_SPACE,
    "Delete": E.KEY_DELETE,
    "ArrowUp": E.KEY_UP,
    "ArrowDown": E.KEY_DOWN,
    "ArrowLeft": E.KEY_LEFT,
    "ArrowRight": E.KEY_RIGHT,
    "Home": E.KEY_HOME,
    "End": E.KEY_END,
    "PageUp": E.KEY_PAGEUP,
    "PageDown": E.KEY_PAGEDOWN,
    "PrintScreen": E.KEY_SYSRQ,
}

FUNCTION_KEYS = {
    f"F{i}": getattr(E, f"KEY_F{i}")
    for i in range(1, 13)
}

PUNCTUATION = {
    "Minus": E.KEY_MINUS,
    "Equal": E.KEY_EQUAL,
    "BracketLeft": E.KEY_LEFTBRACE,
    "BracketRight": E.KEY_RIGHTBRACE,
    "Backslash": E.KEY_BACKSLASH,
    "Backquote": E.KEY_GRAVE,
    "Semicolon": E.KEY_SEMICOLON,
    "Quote": E.KEY_APOSTROPHE,
    "Comma": E.KEY_COMMA,
    "Period": E.KEY_DOT,
    "Slash": E.KEY_SLASH,
}

KEYS.update(MODIFIERS)
KEYS.update(NAVIGATION)
KEYS.update(FUNCTION_KEYS)
KEYS.update(PUNCTUATION)

MOUSE_BUTTONS = [
    E.BTN_LEFT,
    E.BTN_MIDDLE,
    E.BTN_RIGHT,
]

ABS_TOOL = {E.ABS_MT_TOOL_TYPE}
ABS_PRESSURE = {E.ABS_MT_PRESSURE, E.ABS_PRESSURE}
ABS_DISTANCE = {E.ABS_MT_DISTANCE}


def _axis_info(axis):
    if axis == E.ABS_X or axis == E.ABS_MT_POSITION_X:
        return AbsInfo(0, 0, SCREEN_DIMENSIONS[axis], NO_FUZZ, NO_FLAT,
                       RESOLUTION_X)
    if axis == E.ABS_Y or axis == E.ABS_MT_POSITION_Y:
        return AbsInfo(0, 0, SCREEN_DIMENSIONS[axis], NO_FUZZ, NO_FLAT,
                       RESOLUTION_Y)
    if axis in ABS_TOOL:
        return TOOL_INFO
    if axis in ABS_PRESSURE:
        return PRESSURE_INFO
    if axis in ABS_DISTANCE:
        return DISTANCE_INFO
    if axis == E.ABS_MT_SLOT:
        return AbsInfo(0, 0, MAX_TOUCHES - 1, NO_FUZZ, NO_FLAT, NO_RESOLUTION)
    if axis == E.ABS_MT_TRACKING_ID:
        return AbsInfo(0, 0, TRACKING_ID_MAX, NO_FUZZ, NO_FLAT, NO_RESOLUTION)
    raise ValueError(f"unknown axis {axis}")


SCREEN_DIMENSIONS = {
    E.ABS_X: SCREEN_WIDTH,
    E.ABS_Y: SCREEN_HEIGHT,
    E.ABS_MT_POSITION_X: SCREEN_WIDTH,
    E.ABS_MT_POSITION_Y: SCREEN_HEIGHT,
}


def _create_device(name, capabilities, props=()):
    events = {}
    for etype, code in capabilities:
        events.setdefault(etype, []).append(code)
    return UInput(events=events, name=name, input_props=list(props))


class UInputHandler:

    def __init__(self):
        self._devices = []
        self._init_devices()
        _touchpad = touchpad(lambda x: self._send(self.mouse, x))
        self._handle_touchpad = _touchpad.handle_touchpad

    def _init_devices(self):
        self.touch = _create_device(
            "remote-touch",
            [
                (E.EV_KEY, E.BTN_TOUCH),
                (E.EV_KEY, E.BTN_TOOL_FINGER),
                (E.EV_ABS, (E.ABS_X, _axis_info(E.ABS_X))),
                (E.EV_ABS, (E.ABS_Y, _axis_info(E.ABS_Y))),
                (E.EV_ABS, (E.ABS_MT_SLOT, _axis_info(E.ABS_MT_SLOT))),
                (E.EV_ABS, (E.ABS_MT_TRACKING_ID, _axis_info(E.ABS_MT_TRACKING_ID))),
                (E.EV_ABS, (E.ABS_MT_POSITION_X, _axis_info(E.ABS_MT_POSITION_X))),
                (E.EV_ABS, (E.ABS_MT_POSITION_Y, _axis_info(E.ABS_MT_POSITION_Y))),
                (E.EV_ABS, (E.ABS_MT_PRESSURE, PRESSURE_INFO)),
                (E.EV_ABS, (E.ABS_MT_DISTANCE, DISTANCE_INFO)),
                (E.EV_ABS, (E.ABS_PRESSURE, PRESSURE_INFO)),
                (E.EV_ABS, (E.ABS_MT_TOOL_TYPE, TOOL_INFO)),
            ],
            props=[E.INPUT_PROP_DIRECT],
        )

        self.abs_mouse = _create_device(
            "remote-pointer",
            [
                (E.EV_ABS, (E.ABS_X, _axis_info(E.ABS_X))),
                (E.EV_ABS, (E.ABS_Y, _axis_info(E.ABS_Y))),
                (E.EV_ABS, (E.ABS_MT_PRESSURE, PRESSURE_INFO)),
                (E.EV_KEY, E.BTN_LEFT),
                (E.EV_KEY, E.BTN_RIGHT),
                (E.EV_KEY, E.BTN_MIDDLE),
            ],
            props=[E.INPUT_PROP_POINTER],
        )

        self.mouse = _create_device(
            "remote-mouse",
            [
                (E.EV_REL, E.REL_X),
                (E.EV_REL, E.REL_Y),
                (E.EV_REL, E.REL_WHEEL),
                (E.EV_REL, E.REL_WHEEL_HI_RES),
                (E.EV_REL, E.REL_HWHEEL),
                (E.EV_REL, E.REL_HWHEEL_HI_RES),
                (E.EV_KEY, E.BTN_LEFT),
                (E.EV_KEY, E.BTN_RIGHT),
                (E.EV_KEY, E.BTN_MIDDLE),
            ],
            props=[E.INPUT_PROP_POINTER],
        )

        self.keyboard = _create_device(
            "remote-keyboard",
            [(E.EV_KEY, event) for event in set(KEYS.values())],
        )

        self._devices = [self.touch, self.abs_mouse, self.mouse, self.keyboard]
        self._slot_of = {}

    def _scale_x(self, x, source_width):
        return int(x * SCREEN_WIDTH / source_width)

    def _scale_y(self, y, source_height):
        return int(y * SCREEN_HEIGHT / source_height)

    def _send(self, device, events):
        for etype, code, value in events:
            device.write(etype, code, value)
        device.syn()

    def handle(self, message):
        data = json.loads(message)
        event_type = data.get("type")

        try:
            if event_type == "touch":
                self._handle_touch(data)
            elif event_type == "touchpad":
                self._handle_touchpad(data)
            elif event_type == "mouse":
                self._handle_mouse(data)
            elif event_type == "wheel":
                self._handle_wheel(data)
            elif event_type == "mouse_rel":
                self._handle_mouse_rel(data)
            elif event_type == "key":
                self._handle_key(data)
            elif event_type == "disconnect":
                self._handle_disconnect()
        except:
            print(traceback.format_exc())

    def _handle_disconnect(self):
        for device in self._devices:
            try:
                device.close()
            except:
                print(traceback.format_exc())
        self._devices = []
        time.sleep(0.3)
        self._init_devices()

    def _alloc_slot(self, tracking_id):
        used = set(self._slot_of.values())
        for slot in range(MAX_TOUCHES):
            if slot not in used:
                self._slot_of[tracking_id] = slot
                return slot
        return None

    def _handle_touch(self, data):
        action = data.get("action")
        touches = data.get("touches", [])
        events = []

        for t in touches:
            source_w = t.get("w", SCREEN_WIDTH)
            source_h = t.get("h", SCREEN_HEIGHT)
            identifier = int(t.get("identifier", 0)) & TRACKING_ID_MAX
            x = self._scale_x(t.get("x", 0), source_w)
            y = self._scale_y(t.get("y", 0), source_h)
            f = max(0, min(int(t.get("f", 512)), PRESSURE_MAX))

            if action == "touchstart":
                slot = self._alloc_slot(identifier)
                if slot is None:
                    continue
                events += [
                    (E.EV_ABS, E.ABS_MT_SLOT, slot),
                    (E.EV_ABS, E.ABS_MT_TRACKING_ID, identifier),
                    (E.EV_ABS, E.ABS_MT_TOOL_TYPE, MT_TOOL_FINGER),
                    (E.EV_ABS, E.ABS_MT_POSITION_X, x),
                    (E.EV_ABS, E.ABS_MT_POSITION_Y, y),
                    (E.EV_ABS, E.ABS_MT_PRESSURE, f),
                ]
            elif action == "touchmove":
                slot = self._slot_of.get(identifier)
                if slot is None:
                    continue
                events += [
                    (E.EV_ABS, E.ABS_MT_SLOT, slot),
                    (E.EV_ABS, E.ABS_MT_POSITION_X, x),
                    (E.EV_ABS, E.ABS_MT_POSITION_Y, y),
                    (E.EV_ABS, E.ABS_MT_PRESSURE, f),
                ]
            elif action == "touchend":
                slot = self._slot_of.pop(identifier, None)
                if slot is None:
                    continue
                events += [
                    (E.EV_ABS, E.ABS_MT_SLOT, slot),
                    (E.EV_ABS, E.ABS_MT_TRACKING_ID, -1),
                    (E.EV_ABS, E.ABS_MT_PRESSURE, 0),
                ]

        if not touches:
            return

        primary = touches[0]
        primary_w = primary.get("w", SCREEN_WIDTH)
        primary_h = primary.get("h", SCREEN_HEIGHT)
        primary_f = max(0, min(int(primary.get("f", 512)), PRESSURE_MAX))
        if action == "touchend" and not self._slot_of:
            events += [
                (E.EV_KEY, E.BTN_TOUCH, 0),
                (E.EV_KEY, E.BTN_TOOL_FINGER, 0),
            ]
            self._send(self.touch, events)
            return

        first_x = self._scale_x(primary.get("x", 0), primary_w)
        first_y = self._scale_y(primary.get("y", 0), primary_h)
        events += [
            (E.EV_KEY, E.BTN_TOUCH, 1),
            (E.EV_KEY, E.BTN_TOOL_FINGER, 1),
            (E.EV_ABS, E.ABS_X, first_x),
            (E.EV_ABS, E.ABS_Y, first_y),
            (E.EV_ABS, E.ABS_PRESSURE, primary_f),
        ]
        self._send(self.touch, events)

    def _handle_mouse(self, data):
        source_w = data.get("w", SCREEN_WIDTH)
        source_h = data.get("h", SCREEN_HEIGHT)
        button = MOUSE_BUTTONS[data.get("button", 0)]
        action = data["action"]

        if action == "move":
            events = [
                (E.EV_ABS, E.ABS_X, self._scale_x(data["x"], source_w)),
                (E.EV_ABS, E.ABS_Y, self._scale_y(data["y"], source_h)),
            ]
        else:
            events = [(E.EV_KEY, button, 1 if action == "down" else 0)]

        self._send(self.abs_mouse, events)

    def _handle_mouse_rel(self, data):
        button = MOUSE_BUTTONS[data.get("button", 0)]
        action = data["action"]

        if action == "move":
            events = [
                (E.EV_REL, E.REL_X, data.get("rel_x", 0)),
                (E.EV_REL, E.REL_Y, data.get("rel_y", 0)),
            ]
        else:
            events = [(E.EV_KEY, button, 1 if action == "down" else 0)]

        self._send(self.mouse, events)

    def _handle_wheel(self, data):
        delta_y = data.get("dy", 0)
        delta_x = data.get("dx", 0)
        events = []

        if delta_y:
            events.append((E.EV_REL, E.REL_WHEEL, int(-delta_y / 100)))
        if delta_x:
            events.append((E.EV_REL, E.REL_HWHEEL, int(delta_x / 100)))

        self._send(self.mouse, events)

    def _handle_key(self, data):
        key = data.get("code")
        if key.startswith("Key"):
            key = key[3:].lower()
        if key.startswith("Digit"):
            key = key[5:]
        code = KEYS.get(key)
        if code is None:
            return

        value = 1 if data["action"] == "down" else 0
        self._send(self.keyboard, [(E.EV_KEY, code, value)])

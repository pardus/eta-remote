#!/usr/bin/env python
import json
import os
import libevdev
from libevdev import InputEvent, EV_SYN, EV_ABS, EV_REL, EV_KEY, INPUT_PROP_DIRECT, INPUT_PROP_POINTER

SCREEN_WIDTH = int(os.environ.get("REMOTE_SCREEN_WIDTH", 3840))
SCREEN_HEIGHT = int(os.environ.get("REMOTE_SCREEN_HEIGHT", 2160))
MAX_TOUCHES = int(os.environ.get("REMOTE_MAX_TOUCHES", 11))
TRACKING_ID_MAX = 0xFFFF

KEYS = {}

for i in range(10):
    KEYS[str(i)] = getattr(EV_KEY, f"KEY_{i}")

for c in "abcdefghijklmnopqrstuvwxyz":
    KEYS[c] = getattr(EV_KEY, f"KEY_{c.upper()}")

MODIFIERS = {
    "ShiftLeft": EV_KEY.KEY_LEFTSHIFT,
    "ControlLeft": EV_KEY.KEY_LEFTCTRL,
    "AltLeft": EV_KEY.KEY_LEFTALT,
    "MetaLeft": EV_KEY.KEY_LEFTMETA,
    "CapsLock": EV_KEY.KEY_CAPSLOCK,
    "AltRight": EV_KEY.KEY_RIGHTALT,
}

NAVIGATION = {
    "Enter": EV_KEY.KEY_ENTER,
    "Backspace": EV_KEY.KEY_BACKSPACE,
    "Tab": EV_KEY.KEY_TAB,
    "Escape": EV_KEY.KEY_ESC,
    "Space": EV_KEY.KEY_SPACE,
    "Delete": EV_KEY.KEY_DELETE,
    "ArrowUp": EV_KEY.KEY_UP,
    "ArrowDown": EV_KEY.KEY_DOWN,
    "ArrowLeft": EV_KEY.KEY_LEFT,
    "ArrowRight": EV_KEY.KEY_RIGHT,
    "Home": EV_KEY.KEY_HOME,
    "End": EV_KEY.KEY_END,
    "PageUp": EV_KEY.KEY_PAGEUP,
    "PageDown": EV_KEY.KEY_PAGEDOWN,
    "PrintScreen": EV_KEY.KEY_SYSRQ,
}

FUNCTION_KEYS = {
    f"F{i}": getattr(EV_KEY, f"KEY_F{i}")
    for i in range(1, 13)
}

PUNCTUATION = {
    "Minus": EV_KEY.KEY_MINUS,
    "Equal": EV_KEY.KEY_EQUAL,
    "BracketLeft": EV_KEY.KEY_LEFTBRACE,
    "BracketRight": EV_KEY.KEY_RIGHTBRACE,
    "Backslash": EV_KEY.KEY_BACKSLASH,
    "Backquote": EV_KEY.KEY_GRAVE,
    "Semicolon": EV_KEY.KEY_SEMICOLON,
    "Quote": EV_KEY.KEY_APOSTROPHE,
    "Comma": EV_KEY.KEY_COMMA,
    "Period": EV_KEY.KEY_DOT,
    "Slash": EV_KEY.KEY_SLASH,
}

KEYS.update(MODIFIERS)
KEYS.update(NAVIGATION)
KEYS.update(FUNCTION_KEYS)
KEYS.update(PUNCTUATION)

MOUSE_BUTTONS = [
    EV_KEY.BTN_LEFT,
    EV_KEY.BTN_MIDDLE,
    EV_KEY.BTN_RIGHT,
]


def _create_device(name, capabilities):
    device = libevdev.Device()
    device.name = name
    for event, info in capabilities:
        if info:
            device.enable(event, info)
        else:
            device.enable(event)
    return device.create_uinput_device()


class UInputHandler:

    def __init__(self):
        self.touch = _create_device("remote-touch", [
            (INPUT_PROP_DIRECT, None),
            (EV_KEY.BTN_TOUCH, None),
            (EV_KEY.BTN_TOOL_FINGER, None),
            (EV_ABS.ABS_X, libevdev.InputAbsInfo(minimum=0, maximum=SCREEN_WIDTH)),
            (EV_ABS.ABS_Y, libevdev.InputAbsInfo(minimum=0, maximum=SCREEN_HEIGHT)),
            (EV_ABS.ABS_MT_SLOT, libevdev.InputAbsInfo(minimum=0, maximum=MAX_TOUCHES - 1)),
            (EV_ABS.ABS_MT_TRACKING_ID, libevdev.InputAbsInfo(minimum=0, maximum=TRACKING_ID_MAX)),
            (EV_ABS.ABS_MT_POSITION_X, libevdev.InputAbsInfo(minimum=0, maximum=SCREEN_WIDTH)),
            (EV_ABS.ABS_MT_POSITION_Y, libevdev.InputAbsInfo(minimum=0, maximum=SCREEN_HEIGHT)),
            (EV_ABS.ABS_MT_PRESSURE, libevdev.InputAbsInfo(minimum=0, maximum=1023)),
        ])

        self.abs_mouse = _create_device("remote-pointer", [
            (INPUT_PROP_POINTER, None),
            (EV_ABS.ABS_X, libevdev.InputAbsInfo(minimum=0, maximum=SCREEN_WIDTH)),
            (EV_ABS.ABS_Y, libevdev.InputAbsInfo(minimum=0, maximum=SCREEN_HEIGHT)),
            (EV_ABS.ABS_MT_PRESSURE, libevdev.InputAbsInfo(minimum=0, maximum=1023)),
            (EV_KEY.BTN_LEFT, None),
            (EV_KEY.BTN_RIGHT, None),
            (EV_KEY.BTN_MIDDLE, None),
        ])

        self.mouse = _create_device("remote-mouse", [
            (INPUT_PROP_POINTER, None),
            (EV_REL.REL_X, None),
            (EV_REL.REL_Y, None),
            (EV_REL.REL_WHEEL, None),
            (EV_REL.REL_HWHEEL, None),
            (EV_KEY.BTN_LEFT, None),
            (EV_KEY.BTN_RIGHT, None),
            (EV_KEY.BTN_MIDDLE, None),
        ])

        self.keyboard = _create_device("remote-keyboard", [
            (event, None) for event in set(KEYS.values())
        ])

        self._slot_of = {}

    def _scale_x(self, x, source_width):
        return int(x * SCREEN_WIDTH / source_width)

    def _scale_y(self, y, source_height):
        return int(y * SCREEN_HEIGHT / source_height)

    def _send(self, device, events):
        events.append(InputEvent(EV_SYN.SYN_REPORT, value=0))
        device.send_events(events)

    def handle(self, message):
        data = json.loads(message)
        event_type = data.get("type")

        if event_type == "touch":
            self._handle_touch(data)
        elif event_type == "mouse":
            self._handle_mouse(data)
        elif event_type == "wheel":
            self._handle_wheel(data)
        elif event_type == "mouse_rel":
            self._handle_mouse_rel(data)
        elif event_type == "key":
            self._handle_key(data)

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
            f = t.get("f", 512)

            if action == "touchstart":
                slot = self._alloc_slot(identifier)
                if slot is None:
                    continue
                events += [
                    InputEvent(EV_ABS.ABS_MT_SLOT, slot),
                    InputEvent(EV_ABS.ABS_MT_TRACKING_ID, identifier),
                    InputEvent(EV_ABS.ABS_MT_POSITION_X, x),
                    InputEvent(EV_ABS.ABS_MT_POSITION_Y, y),
                    InputEvent(EV_ABS.ABS_MT_PRESSURE, f),
                ]
            elif action == "touchmove":
                slot = self._slot_of.get(identifier)
                if slot is None:
                    continue
                events += [
                    InputEvent(EV_ABS.ABS_MT_SLOT, slot),
                    InputEvent(EV_ABS.ABS_MT_POSITION_X, x),
                    InputEvent(EV_ABS.ABS_MT_POSITION_Y, y),
                    InputEvent(EV_ABS.ABS_MT_PRESSURE, f),
                ]
            elif action == "touchend":
                slot = self._slot_of.pop(identifier, None)
                if slot is None:
                    continue
                events += [
                    InputEvent(EV_ABS.ABS_MT_SLOT, slot),
                    InputEvent(EV_ABS.ABS_MT_TRACKING_ID, -1),
                    InputEvent(EV_ABS.ABS_MT_PRESSURE, 0),
                ]

        if not touches:
            return

        primary = touches[0]
        if action == "touchend" and not self._slot_of:
            events += [
                InputEvent(EV_KEY.BTN_TOUCH, 0),
                InputEvent(EV_KEY.BTN_TOOL_FINGER, 0),
            ]
            self._send(self.touch, events)
            return

        first_x = self._scale_x(primary.get("x", 0), source_w)
        first_y = self._scale_y(primary.get("y", 0), source_h)
        events += [
            InputEvent(EV_KEY.BTN_TOUCH, 1),
            InputEvent(EV_KEY.BTN_TOOL_FINGER, 1),
            InputEvent(EV_ABS.ABS_X, first_x),
            InputEvent(EV_ABS.ABS_Y, first_y),
            InputEvent(EV_ABS.ABS_PRESSURE, f),
        ]
        print(events)
        self._send(self.touch, events)

    def _handle_mouse(self, data):
        source_w = data.get("w", SCREEN_WIDTH)
        source_h = data.get("h", SCREEN_HEIGHT)
        button = MOUSE_BUTTONS[data.get("button", 0)]
        action = data["action"]

        if action == "move":
            events = [
                InputEvent(EV_ABS.ABS_X, self._scale_x(data["x"], source_w)),
                InputEvent(EV_ABS.ABS_Y, self._scale_y(data["y"], source_h)),
            ]
        else:
            events = [InputEvent(button, 1 if action == "down" else 0)]

        self._send(self.abs_mouse, events)

    def _handle_mouse_rel(self, data):
        button = MOUSE_BUTTONS[data.get("button", 0)]
        action = data["action"]

        if action == "move":
            events = [
                InputEvent(EV_REL.REL_X, data.get("rel_x", 0)),
                InputEvent(EV_REL.REL_Y, data.get("rel_y", 0)),
            ]
        else:
            events = [InputEvent(button, 1 if action == "down" else 0)]

        self._send(self.mouse, events)

    def _handle_wheel(self, data):
        delta_y = data.get("dy", 0)
        delta_x = data.get("dx", 0)
        events = []

        if delta_y:
            events.append(InputEvent(EV_REL.REL_WHEEL, int(-delta_y / 100)))
        if delta_x:
            events.append(InputEvent(EV_REL.REL_HWHEEL, int(delta_x / 100)))

        self._send(self.mouse, events)

    def _handle_key(self, data):
        key = data.get("code")
        if key.startswith("Key"):
            key = key[3:].lower()
        if key.startswith("Digit"):
            key = key[5:]
        print(key)
        code = KEYS.get(key)
        if code is None:
            return

        value = 1 if data["action"] == "down" else 0
        self._send(self.keyboard, [InputEvent(code, value)])
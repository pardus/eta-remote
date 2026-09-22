import time
from evdev import ecodes as E

BUTTONS = [E.BTN_LEFT, E.BTN_RIGHT, E.BTN_MIDDLE]

class touchpad:
    def __init__(self, sender):
        self.pos = {"x": 0, "y": 0}
        self.count = 0
        self.count_max = 0
        self.moved = False
        self._send = sender

    def _click(self, button):
        button = min(button, len(BUTTONS)) -1
        self._send([(E.EV_KEY, BUTTONS[button], 1)])
        time.sleep(0.02)
        self._send([(E.EV_KEY, BUTTONS[button], 0)])

    def handle_touchpad(self, data):
        action = data.get("action")
        touches = data.get("touches", [])
        events = []
        if action == "touchstart":
            self.moved = False
            self.count += 1
            self.count_max = max(self.count, self.count_max)
            for t in touches:
                tid = t.get("identifier", -1)
                if tid == 0:
                    self.pos = {
                        "x": t.get("x", 0),
                        "y": t.get("y", 0)
                    }
        elif action == "touchmove":
            for t in touches:
                if t.get("identifier", -1) == 0:
                    x = t.get("x", 0)
                    y = t.get("y", 0)
                    dx = x - self.pos["x"]
                    dy = y - self.pos["y"]
                    if dx != 0 or dy != 0:
                        events += [
                            (E.EV_REL, E.REL_X, dx),
                            (E.EV_REL, E.REL_Y, dy),
                        ]
                        self.pos = {"x": x, "y": y}
                        self.moved = True
        elif action == "touchend":
            self.count -= 1
            for t in touches:
                if t.get("identifier", -1) == 0:
                    if not self.moved:
                        self._click(self.count_max)
                    self.count = 0
                    self.count_max = 0
        self._send(events)

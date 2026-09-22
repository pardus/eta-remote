import time
from evdev import ecodes as E

class touchpad:
    def __init__(self, sender):
        self.pos = {"x": 0, "y": 0}
        self.count = 0
        self.moved = False
        self._send = sender

    def _click(self, button = E.BTN_LEFT):
        self._send([(E.EV_KEY, button, 1)])
        time.sleep(0.02)
        self._send([(E.EV_KEY, button, 0)])

    def handle_touchpad(self, data):
        action = data.get("action")
        touches = data.get("touches", [])
        events = []
        if action == "touchstart":
            self.moved = False
            self.count = len(touches)
            if self.count > 0:
                self.pos = {
                    "x": touches[0].get("x", 0),
                    "y": touches[0].get("y", 0)
                }
        elif action == "touchmove":
            self.moved = True
            self.count = len(touches)
            if self.count > 0:
                x = touches[0].get("x", 0)
                y = touches[0].get("y", 0)
                events += [
                    (E.EV_REL, E.REL_X, x - self.pos["x"]),
                    (E.EV_REL, E.REL_Y, y - self.pos["y"]),
                ]
                self.pos = {"x": x, "y": y}
        elif action == "touchend":
            if not self.moved:
                self._click()
        self._send(events)

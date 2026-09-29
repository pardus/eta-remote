import time
import threading
from evdev import ecodes as E

BUTTONS = [E.BTN_LEFT, E.BTN_RIGHT, E.BTN_MIDDLE]

TOUCH_TRESHOLD = 0.125

class touchpad:
    def __init__(self, sender):
        self.pos = {"x": 0, "y": 0, "v": 0}
        self.count = 0
        self.count_max = 0
        self.moved = False
        self._send = sender
        self._last_event = 0
        self._lock = False
        self._primary = 0

    def _click(self, button, delay=TOUCH_TRESHOLD):
        self._last_event = time.time()
        time.sleep(delay)
        if self._lock:
            return
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
            if self.count == 0 and len(touches) > 0:
                self._primary = touches[0].get("identifier", 0)
            self.count += 1
            self.count_max = max(self.count, self.count_max)
            for t in touches:
                tid = t.get("identifier", -1)
                if tid == self._primary:
                    self.pos = {
                        "x": t.get("x", 0),
                        "y": t.get("y", 0),
                        "v": -1
                    }
                    if  time.time() - self._last_event < TOUCH_TRESHOLD:
                        self._send([(E.EV_KEY, E.BTN_LEFT, 1)])
                        self._lock = True
        elif action == "touchmove":
            if len(touches) > 1:
                v = 0
                for t in touches:
                    v += t.get("y", 0)
                v = v / len(touches)
                dv = v - self.pos["v"]
                if self.pos["v"] > 0:
                    events += [
                        (E.EV_REL, E.REL_WHEEL_HI_RES, int(dv*-5))
                    ]
                self.pos["v"] = v
            for t in touches:
                if t.get("identifier", -1) == self._primary:
                    x = t.get("x", 0)
                    y = t.get("y", 0)
                    dx = x - self.pos["x"]
                    dy = y - self.pos["y"]
                    if dx != 0 or dy != 0:
                        if len(touches) == 1:
                            events += [
                                (E.EV_REL, E.REL_X, dx),
                                (E.EV_REL, E.REL_Y, dy),
                            ]
                        self.pos["x"] = x
                        self.pos["y"] = y
                        self.moved = True
        elif action == "touchend":
            self.count -= 1
            for t in touches:
                if t.get("identifier", -1) == self._primary or len(touches) == 1:
                    if self._lock:
                        self._send([(E.EV_KEY, E.BTN_LEFT, 0)])
                        self._lock = False
                    elif not self.moved:
                        threading.Thread(target=self._click, args=(self.count_max,)).start()
                    self.count = 0
                    self.count_max = 0
                    self._primary = 0
        self._send(events)

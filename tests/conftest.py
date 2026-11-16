"""Make logic tests runnable even on machines without a graphical SDL stack.

When real pygame is present, tests use the real library instead of the stub.
The stub verifies Python-level hooks, not physical sound or GUI rendering.
"""
import importlib.util
import sys
import types

if importlib.util.find_spec("pygame") is None:
    pg = types.ModuleType("pygame")
    names = [
        "escape", "p", "r", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "tab", "m", "n", "-", "=",
        "kp +", "kp -", "left", "right", "up", "down", "x", "z",
        "space", "c", "left shift", "h", "j", "k", "u", "i", "q",
        "w", "e", "a", "d", "s", "b", "y", "return", "kp enter", "1", "2", "3", "4",
    ]
    key_by_name = {name: 1000 + i for i, name in enumerate(names)}
    name_by_key = {code: name for name, code in key_by_name.items()}
    pg.K_ESCAPE = key_by_name["escape"]
    pg.K_p = key_by_name["p"]
    pg.K_r = key_by_name["r"]
    pg.K_F1 = key_by_name["f1"]
    pg.K_F2 = key_by_name["f2"]
    pg.K_F3 = key_by_name["f3"]
    pg.K_F4 = key_by_name["f4"]
    pg.K_F5 = key_by_name["f5"]
    pg.K_F6 = key_by_name["f6"]
    pg.K_F7 = key_by_name["f7"]
    pg.K_F8 = key_by_name["f8"]
    pg.K_TAB = key_by_name["tab"]
    pg.K_m = key_by_name["m"]
    pg.K_n = key_by_name["n"]
    pg.K_MINUS = key_by_name["-"]
    pg.K_EQUALS = key_by_name["="]
    pg.K_KP_PLUS = key_by_name["kp +"]
    pg.K_KP_MINUS = key_by_name["kp -"]
    pg.K_SPACE = key_by_name["space"]
    pg.K_x = key_by_name["x"]
    pg.K_RIGHT = key_by_name["right"]
    pg.K_LEFT = key_by_name["left"]
    pg.K_w = key_by_name["w"]
    pg.K_a = key_by_name["a"]
    pg.K_d = key_by_name["d"]
    pg.K_s = key_by_name["s"]
    pg.K_UP = key_by_name["up"]
    pg.K_DOWN = key_by_name["down"]
    pg.K_RETURN = key_by_name["return"]
    pg.K_KP_ENTER = key_by_name["kp enter"]
    for digit in range(1, 5):
        setattr(pg, "K_" + str(digit), key_by_name[str(digit)])
    pg.KEYDOWN = 101
    pg.KEYUP = 102
    pg.QUIT = 103
    pg.MOUSEBUTTONDOWN = 104
    pg.error = type("PygameError", (Exception,), {})

    def key_code(name):
        if name not in key_by_name:
            raise ValueError("invalid key")
        return key_by_name[name]

    pg.key = types.SimpleNamespace(key_code=key_code, name=lambda code: name_by_key[code])

    class Rect:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.w, self.h = x, y, w, h
        def collidepoint(self, point):
            return self.x <= point[0] < self.x + self.w and self.y <= point[1] < self.y + self.h

    pg.Rect = Rect

    class Sound:
        def __init__(self, path):
            from pathlib import Path
            if not Path(path).is_file():
                raise OSError(path)
            self.volume = 1
            self.count = 0
        def set_volume(self, value):
            self.volume = value
        def play(self):
            self.count += 1

    class Music:
        def __init__(self):
            self.loaded = False
            self.playing = False
            self.paused = False
            self.volume = 1
        def load(self, path):
            self.loaded = True
        def set_volume(self, volume):
            self.volume = volume
        def play(self, loops=0):
            self.playing = True
        def pause(self):
            self.paused = True
        def unpause(self):
            self.paused = False
        def stop(self):
            self.playing = False
        def get_busy(self):
            return self.playing

    music = Music()
    pg.mixer = types.SimpleNamespace(
        get_init=lambda: (22050, -16, 2), init=lambda: None,
        set_num_channels=lambda count: None, get_num_channels=lambda: 8,
        Sound=Sound, music=music,
    )
    sys.modules["pygame"] = pg

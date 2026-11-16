"""Windows IME protection for the Pygame keyboard-only game.

We disable text composition on the SDL window, and (Windows only) temporarily
unassociate the IME context from that *one* HWND. The user's system-wide input
language is neither switched nor permanently changed. No elevated rights are
needed. Restore the previous context when the window is closed.
"""
import ctypes
import sys


class GameKeyboardMode:
    def __init__(self, pygame_module, *, platform=None, win_dll=None):
        self.pygame = pygame_module
        self.platform = sys.platform if platform is None else platform
        self._win_dll = win_dll
        self._hwnd = None
        self._imm_associate = None
        self._previous_ime = None
        self._restored = False

    def _stop_text_composition(self):
        key = getattr(self.pygame, "key", None)
        if key is None:
            return
        stop = getattr(key, "stop_text_input", None)
        if callable(stop):
            try:
                stop()
            except (self.pygame.error, RuntimeError):
                pass
        # Auto-repeat is handled by DAS/ARR in Tetris, not OS key repeat.
        repeat = getattr(key, "set_repeat", None)
        if callable(repeat):
            try:
                repeat()
            except (self.pygame.error, RuntimeError):
                pass

    def enable(self):
        self._stop_text_composition()
        if self.platform != "win32":
            return False
        try:
            get_wm_info = getattr(self.pygame.display, "get_wm_info", None)
            hwnd = (get_wm_info() or {}).get("window") if callable(get_wm_info) else None
            if not hwnd:
                return False
            library = self._win_dll or ctypes.WinDLL("imm32", use_last_error=True)
            associate = library.ImmAssociateContext
            # HWND and HIMC are pointer-sized. Do not use c_int (truncates x64).
            associate.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            associate.restype = ctypes.c_void_p
            self._hwnd = int(hwnd)
            self._imm_associate = associate
            self._previous_ime = associate(ctypes.c_void_p(self._hwnd), None)
            return True
        except (AttributeError, OSError, TypeError, ValueError):
            # Don't stop the game if the current SDL / Windows backend does
            # not expose a native window handle or IMM support.
            self._hwnd = None
            self._imm_associate = None
            return False

    def refresh(self):
        """An IME may be reattached after the window loses/regains focus."""
        self._stop_text_composition()
        if self._imm_associate and self._hwnd:
            try:
                self._imm_associate(ctypes.c_void_p(self._hwnd), None)
            except (OSError, ValueError):
                pass

    def restore(self):
        if self._restored:
            return
        self._restored = True
        if self._imm_associate is not None and self._hwnd and self._previous_ime:
            try:
                self._imm_associate(ctypes.c_void_p(self._hwnd),
                                    ctypes.c_void_p(self._previous_ime))
            except (OSError, ValueError):
                pass

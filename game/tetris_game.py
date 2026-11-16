"""Human-playable single- and two-player TetrisBattle.

Keeps the original battle rules, boards, images, and key assignments while
adding customizable controls, help, pause/restart, and background/SFX audio.
"""
import argparse
import pygame

from TetrisBattle.settings import FPS, MAX_TIME, SCREENWIDTH, SCREENHEIGHT, SPEED_UP, BOMB_CELL, load_imgs
from TetrisBattle.renderer import Renderer
from TetrisBattle.tetris import Tetris, Player, Judge, freeze, get_infos
from TetrisBattle.controls import load_keymaps, describe_keymaps
from TetrisBattle.audio import AudioManager
from TetrisBattle.effects import EffectEngine
from TetrisBattle.windows_input import GameKeyboardMode

POS_LIST = [
    {
        'combo': (44, 437), 'tetris': (314, 477), 'tspin': (304, 477),
        'back2back': (314, 437), 'board': (112, 138), 'drawscreen': (112, 138),
        'big_ko': (44, 235), 'ko': (140, 233), 'transparent': (110, 135),
        'attack_clean': (298, 140, 3, 360), 'attack_alarm': (298, 481, 3, 18),
        'you_win': (120, 230), 'you_lose': (115, 230),
    },
    {
        'combo': (415, 437), 'tetris': (685, 477), 'tspin': (675, 477),
        'back2back': (685, 437), 'board': (495, 138), 'drawscreen': (495, 138),
        'big_ko': (426, 235), 'ko': (527, 233), 'transparent': (494, 135),
        'attack_clean': (680, 140, 3, 360), 'attack_alarm': (680, 481, 3, 18),
        'you_win': (520, 230), 'you_lose': (515, 230),
    },
]

MAP_RECTS = [
    pygame.Rect(155, 75, 200, 200), pygame.Rect(439, 75, 200, 200),
    pygame.Rect(155, 309, 200, 200), pygame.Rect(439, 309, 200, 200),
]
MAP_NAMES = ("none", "classic", "comboking", "lunchbox")


class TetrisGame:
    def __init__(self, mode="single", controls="classic", keymap=None,
                 audio=True, music_volume=0.30, sfx_volume=0.55,
                 bombs=True, effects=True, sfx_pack="auto",
                 das_ms=120.0, arr_ms=25.0, soft_drop_ms=30.0,
                 debug_input=False, start_map=None,
                 mino_skin="classic", ghost_skin="outline", bomb_skin="bomb",
                 original_visuals=True):
        pygame.init()
        # Keyboard focus is controlled by the OS/SDL window manager, not audio.
        # Only enable optional diagnostics when explicitly requested.
        self.debug_input = bool(debug_input)
        self._last_input = "(no key received)"
        self.start_map = start_map
        self.mode = mode
        self.num_players = 1 if mode == "single" else 2
        self.controls = controls
        self.keymap = keymap
        self.das_ms = float(das_ms)
        self.arr_ms = float(arr_ms)
        self.soft_drop_ms = float(soft_drop_ms)
        if not (0 <= self.das_ms <= 500 and 1 <= self.arr_ms <= 250
                and 1 <= self.soft_drop_ms <= 250):
            raise ValueError("Input timing out of range: DAS 0-500, ARR/soft drop 1-250 milliseconds")
        self.bombs_enabled = bool(bombs)
        self.visual_effects_enabled = bool(effects)
        self.effects = EffectEngine(enabled=self.visual_effects_enabled)
        self.keymaps = load_keymaps(mode, controls, keymap)
        self.screen = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
        pygame.display.set_caption("Tetris Battle")
        # Stop SDL text composition and detach the Windows IME from THIS
        # window only. The user's global language / keyboard stays intact.
        self._keyboard_mode = GameKeyboardMode(pygame)
        self._keyboard_mode.enable()
        self.renderer = Renderer(self.screen, load_imgs(),
                                 mino_skin=mino_skin, ghost_skin=ghost_skin,
                                 bomb_skin=bomb_skin, original_visuals=original_visuals)
        if original_visuals:
            self.effects.load_source_visuals()
        self.clock = pygame.time.Clock()
        self.audio = AudioManager(enabled=audio, music_volume=music_volume,
                                  sfx_volume=sfx_volume, sfx_pack=sfx_pack)
        self._last_gridchoice = None
        self._quit_requested = False
        self._font = pygame.font.SysFont("arial", 19)
        self._small_font = pygame.font.SysFont("arial", 15)
        self._title_font = pygame.font.SysFont("arial", 29, bold=True)

    def _text(self, value, x, y, color=(242, 245, 250), font=None):
        label = (font or self._font).render(value, True, color)
        self.screen.blit(label, (x, y))

    def _panel(self, x, y, width, height, alpha=228):
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((12, 17, 31, alpha))
        self.screen.blit(panel, (x, y))

    def _footnote(self, value):
        self._panel(14, 557, 772, 35, 195)
        self._text(value, 26, 566, font=self._small_font)

    def _game_event(self, name, player_index, tetris):
        """Route an actual state-machine event to both SFX and VFX."""
        if name == "bomb_chain":
            tier = getattr(tetris, "bomb_chain_count", 0)
        elif name == "line_clear":
            tier = getattr(tetris, "cleared", 1)
        else:
            tier = getattr(tetris, "combo", 0)
        self.audio.play(name, player_index=player_index, intensity=tier)
        engine = getattr(self, "effects", None)
        if engine is None:
            return
        pos = POS_LIST[player_index]["board"]
        rect = (pos[0], pos[1], 180, 360)
        positions = ()
        if name in ("bomb_explode", "bomb_chain"):
            excess = len(tetris.grid[0]) - 20
            positions = [(x, y - excess) for x, y in tetris.last_blast
                         if 0 <= y - excess < 20]
        elif name in ("line_clear", "tetris", "perfect_clear"):
            positions = [(x, y) for y in tetris.last_cleared_rows for x in range(10)]
        engine.event(name, rect, positions, max(0, tetris.combo + 1))

    def _draw_status(self, entries):
        """Show real incoming garbage and bomb-row information."""
        for i, entry in enumerate(entries):
            tetris = entry["tetris"]
            x = (92, 476)[i]
            self._panel(x, 505, 234, 44, 210)
            self._text("LINES {:>3}   SENT {:>3}".format(tetris.total_lines, tetris.sent),
                       x + 8, 509, font=self._small_font)
            if tetris.bombs_enabled:
                bombs = sum(cell == BOMB_CELL for column in tetris.grid for cell in column)
                self._text("IN {}  BOMBS {} (AUTO)".format(tetris.attacked, bombs),
                           x + 8, 526, color=(255, 207, 78), font=self._small_font)
            else:
                self._text("SOLID GARBAGE (NO BOMBS)", x + 8, 526, font=self._small_font)

    def update_time(self, remaining_ms):
        # One clock update PER FRAME, not once per player (the original double
        # mode accidentally advanced its countdown twice as quickly).
        return max(0, remaining_ms - (1000.0 / FPS) * SPEED_UP)

    def play(self):
        # Explicit --map is a quick-start mode: show a playable board at once.
        page = "start" if getattr(self, "start_map", None) is not None else "menu"
        try:
            while page != "exit":
                if page == "menu":
                    page = self.menu()
                elif page in ("start", "restart"):
                    page = self.start(reuse_map=(page == "restart"))
                elif page == "viewmap":
                    page = self.viewmap()
                elif page == "instructions":
                    page = self.instructions()
                else:
                    page = "menu"
        finally:
            self.audio.stop_music()
            keyboard_mode = getattr(self, "_keyboard_mode", None)
            if keyboard_mode is not None:
                keyboard_mode.restore()
            pygame.quit()

    def _menu_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit_requested = True
                return "exit", None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "escape", None
                if event.key == pygame.K_RETURN:
                    return "enter", None
                if event.key == pygame.K_F1:
                    return "help", None
                if event.key == pygame.K_F2:
                    return "preset", None
                if event.key == pygame.K_F3:
                    return "visuals", None
                if event.key == pygame.K_F4:
                    return "bombs", None
                if event.key == pygame.K_TAB:
                    return "mode", None
                if self._visual_hotkey(event.key) or self._audio_hotkey(event.key):
                    continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                return "click", event.pos
        return None, None

    def _visual_hotkey(self, key):
        """F5/F6/F7 change artwork only. Do not touch the active Tetris object."""
        groups = {
            pygame.K_F5: "mino",
            pygame.K_F6: "ghost",
            pygame.K_F7: "bomb",
        }
        if key == pygame.K_F8:
            visual = getattr(getattr(self, "renderer", None), "visuals", None)
            if visual is not None and hasattr(visual, "enabled"):
                visual.enabled = not visual.enabled
                visual.apply()
            return True
        group = groups.get(key)
        if group:
            visual = getattr(getattr(self, "renderer", None), "visuals", None)
            if visual is not None and hasattr(visual, "cycle"):
                visual.cycle(group)
                if getattr(self, "audio", None):
                    self.audio.play("menu")
            return True
        return False

    def _audio_hotkey(self, key):
        if key == pygame.K_m:
            self.audio.toggle_music()
            return True
        if key == pygame.K_n:
            self.audio.toggle_sfx()
            return True
        if key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.audio.adjust_volume(.10)
            return True
        if key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.audio.adjust_volume(-.10)
            return True
        return False

    def menu(self):
        start_button = pygame.Rect(320, 204, 146, 50)
        buttons = [pygame.Rect(325, y * 42 + 275, 135, 30) for y in range(3)]
        while True:
            action, point = self._menu_events()
            if action == "exit" or action == "escape":
                return "exit"
            if action == "enter":
                self.audio.play("menu")
                return "start"
            if action == "help":
                return "instructions"
            if action == "mode":
                self.mode = "double" if self.mode == "single" else "single"
                self.num_players = 1 if self.mode == "single" else 2
                self.keymaps = load_keymaps(self.mode, self.controls if self.mode == "single" else "classic", self.keymap)
                self.audio.play("menu")
            if action == "visuals":
                self.visual_effects_enabled = not self.visual_effects_enabled
                self.effects.enabled = self.visual_effects_enabled
                if not self.visual_effects_enabled:
                    self.effects.clear()
                self.audio.play("menu")
            if action == "bombs":
                self.bombs_enabled = not self.bombs_enabled
                self.audio.play("menu")
            if action == "preset" and self.mode == "single" and not self.keymap:
                self.controls = "wasd" if self.controls == "classic" else "classic"
                self.keymaps = load_keymaps(self.mode, self.controls)
                self.audio.play("menu")
            if action == "click":
                if start_button.collidepoint(point):
                    self.audio.play("menu")
                    return "start"
                for rect, page in zip(buttons, ("viewmap", "instructions", "exit")):
                    if rect.collidepoint(point):
                        self.audio.play("menu")
                        return page

            self.renderer.drawByName("intro", 0, 0)
            if hasattr(self.renderer, "draw_facebook_brand"):
                self.renderer.draw_facebook_brand()
            pos = pygame.mouse.get_pos()
            if start_button.collidepoint(pos):
                self.renderer.drawByName("startbutton", 319, 207)
            elif buttons[0].collidepoint(pos):
                self.renderer.drawByName("setmapbutton", 325, 274)
            elif buttons[1].collidepoint(pos):
                self.renderer.drawByName("helpbutton", 325, 317)
            elif buttons[2].collidepoint(pos):
                self.renderer.drawByName("quitbutton", 325, 360)

            preset = " | F2 Switch layout: {}".format(self.controls.upper()) if self.mode == "single" and not self.keymap else ""
            self._footnote("ENTER Start | TAB {} | F1 Help{} | F3 FX:{} | F4 Bomb:{} | F5/6/7 Skins".format(
                self.mode.upper(), preset,
                "ON" if self.visual_effects_enabled else "OFF",
                "ON" if self.bombs_enabled else "OFF"))
            pygame.display.flip()
            self.clock.tick(FPS)

    def _map_screen(self, choose):
        """Select a map with either mouse OR keyboard (previously Enter cancelled).

        The original version only accepted mouse clicks on this screen. Users
        starting with Enter could never reach the playable game from a keyboard.
        """
        selected = 0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit_requested = True
                    return None
                if event.type == pygame.KEYDOWN:
                    key = event.key
                    if key == pygame.K_ESCAPE:
                        return None
                    if key in (pygame.K_LEFT, pygame.K_a):
                        selected = (selected - 1) % len(MAP_NAMES)
                        self.audio.play("menu")
                    elif key in (pygame.K_RIGHT, pygame.K_d):
                        selected = (selected + 1) % len(MAP_NAMES)
                        self.audio.play("menu")
                    elif key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 2) % len(MAP_NAMES)
                        self.audio.play("menu")
                    elif key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 2) % len(MAP_NAMES)
                        self.audio.play("menu")
                    elif pygame.K_1 <= key <= pygame.K_4:
                        selected = key - pygame.K_1
                        self._suppress_initial_space = False
                        self.audio.play("menu")
                        return MAP_NAMES[selected] if choose else None
                    elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        # Confirming a map with Space must not ALSO hard-drop
                        # the unseen first piece. It will work on next press.
                        self._suppress_initial_space = (key == pygame.K_SPACE and choose)
                        self.audio.play("menu")
                        return MAP_NAMES[selected] if choose else None
                    elif self._audio_hotkey(key):
                        continue
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for index, rect in enumerate(MAP_RECTS):
                        if rect.collidepoint(event.pos):
                            self._suppress_initial_space = False
                            self.audio.play("menu")
                            return MAP_NAMES[index] if choose else None
            self.renderer.drawByName("back1", 0, 0)
            # Do not replace keyboard selection on every frame with the
            # stationary mouse pointer's hover location.
            x, y = ((149, 64), (431, 64), (149, 301), (431, 301))[selected]
            self.renderer.drawByName("outline", x, y)
            self._footnote("Arrows / WASD select | 1-4 direct | ENTER / SPACE {} | ESC Back".format(
                "PLAY" if choose else "Back"))
            pygame.display.flip()
            self.clock.tick(FPS)

    @staticmethod
    def _keyboard_focused():
        """Treat unsupported focus APIs as unknown, never as confirmed loss."""
        focus = getattr(pygame.key, "get_focused", None)
        if focus is None:
            return True
        try:
            return bool(focus())
        except pygame.error:
            return True

    def _focus_overlay(self, snapshot):
        self.screen.blit(snapshot, (0, 0))
        self._panel(140, 219, 520, 139, 243)
        self._text("KEYBOARD FOCUS LOST", 241, 239, font=self._title_font)
        self._text("Click inside this game window, then use the keyboard.", 177, 298,
                   font=self._small_font)
        self._text("Game is paused until the window is active.", 218, 325,
                   font=self._small_font)
        pygame.display.flip()
        self.clock.tick(FPS)

    def _debug_key_event(self, event):
        if event.type not in (pygame.KEYDOWN, pygame.KEYUP):
            return
        try:
            key_name = pygame.key.name(event.key)
        except (ValueError, AttributeError):
            key_name = str(event.key)
        self._last_input = "{} {}".format(
            "DOWN" if event.type == pygame.KEYDOWN else "UP", key_name)
        if getattr(self, "debug_input", False):
            print("[INPUT] mode={} {} focus={}".format(
                self.mode, self._last_input, self._keyboard_focused()), flush=True)

    def setmap(self):
        return self._map_screen(choose=True)

    def viewmap(self):
        self._map_screen(choose=False)
        return "exit" if self._quit_requested else "menu"

    def _draw_help(self, is_game=False):
        # Dynamic text displays the *active* keymap, including JSON overrides.
        self._panel(70, 35, 660, 526, 245)
        self._text("TETRIS BATTLE - CONTROLS", 102, 58, font=self._title_font)
        descriptions = describe_keymaps(self.keymaps)
        col_x = (103, 420) if len(descriptions) == 2 else (103,)
        for col, lines in zip(col_x, descriptions):
            for number, line in enumerate(lines):
                self._text(line, col, 100 + number * 27,
                           color=(112, 213, 250) if number == 0 else (239, 245, 252),
                           font=self._font)
        self._text("BOMBS: Incoming garbage rows contain a bomb target.", 102, 380,
                   font=self._small_font, color=(255, 211, 112))
        self._text("Land on the bomb to clear its entire row; aligned bombs chain.", 102, 400,
                   font=self._small_font, color=(255, 211, 112))
        self._text("P Pause/Resume    R Restart    ESC Menu/Back    F1 Help", 102, 428,
                   font=self._small_font)
        self._text("M Music    N SFX    - / = Volume    F3 Visual FX", 102, 450,
                   font=self._small_font)
        self._text("F5 Mino Skin   F6 Ghost   F7 Bomb Skin   F8 Legacy / Original", 102, 471,
                   font=self._small_font, color=(138, 215, 246))
        if self.mode == "single" and not self.keymap:
            self._text("Menu: TAB 1P/2P, F2 Classic/WASD, F4 Bombs", 102, 492,
                       font=self._small_font)
        self._text("F1 Close help{}".format(" / P Resume" if is_game else " / ESC Back"),
                   102, 525, color=(247, 203, 106), font=self._small_font)

    def instructions(self):
        while True:
            action, _ = self._menu_events()
            if action == "exit":
                return "exit"
            if action in ("escape", "enter", "help", "click"):
                return "menu"
            self.renderer.drawByName("back2", 0, 0)
            self._draw_help()
            pygame.display.flip()
            self.clock.tick(FPS)

    def start(self, reuse_map=False):
        # --map starts a playable match immediately without the map chooser.
        if reuse_map:
            gridchoice = self._last_gridchoice
        elif getattr(self, "start_map", None) is not None:
            gridchoice = self.start_map
        else:
            gridchoice = self.setmap()
        if gridchoice is None:
            return "exit" if self._quit_requested else "menu"
        self._last_gridchoice = gridchoice
        return self._run_match(gridchoice)

    def _record_single_stats(self, tetris, scores):
        height_sum, diff_sum, max_height, holes = get_infos(tetris.get_board())
        previous = self.last_infos
        print({
            "is_fallen": tetris.is_fallen,
            "height_sum": height_sum - previous["height_sum"],
            "diff_sum": diff_sum - previous["diff_sum"],
            "max_height": max_height - previous["max_height"],
            "holes": holes - previous["holes"],
            "n_used_block": tetris.n_used_block - previous["n_used_block"],
            "scores": scores,
            "cleared": tetris.cleared,
        })
        self.last_infos = {
            "height_sum": height_sum, "diff_sum": diff_sum,
            "max_height": max_height, "holes": holes,
            "n_used_block": tetris.n_used_block,
        }

    def _pause_overlay(self, snapshot, help_visible):
        self.screen.blit(snapshot, (0, 0))
        if help_visible:
            self._draw_help(is_game=True)
        else:
            self._panel(235, 200, 330, 178, 238)
            self._text("PAUSED", 338, 227, font=self._title_font)
            self._text("P  -  Resume", 306, 285)
            self._text("F1 Help   R Restart", 306, 316, font=self._small_font)
            self._text("ESC Return to menu", 306, 341, font=self._small_font)
        pygame.display.flip()
        self.clock.tick(FPS)

    def _end_match(self, entries, winner=None, lost=False):
        self.audio.stop_music()
        if self.num_players == 2:
            for entry in entries:
                tetris, pos = entry["tetris"], entry["pos"]
                self.renderer.drawByName("transparent", *pos["transparent"])
                name = "you_win" if tetris.get_id() == winner else "you_lose"
                self.renderer.drawByName(name, *pos[name])
            if winner is None:
                self._panel(292, 235, 216, 100, 232)
                self._text("DRAW", 352, 264, font=self._title_font)
                self.audio.play("ko")
            else:
                self.audio.play("win")
        else:
            pos = entries[0]["pos"]
            self.renderer.drawByName("transparent", *pos["transparent"])
            self.audio.play("lose" if lost else "win")
            self._panel(265, 255, 280, 75, 228)
            self._text("GAME OVER" if lost else "TIME UP", 317, 276, font=self._title_font)
        pygame.display.flip()
        # Let results and their sound be perceptible. Original game also held
        # this screen for 2 seconds before returning to the main menu.
        pygame.time.wait(2000)
        return "menu"

    @staticmethod
    def _topout_result(entries):
        """Return (winner_id, lost) for a real top-out, else None.

        One loser in 2P means the OTHER player wins immediately. If both
        top out in the same frame, neither is awarded a win (draw).
        """
        losers = [index for index, entry in enumerate(entries)
                  if entry["tetris"].check_KO()]
        if not losers:
            return None
        if len(entries) == 1:
            return (None, True)
        if len(losers) == len(entries):
            return (None, False)
        winner_index = next(i for i in range(len(entries)) if i not in losers)
        return (entries[winner_index]["tetris"].get_id(), False)

    def _finish_on_topout(self, entries):
        """Stop the current match immediately: one KO, not best-of-three."""
        result = self._topout_result(entries)
        if result is None:
            return None
        for i, entry in enumerate(entries):
            if entry["tetris"].check_KO():
                self._game_event("ko", i, entry["tetris"])
        return self._end_match(entries, winner=result[0], lost=result[1])

    def _run_match(self, gridchoice):
        self.last_infos = {
            "height_sum": 0, "diff_sum": 0, "max_height": 0,
            "holes": 0, "n_used_block": 0,
        }
        entries = []
        for i, info in enumerate(self.keymaps):
            tetris = Tetris(Player(info), gridchoice, bombs_enabled=getattr(self, "bombs_enabled", True),
                            modern_controls=True,
                            das_ms=getattr(self, "das_ms", 120.0),
                            arr_ms=getattr(self, "arr_ms", 25.0),
                            soft_drop_ms=getattr(self, "soft_drop_ms", 30.0))
            tetris.on_event = lambda name, index=i, model=tetris: self._game_event(name, index, model)
            entries.append({"tetris": tetris, "pos": POS_LIST[i]})

        if self.num_players == 1 and getattr(self, "_suppress_initial_space", False):
            # The Space KEYDOWN which selected the map was used by the menu.
            # Wait for key release before it can hard-drop a piece.
            entries[0]["tetris"]._held_actions.add(pygame.K_SPACE)
        self._suppress_initial_space = False

        paused = False
        show_help = False
        paused_before_help = False
        pause_snapshot = None
        remaining_ms = float(MAX_TIME)
        previous_frame_ms = 1000.0 / FPS
        focus_snapshot = None
        focus_lost = False
        self.renderer.drawByName("gamescreen", 0, 0)
        self.audio.start_music()
        if getattr(self, "effects", None) is not None:
            self.effects.clear()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.audio.stop_music()
                    return "exit"
                self._debug_key_event(event)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.audio.stop_music()
                        return "menu"
                    if event.key == pygame.K_F3:
                        self.visual_effects_enabled = not getattr(self, "visual_effects_enabled", True)
                        if getattr(self, "effects", None) is not None:
                            self.effects.enabled = self.visual_effects_enabled
                            if not self.visual_effects_enabled:
                                self.effects.clear()
                        continue
                    if event.key == pygame.K_r:
                        self.audio.stop_music()
                        return "restart"
                    if self._visual_hotkey(event.key) or self._audio_hotkey(event.key):
                        continue
                    if event.key == pygame.K_p:
                        paused = not paused
                        show_help = False
                        self.audio.pause_music(paused)
                        if paused:
                            for entry in entries:
                                entry["tetris"].release_movement()
                            pause_snapshot = self.screen.copy()
                            self.audio.play("pause")
                        else:
                            self.renderer.drawByName("gamescreen", 0, 0)
                        continue
                    if event.key == pygame.K_F1:
                        if show_help:
                            paused = paused_before_help
                            show_help = False
                            self.audio.pause_music(paused)
                            if not paused:
                                self.renderer.drawByName("gamescreen", 0, 0)
                        else:
                            paused_before_help = paused
                            pause_snapshot = self.screen.copy()
                            paused = True
                            show_help = True
                            for entry in entries:
                                entry["tetris"].release_movement()
                            self.audio.pause_music(True)
                        continue
                if not paused or event.type == pygame.KEYUP:
                    # KEYUP must also be processed while paused; otherwise
                    # one-shot actions remain stuck when a key is released.
                    for entry in entries:
                        entry["tetris"].trigger(event)

            # SDL delivers keyboard events only to the focused window.
            # When another app owns the keyboard, visibly pause instead of
            # silently ignoring movement while gravity keeps running.
            focused = self._keyboard_focused()
            if not focused:
                if not focus_lost:
                    focus_snapshot = self.screen.copy()
                    for entry in entries:
                        entry["tetris"].release_movement()
                    focus_lost = True
                if hasattr(self, "_focus_overlay"):
                    self._focus_overlay(focus_snapshot)
                else:
                    self.clock.tick(FPS)
                continue
            if focus_lost:
                focus_lost = False
                keyboard_mode = getattr(self, "_keyboard_mode", None)
                if keyboard_mode is not None:
                    keyboard_mode.refresh()
                self.renderer.drawByName("gamescreen", 0, 0)
            if paused:
                self._pause_overlay(pause_snapshot, show_help)
                continue

            # KEYDOWN can be consumed by map selection, by OS focus changes,
            # or dropped under load. Synchronize EVERY bound physical key,
            # not just Space. One-shot actions remain edge-triggered.
            pressed_api = getattr(pygame.key, "get_pressed", None)
            if pressed_api is not None:
                physical_keys = pressed_api()
                for entry in entries:
                    entry["tetris"].sync_pressed_keys(physical_keys)

            # Input (especially HOLD) may spawn a piece straight into an
            # occupied board. Do not continue advancing a blocked piece.
            if self._topout_result(entries) is not None:
                return self._finish_on_topout(entries)

            for entry in entries:
                tetris = entry["tetris"]
                tetris.natural_down()
                tetris.move(previous_frame_ms)

            # Buffer attacks until all players finish the frame so that the
            # player processed second is not unfairly able to cancel first.
            pending_attacks = [0] * len(entries)
            for i, entry in enumerate(entries):
                tetris, pos = entry["tetris"], entry["pos"]
                if tetris.check_fallen():
                    scores = tetris.clear()
                    outgoing = tetris.attack_outgoing
                    if self.num_players == 2 and outgoing > 0:
                        pending_attacks[1 - i] += outgoing
                        self._game_event("attack", i, tetris)
                    self.renderer.drawCombo(tetris, *pos["combo"])
                    self.renderer.drawTetris(tetris, *pos["tetris"])
                    self.renderer.drawTspin(tetris, *pos["tspin"])
                    self.renderer.drawBack2Back(tetris, *pos["back2back"])

                    if self.num_players == 1:
                        self._record_single_stats(tetris, scores)
                    # Check a lock/garbage overflow BEFORE spawning the next
                    # piece, and check the new spawn position afterward.
                    if not tetris.check_KO():
                        tetris.new_block()

                self.renderer.drawGameScreen(tetris)
                tetris.increment_timer()
                if self.num_players == 2:
                    pygame.draw.rect(self.screen, (30, 30, 30), pos["attack_clean"])
                    for j in range(tetris.attacked):
                        ax, ay, aw, ah = pos["attack_alarm"]
                        pygame.draw.rect(self.screen, (255, 0, 0), (ax, ay - 18 * j, aw, ah))
                    if tetris.KO > 0:
                        self.renderer.drawKO(tetris.KO, *pos["big_ko"])
                self.renderer.drawScreen(tetris, *pos["drawscreen"])

            for i, amount in enumerate(pending_attacks):
                if amount:
                    entries[i]["tetris"].add_attacked(amount)

            if self.num_players == 1:
                self.renderer.drawByName("transparent", *POS_LIST[1]["transparent"])

            remaining_ms = self.update_time(remaining_ms)
            self.renderer.drawTime2p(remaining_ms)
            if hasattr(self.renderer, "draw_facebook_brand"):
                self.renderer.draw_facebook_brand()
            visual = getattr(self.renderer, "visuals", None)
            if visual is not None and hasattr(visual, "snapshot") and visual.enabled:
                skins = visual.snapshot()
                self._panel(438, 15, 238, 31, 195)
                self._text("SKINS {} / {} / {}".format(
                    skins["mino"].upper(), skins["ghost"].upper(), skins["bomb"].upper()),
                    445, 21, font=self._small_font)
            if hasattr(self, "_draw_status") and getattr(self, "_small_font", None) is not None:
                self._draw_status(entries)
            engine = getattr(self, "effects", None)
            if engine is not None and engine.enabled:
                for entry in entries:
                    tetris = entry["tetris"]
                engine.tick()
                engine.draw(self.screen)
            layout_name = ("CUSTOM" if getattr(self, "keymap", None) else
                           str(getattr(self, "controls", "classic")).upper())
            help_note = ("1P {} | SPACE hard drop | F1 keys | P pause".format(layout_name)
                         if self.num_players == 1 else
                         "2P: P1 arrows/SPACE | P2 H/J/K/W | F1 help")
            visual = getattr(getattr(self, "renderer", None), "visuals", None)
            if visual is not None and getattr(visual, "enabled", False):
                help_note = help_note + " | F5 mino / F6 ghost / F7 bomb / F8 original ON"
            else:
                help_note = help_note + " | F5/F6/F7 skins, F8 toggle"
            self._footnote(help_note)
            if getattr(self, "debug_input", False):
                self._text("INPUT {} | focus {}".format(
                    getattr(self, "_last_input", "none"),
                    "YES" if self._keyboard_focused() else "NO"),
                    15, 17, color=(255, 210, 110), font=self._small_font)
            pygame.display.flip()
            previous_frame_ms = self.clock.tick(FPS)

            # First top-out ends a two-player match in this playable edition.
            # Also handles both players reaching the top in one update (draw).
            finished = self._finish_on_topout(entries) if self._topout_result(entries) is not None else None
            if finished is not None:
                return finished
            if remaining_ms <= 0:
                if self.num_players == 2:
                    winner = Judge.who_win(entries[0]["tetris"], entries[1]["tetris"])
                    return self._end_match(entries, winner=winner)
                return self._end_match(entries)


class TetrisGameDouble(TetrisGame):
    def __init__(self, **kwargs):
        super().__init__(mode="double", **kwargs)


class TetrisGameSingle(TetrisGame):
    def __init__(self, **kwargs):
        super().__init__(mode="single", **kwargs)


def parser():
    argparser = argparse.ArgumentParser(description="TetrisBattle: keyboard and audio edition")
    argparser.add_argument("--mode", choices=("single", "double"), default="single")
    argparser.add_argument("--map", choices=MAP_NAMES, dest="start_map", default=None,
                           help="Immediately start a match on this map, skipping the chooser")
    argparser.add_argument("--debug-input", action="store_true",
                           help="Print real KEYDOWN/KEYUP events and keyboard focus to the terminal")
    argparser.add_argument("--controls", choices=("classic", "wasd"), default="classic",
                           help="Single-player keyboard preset (double uses original keys)")
    argparser.add_argument("--keymap", metavar="FILE", help="Optional JSON control overrides")
    argparser.add_argument("--no-audio", action="store_true", help="Disable music and sound effects")
    argparser.add_argument("--sfx-pack", default="auto", metavar="NAME",
                           help="Recorded SFX bank (auto uses active_pack.json, original uses bundled sounds)")
    argparser.add_argument("--no-effects", action="store_true", help="Disable particle effects and flashes")
    argparser.add_argument("--mino-skin", choices=("classic", "default", "neon", "legacy"), default="classic",
                           help="Source SWF mino graphics (legacy = old project graphics)")
    argparser.add_argument("--ghost-skin", choices=("outline", "shadow", "ghost", "legacy"), default="outline")
    argparser.add_argument("--bomb-skin", choices=("bomb", "thunder", "smiley", "legacy"), default="bomb")
    argparser.add_argument("--no-original-visuals", action="store_true", help="Disable original graphics + logo and use old tiles")
    argparser.add_argument("--no-bombs", action="store_true", help="Disable bombs for classic play")
    argparser.add_argument("--das-ms", type=float, default=120.0,
                           help="Wait before held horizontal movement starts repeating (0-500ms)")
    argparser.add_argument("--arr-ms", type=float, default=25.0,
                           help="Held horizontal movement repeat period (1-250ms)")
    argparser.add_argument("--soft-drop-ms", type=float, default=30.0,
                           help="Held soft-drop repeat period (1-250ms)")
    argparser.add_argument("--music-volume", type=float, default=0.30, metavar="0..1")
    argparser.add_argument("--sfx-volume", type=float, default=0.55, metavar="0..1")
    return argparser.parse_args()


if __name__ == "__main__":
    args = parser()
    if args.mode == "double" and args.controls == "wasd":
        raise SystemExit("--controls wasd is single-player only; use --keymap for double-player overrides")
    options = {
        "controls": args.controls,
        "keymap": args.keymap,
        "audio": not args.no_audio,
        "effects": not args.no_effects,
        "bombs": not args.no_bombs,
        "music_volume": args.music_volume,
        "sfx_volume": args.sfx_volume,
        "sfx_pack": args.sfx_pack,
        "das_ms": args.das_ms,
        "arr_ms": args.arr_ms,
        "soft_drop_ms": args.soft_drop_ms,
        "debug_input": args.debug_input,
        "start_map": args.start_map,
        "mino_skin": args.mino_skin,
        "ghost_skin": args.ghost_skin,
        "bomb_skin": args.bomb_skin,
        "original_visuals": not args.no_original_visuals,
    }
    try:
        game = TetrisGameSingle(**options) if args.mode == "single" else TetrisGameDouble(**options)
    except (ValueError, OSError) as exc:
        raise SystemExit("Invalid TetrisBattle configuration: {}".format(exc))
    game.play()

"""Keyboard layouts for the human-playable game.

The AI/gym interface continues to use its original integer action IDs.
"""
import json
from pathlib import Path

import pygame

ACTIONS = ("left", "right", "down", "rotate_right", "rotate_left", "drop", "hold")

# Original key assignments remain present. Additional keys only complement them.
CLASSIC_P1 = {
    "left": ["left"], "right": ["right"], "down": ["down"],
    "rotate_right": ["up", "x"], "rotate_left": ["z"],
    "drop": ["space"], "hold": ["c", "left shift"],
}
CLASSIC_P2 = {
    "left": ["h"], "right": ["k"], "down": ["j"],
    "rotate_right": ["u", "i"], "rotate_left": ["q"],
    "drop": ["w"], "hold": ["e"],
}
WASD_P1 = {
    "left": ["a"], "right": ["d"], "down": ["s"],
    "rotate_right": ["w", "x"], "rotate_left": ["z", "q"],
    "drop": ["space"], "hold": ["c", "left shift"],
}

# Global shortcuts are handled separately to keep players' bindings unambiguous.
RESERVED = {
    pygame.K_ESCAPE, pygame.K_p, pygame.K_r, pygame.K_F1, pygame.K_F3, pygame.K_F4, pygame.K_TAB,
    pygame.K_F2, pygame.K_m, pygame.K_n, pygame.K_MINUS,
    pygame.K_EQUALS, pygame.K_KP_PLUS, pygame.K_KP_MINUS,
}


def _to_keycode(key):
    if not isinstance(key, str) or not key.strip():
        raise ValueError("Key names must be nonempty strings")
    try:
        return pygame.key.key_code(key.strip().lower())
    except (ValueError, AttributeError) as exc:
        raise ValueError("Unknown pygame key name: {!r}".format(key)) from exc


def _read_config(path):
    if not path:
        return {}
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("The keymap JSON must be an object")
    return data


def load_keymaps(mode, preset="classic", config_path=None):
    """Return a list of player dictionaries with integer or tuple key bindings.

    Custom JSON may provide partial overrides in ``single.p1`` or
    ``double.p1``/``double.p2``. Duplicate keys and global shortcut collisions
    are reported explicitly instead of silently stealing another player's keys.
    """
    if mode not in ("single", "double"):
        raise ValueError("Mode must be 'single' or 'double'")
    if preset not in ("classic", "wasd"):
        raise ValueError("Unknown controls preset: {}".format(preset))
    if mode == "double" and preset == "wasd":
        raise ValueError("The WASD preset is for single-player only; use --keymap for doubles")

    defaults = [dict(CLASSIC_P1 if preset == "classic" else WASD_P1)]
    if mode == "double":
        defaults.append(dict(CLASSIC_P2))
    config = _read_config(config_path)
    section = config.get(mode, {})
    if not isinstance(section, dict):
        raise ValueError("'{}' must be a JSON object".format(mode))

    maps = []
    used = {}
    for index, default in enumerate(defaults):
        player_name = "p{}".format(index + 1)
        overrides = section.get(player_name, {})
        if not isinstance(overrides, dict):
            raise ValueError("{}.{} must be an object".format(mode, player_name))
        unknown = set(overrides) - set(ACTIONS)
        if unknown:
            raise ValueError("Invalid action(s): {}".format(", ".join(sorted(unknown))))
        bindings = {**default, **overrides}
        out = {"id": index}
        for action in ACTIONS:
            raw = bindings[action]
            if isinstance(raw, str):
                raw = [raw]
            if not isinstance(raw, list) or not raw:
                raise ValueError("{}.{} requires one or more key names".format(player_name, action))
            keys = tuple(dict.fromkeys(_to_keycode(item) for item in raw))
            # Required single-player invariant, even with custom JSON overrides.
            if mode == "single" and action == "drop":
                keys = tuple(dict.fromkeys((pygame.K_SPACE,) + keys))
            for code in keys:
                if code in RESERVED:
                    raise ValueError("{} ({}) uses a reserved shortcut".format(player_name, pygame.key.name(code)))
                if code in used:
                    raise ValueError("Key {!r} assigned to both {} and {}.{}".format(
                        pygame.key.name(code), used[code], player_name, action))
                used[code] = "{}.{}".format(player_name, action)
            out[action] = keys if len(keys) > 1 else keys[0]
        maps.append(out)
    return maps


def describe_keymaps(maps):
    """Human-readable lines suitable for a Pygame overlay."""
    labels = {
        "left": "Move left", "right": "Move right", "down": "Soft drop",
        "rotate_right": "Rotate CW", "rotate_left": "Rotate CCW",
        "drop": "Hard drop", "hold": "Hold piece",
    }
    descriptions = []
    for player in maps:
        lines = ["PLAYER {}".format(player["id"] + 1)]
        for action in ACTIONS:
            binding = player[action]
            keys = binding if isinstance(binding, (list, tuple)) else (binding,)
            names = " / ".join(pygame.key.name(code).upper() for code in keys)
            lines.append("{}: {}".format(labels[action], names))
        descriptions.append(lines)
    return descriptions

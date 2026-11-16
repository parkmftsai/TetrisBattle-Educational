#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
exec python3 -m game.tetris_game --mode double --map none

@echo off
cd /d "%~dp0"
python -m game.tetris_game --mode double --map none
if errorlevel 1 pause

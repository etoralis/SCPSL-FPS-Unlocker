@echo off
title SCPSL FPS Unlocker
python "%~dp0main.py" %*
if errorlevel 1 (
    echo.
    echo Error: Python 3.10+ is required.
    echo Download from https://www.python.org/downloads/
    pause
)

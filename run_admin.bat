@echo off
title SCPSL FPS Unlocker (Admin)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && python main.py %*' -Verb RunAs"
    exit /b
)
python "%~dp0main.py" %*
pause

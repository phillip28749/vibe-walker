@echo off
REM Vibe Walker Launcher - Prevents multiple instances

echo Checking for existing Vibe Walker instances...
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq Vibe Walker*" >nul 2>&1

echo Starting Vibe Walker...
cd /d "%~dp0src"
start "Vibe Walker" pythonw.exe main.py

echo Vibe Walker started!
echo Check your taskbar for the walking character.
echo.
echo To stop: Run stop_vibewalker.bat
pause

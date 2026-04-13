@echo off
REM Vibe Walker - Activity-based launcher

echo Starting Vibe Walker (Activity Monitor)...
cd /d "%~dp0"

REM Use virtual environment Python
start "Vibe Walker" .venv\Scripts\pythonw.exe src\main.py

echo.
echo Vibe Walker is now running!
echo The character will appear when Claude Code is actively working.
echo.
echo To stop: Run stop.bat or close this window
timeout /t 3

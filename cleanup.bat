@echo off
REM Manual cleanup script for Vibe Walker orphaned queries
cd /d "%~dp0"
.venv\Scripts\python.exe cleanup_orphaned_queries.py
pause

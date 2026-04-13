@echo off
REM Stop Vibe Walker

echo Stopping all Vibe Walker instances...
taskkill /F /FI "WINDOWTITLE eq Vibe Walker*" >nul 2>&1

REM Also stop any python.exe running main.py
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr /B "PID:"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /I "main.py" >nul
    if not errorlevel 1 (
        taskkill /F /PID %%a >nul 2>&1
        echo Stopped process %%a
    )
)

echo All Vibe Walker instances stopped!
pause

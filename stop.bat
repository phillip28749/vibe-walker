@echo off
REM Stop Vibe Walker

echo Stopping Vibe Walker...

REM Kill pythonw.exe processes running from .venv
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO LIST ^| findstr /B "PID:"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /I "vibe-walker" >nul
    if not errorlevel 1 (
        taskkill /F /PID %%a >nul 2>&1
        echo Stopped Vibe Walker (PID: %%a)
    )
)

REM Also check python.exe
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr /B "PID:"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /I "vibe-walker" >nul
    if not errorlevel 1 (
        taskkill /F /PID %%a >nul 2>&1
        echo Stopped Vibe Walker (PID: %%a)
    )
)

echo Done!
timeout /t 2

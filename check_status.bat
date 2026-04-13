@echo off
REM Check if Vibe Walker is running

echo Checking Vibe Walker status...
echo.

set FOUND=0
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| findstr /B "PID:"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr /I "main.py" >nul
    if not errorlevel 1 (
        echo [RUNNING] Vibe Walker instance found (PID: %%a^)
        set FOUND=1
    )
)

if %FOUND%==0 (
    echo [STOPPED] No Vibe Walker instances running
)

echo.
pause

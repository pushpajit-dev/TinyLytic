@echo off
title TinyLytic Studio - Pre-Flight Check and Launcher
cd /d "%~dp0"

echo ======================================================================
echo           TinyLytic Studio - Pre-Flight Verification and Runner        
echo ======================================================================
echo.

:: 1. Check for Python
echo [*] Checking Python installation...
set PY_EXE=
python --version >nul 2>&1
if not errorlevel 1 (
    set PY_EXE=python
    goto found_python
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set PY_EXE=py -3
    goto found_python
)

echo.
echo [X] ERROR: Python was not detected on your system.
echo     Please install Python 3.10+ from https://www.python.org/downloads/
echo     CRITICAL: Check the box "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:found_python
echo [OK] Using Python:
%PY_EXE% --version
echo.

:: 2. Check and install core dependencies
echo [*] Checking runtime dependencies...
%PY_EXE% -c "import PyQt6, pyperclip, sounddevice, soundfile, whisper, torch, yt_dlp, cv2, requests, psutil" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [!] Missing dependencies detected.
    echo [*] Installing required packages via pip...
    %PY_EXE% -m pip install -r requirements.txt
    echo.
) else (
    echo [OK] All core dependencies verified and ready!
)

echo.
echo ======================================================================
echo  [OK] Pre-flight checks passed! Starting TinyLytic Studio...
echo ======================================================================
echo.

%PY_EXE% "Tinylytic.py"

echo.
echo ======================================================================
echo  TinyLytic Studio session has ended.
echo ======================================================================
pause

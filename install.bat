@echo off
title TinyLytic Studio - Setup and Installation
cd /d "%~dp0"

echo ======================================================================
echo          TinyLytic Studio - Intelligent Installation Setup           
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

:: 2. Launch Setup Wizard GUI
echo [*] Launching Setup Wizard...
%PY_EXE% "installer_wizard.py"

if errorlevel 1 (
    echo.
    echo [!] Setup Wizard exited with code %errorlevel%.
)
echo.
pause

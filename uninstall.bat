@echo off
title TinyLytic Studio - Clean Uninstaller
cd /d "%~dp0"

echo ======================================================================
echo              TinyLytic Studio - Uninstaller Launcher                 
echo ======================================================================
echo.

set PY_EXE=python
python --version >nul 2>&1
if not errorlevel 1 goto run_uninstaller

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set PY_EXE=py -3
    goto run_uninstaller
)

echo [X] Python was not found to execute the uninstaller script.
echo Attempting direct removal via PowerShell...
powershell -NoProfile -Command "Remove-Item -Path '%~dp0' -Recurse -Force"
exit /b 0

:run_uninstaller
%PY_EXE% "uninstaller.py"

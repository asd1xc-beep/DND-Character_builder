@echo off
setlocal
title D&D Character Builder Setup
cd /d "%~dp0"

echo D&D Character Builder first-time setup
echo.
echo This will create a local .venv folder and install the required Python packages.
echo You only need to run this once on a new computer.
echo.

if not exist "requirements.txt" (
    echo Could not find requirements.txt in this folder.
    echo Make sure you extracted the whole zip before running setup.
    echo.
    pause
    exit /b 1
)

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 goto no_python
    set "PYTHON_CMD=python"
)

echo Using Python:
%PYTHON_CMD% --version
if errorlevel 1 goto no_python
echo.

echo Creating local app environment...
%PYTHON_CMD% -m venv ".venv"
if errorlevel 1 goto setup_failed

echo.
echo Updating installer tools...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto setup_failed

echo.
echo Installing app requirements...
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto setup_failed

echo.
echo Setup complete.
echo You can now double-click "Start Character Builder.cmd" to run the app.
echo.
pause
exit /b 0

:no_python
echo Python was not found on this computer.
echo Install Python 3.11 or newer from https://www.python.org/downloads/
echo During installation, check the box that says "Add python.exe to PATH".
echo Then run this setup file again.
echo.
pause
exit /b 1

:setup_failed
echo.
echo Setup did not finish successfully.
echo Check the messages above, then try running this setup file again.
echo.
pause
exit /b 1

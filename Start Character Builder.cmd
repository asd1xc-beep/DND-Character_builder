@echo off
setlocal
title D&D Character Builder
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Could not find the project virtual environment.
    echo Expected: .venv\Scripts\python.exe
    echo.
    echo If this is a new computer, double-click "Setup First Time.cmd" first.
    echo After setup finishes, run this start shortcut again.
    pause
    exit /b 1
)

echo Starting D&D Character Builder...
echo.
echo Keep this window open while using the app.
echo Close this window when you want to stop it.
echo.

".venv\Scripts\python.exe" -m streamlit run "app.py" --server.headless false

if errorlevel 1 (
    echo.
    echo The app stopped because of an error.
    pause
)

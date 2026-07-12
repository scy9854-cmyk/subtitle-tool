@echo off
cd /d %~dp0

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERROR] python was not found on PATH.
  echo Reinstall from https://www.python.org/downloads/ and check
  echo "Add python.exe to PATH" during setup, then open a NEW terminal
  echo and run this script again.
  echo.
  pause
  exit /b 1
)

echo Installing dependencies (first run only, takes a minute)...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] pip install failed. See the error above.
  pause
  exit /b 1
)

echo Starting server...
start "" cmd /c "timeout /t 2 /nobreak >nul && start "" http://localhost:5050"
python app.py

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

echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] pip install -r requirements.txt failed. See the error above.
  pause
  exit /b 1
)
python -m pip install -r requirements-desktop.txt
if errorlevel 1 (
  echo.
  echo [ERROR] pip install -r requirements-desktop.txt failed. See the error above.
  pause
  exit /b 1
)

echo.
echo Building subtitle-tool.exe (this can take a minute)...
python -m PyInstaller --onefile --name subtitle-tool ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  desktop.py
if errorlevel 1 (
  echo.
  echo [ERROR] PyInstaller build failed. See the error above.
  pause
  exit /b 1
)

echo.
echo Done. dist\subtitle-tool.exe is ready.
echo Copy your .env file (with ANTHROPIC_API_KEY) into the dist folder next to it.
pause

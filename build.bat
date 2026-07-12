@echo off
cd /d %~dp0

echo Installing dependencies...
pip install -r requirements.txt
pip install -r requirements-desktop.txt

echo.
echo Building subtitle-tool.exe (this can take a minute)...
pyinstaller --onefile --name subtitle-tool ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  desktop.py

echo.
echo Done. dist\subtitle-tool.exe is ready.
echo Copy your .env file (with ANTHROPIC_API_KEY) into the dist folder next to it.
pause

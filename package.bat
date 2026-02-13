@echo off
echo [INFO] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo [INFO] Cleaning up old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MistakeReservoir.spec del MistakeReservoir.spec

echo [INFO] Converting icon...
python -c "from PIL import Image; Image.open('approved.png').save('approved.ico', format='ICO', sizes=[(256, 256)])"

echo [INFO] Starting PyInstaller build...
pyinstaller --noconfirm --noconsole --onefile --name "MistakeReservoir" --icon "approved.ico" --add-data "static;static" --add-data "approved.png;." main.py

echo [INFO] Build complete! Executable is located in the 'dist' folder.
pause

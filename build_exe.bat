@echo off
title Diktat - Standalone EXE Derleyici
cd /d "%~dp0"

echo ========================================================
echo   Diktat - Standalone EXE Olusturucu (PyInstaller)
echo ========================================================
echo.
python -m pip install pyinstaller

echo.
echo Derleme basliyor...
python -m PyInstaller --noconfirm --onefile --windowed --name "Diktat" ^
    --icon="icon.ico" ^
    --exclude-module PyQt5 ^
    --exclude-module matplotlib ^
    --exclude-module tkinter ^
    --exclude-module pygame ^
    --add-data ".env;." ^
    --add-data "icon.ico;." ^
    --add-data "icon.png;." ^
    diktat.py

echo.
echo Derleme tamamlandi! 
echo Cikti: 'dist/Diktat.exe'
pause

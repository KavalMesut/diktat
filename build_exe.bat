@echo off
title Dictator - Standalone EXE Derleyici
cd /d "%~dp0"

echo ========================================================
echo   Dictator - Standalone EXE Olusturucu (PyInstaller)
echo ========================================================
echo.
python -m pip install pyinstaller

echo.
echo Derleme basliyor...
python -m PyInstaller --noconfirm --onefile --windowed --name "Dictator" ^
    --icon="icon.ico" ^
    --exclude-module PyQt5 ^
    --exclude-module matplotlib ^
    --exclude-module tkinter ^
    --exclude-module pygame ^
    --add-data ".env;." ^
    --add-data "icon.ico;." ^
    --add-data "icon.png;." ^
    dictator.py

echo.
echo Derleme tamamlandi! 
echo Cikti: 'dist/Dictator.exe'
pause

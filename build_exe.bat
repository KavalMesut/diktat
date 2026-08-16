@echo off
title Diktat - Standalone EXE Derleyici
cd /d "%~dp0"

echo ========================================================
echo   Diktat - Standalone EXE Olusturucu (PyInstaller)
echo ========================================================
echo.

echo Derleme basliyor...
python -m PyInstaller --noconfirm Diktat.spec

echo.
echo Derleme tamamlandi! 
echo Cikti: 'dist/Diktat.exe'
pause

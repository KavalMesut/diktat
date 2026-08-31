@echo off
title Diktat - Standalone EXE Derleyici
cd /d "%~dp0"

echo ========================================================
echo   Diktat - Standalone EXE Olusturucu (PyInstaller)
echo ========================================================
echo.

echo Derleme basliyor (Gecici dosyalar %%TEMP%% altinda olusturuluyor)...
python -m PyInstaller --noconfirm --workpath "%TEMP%\diktat_build" Diktat.spec

echo.
echo Derleme tamamlandi! 
echo Cikti: 'dist/Diktat.exe'
pause

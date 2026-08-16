@echo off
title Diktat - AI Voice Dictation
cd /d "%~dp0"

echo ========================================================
echo   Diktat - AI Sesli Diktat Asistani
echo ========================================================
echo.
echo Diktat arkaplanda hazir bekliyor...
echo Kisayol: [Ctrl + Space]
echo Iptal:   [Ctrl + Alt + Space]
echo.
python diktat.py
pause

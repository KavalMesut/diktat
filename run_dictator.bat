@echo off
title Dictator - AI Voice Dictation
cd /d "%~dp0"

echo ========================================================
echo   Dictator - AI Sesli Dikte Asistani
echo ========================================================
echo.
echo Dictator arkaplanda calisiyor...
echo Kisayol: [Ctrl + Space]
echo Iptal:   [Ctrl + Alt + Space]
echo.
python dictator.py
pause

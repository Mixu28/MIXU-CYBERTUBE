@echo off
setlocal
cd /d "%~dp0"
if not exist ".tmp" mkdir ".tmp"
set "TEMP=%~dp0.tmp"
set "TMP=%TEMP%"
py -3 gui.py %*
set "FIX08_EXIT=%ERRORLEVEL%"
if not "%FIX08_EXIT%"=="0" pause
exit /b %FIX08_EXIT%

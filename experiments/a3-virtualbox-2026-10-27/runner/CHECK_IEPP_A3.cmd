@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0IEPP_A3_Launcher.ps1" -CheckOnly
endlocal

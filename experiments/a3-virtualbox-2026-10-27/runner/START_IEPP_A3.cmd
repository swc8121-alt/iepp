@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0IEPP_A3_Launcher.ps1"
if errorlevel 1 (
  echo.
  echo The IEPP A3 run did not complete. The error record is in IEPP_A3_LAST_ERROR.txt.
  pause
)
endlocal

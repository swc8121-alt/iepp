@echo off
chcp 65001 >nul
title IEPP L2 Preflight
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0IEPP_L2_Launcher.ps1" -CheckOnly
if errorlevel 1 pause

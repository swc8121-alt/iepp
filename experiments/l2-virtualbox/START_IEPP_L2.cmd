@echo off
chcp 65001 >nul
title IEPP L2 VirtualBox 22-Trial Batch
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0IEPP_L2_Launcher.ps1"
if errorlevel 1 pause

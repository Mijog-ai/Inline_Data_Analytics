@echo off
rem Inline Data Analytics auf diesem PC installieren (ohne Administratorrechte). / Install Inline Data Analytics on this PC (no admin rights).
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0install.ps1"

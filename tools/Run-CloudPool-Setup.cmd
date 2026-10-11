@echo off
setlocal
PowerShell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-ElectronicBrain-CloudPool.ps1" %*
set "rc=%errorlevel%"
if not "%rc%"=="0" echo Setup failed. Inspect C:\Brain\logs.
if not "%rc%"=="0" pause
exit /b %rc%

@echo off
rem Double-click to start ai-partner on Windows.
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py start.py %*
) else (
  python start.py %*
)
pause

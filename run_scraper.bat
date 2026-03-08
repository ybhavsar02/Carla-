@echo off
setlocal

set "PY_EXE=%USERPROFILE%\anaconda3\python.exe"
if not exist "%PY_EXE%" (
  echo ERROR: Python not found at "%PY_EXE%"
  exit /b 1
)

cd /d "%~dp0"
"%PY_EXE%" scraper.py >> data\scheduler.log 2>&1
exit /b %errorlevel%


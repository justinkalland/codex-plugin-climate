@echo off
setlocal
set "SCRIPT_DIR=%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 "%SCRIPT_DIR%climate.py" %*
  exit /b %ERRORLEVEL%
)

where python3 >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python3 "%SCRIPT_DIR%climate.py" %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%SCRIPT_DIR%climate.py" %*
  exit /b %ERRORLEVEL%
)

echo Climate requires Python 3.10 or newer. Install Python 3 and try again. 1>&2
exit /b 1

@echo off
setlocal
set "BACKEND_DIR=%~dp0"
set "PYTHON_EXE=%BACKEND_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo Virtual environment interpreter not found: "%PYTHON_EXE%"
  exit /b 1
)

pushd "%BACKEND_DIR%"
"%PYTHON_EXE%" app.py
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%

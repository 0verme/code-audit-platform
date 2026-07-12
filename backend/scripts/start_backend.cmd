@echo off
setlocal
for %%I in ("%~dp0..") do set "BACKEND_DIR=%%~fI"
set "PYTHON_EXE=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "LOG_DIR=%BACKEND_DIR%\logs"
set "STDOUT_LOG=%LOG_DIR%\backend.log"
set "STDERR_LOG=%LOG_DIR%\backend.err.log"

if not exist "%PYTHON_EXE%" (
  echo Virtual environment interpreter not found: "%PYTHON_EXE%"
  exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

pushd "%BACKEND_DIR%"
echo Starting backend; backend\.env is loaded automatically when present.
"%PYTHON_EXE%" -u app.py 1>> "%STDOUT_LOG%" 2>> "%STDERR_LOG%"
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%

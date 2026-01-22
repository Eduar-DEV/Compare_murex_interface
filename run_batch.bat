@echo off
setlocal

REM Configuration
set DIR_A=tests\batch_data\server_a
set DIR_B=tests\batch_data\server_b
set OUTPUT_DIR=results
set CONFIG_FILE=batch_config.json

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if uv is available
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 'uv' tool is not installed or not in PATH.
    echo Please install it: pip install uv
    pause
    exit /b 1
)

echo ===================================================
echo   Murex Batch Comparator (Windows Wrapper)
echo ===================================================
echo Source A: %DIR_A%
echo Source B: %DIR_B%
echo Output  : %OUTPUT_DIR%
echo Config  : %CONFIG_FILE%
echo ===================================================

REM Install dependencies if needed (implicit in uv run, but sync is good practice)
echo [INFO] Syncing environment...
uv sync

REM Run Orchestrator
echo [INFO] Starting Batch Process...
uv run src/batch/orchestrator.py --dir-a "%DIR_A%" --dir-b "%DIR_B%" --output "%OUTPUT_DIR%" --config "%CONFIG_FILE%"

if %errorlevel% neq 0 (
    echo [ERROR] Batch process encountered an issue. Check logs.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Batch Process Completed.
pause
endlocal

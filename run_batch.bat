@echo off
setlocal

REM Ir a la carpeta del .bat (raíz del proyecto)
cd /d "%~dp0"

REM Configuration
set "DIR_A=tests\batch_data\server_a"
set "DIR_B=tests\batch_data\server_b"
set "OUTPUT_DIR=results"
set "CONFIG_FILE=batch_config.json"
set "SEPARATOR="

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
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

echo [INFO] Syncing environment...
uv sync


echo [INFO] Validate headers...
if "%SEPARATOR%"=="" (
    uv run -m src.batch.validate_headers --dir-a "%DIR_A%" --dir-b "%DIR_B%" --output "%OUTPUT_DIR%" --config "%CONFIG_FILE%"
) else (
    uv run -m src.batch.validate_headers --dir-a "%DIR_A%" --dir-b "%DIR_B%" --output "%OUTPUT_DIR%" --config "%CONFIG_FILE%" --separator "%SEPARATOR%"
)

echo [INFO] Starting Batch Process...
if "%SEPARATOR%"=="" (
    uv run -m src.batch.orchestrator --dir-a "%DIR_A%" --dir-b "%DIR_B%" --output "%OUTPUT_DIR%" --config "%CONFIG_FILE%"
) else (
    uv run -m src.batch.orchestrator --dir-a "%DIR_A%" --dir-b "%DIR_B%" --output "%OUTPUT_DIR%" --config "%CONFIG_FILE%" --separator "%SEPARATOR%"
)

if %errorlevel% neq 0 (
    echo [ERROR] Batch process encountered an issue. Check logs.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Batch Process Completed.
pause
endlocal

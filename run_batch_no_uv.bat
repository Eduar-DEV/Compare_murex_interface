@echo off
setlocal EnableExtensions

REM --- Ir a la raíz del proyecto (carpeta donde está este .bat)
cd /d "%~dp0"

REM --- Configuración
set "DIR_A=tests\batch_data\server_a"
set "DIR_B=tests\batch_data\server_b"
set "OUTPUT_DIR=results"
set "CONFIG_FILE=batch_config.json"

echo ===================================================
echo   Murex Batch Comparator (No UV)
echo ===================================================
echo Source A: %DIR_A%
echo Source B: %DIR_B%
echo Output  : %OUTPUT_DIR%
echo Config  : %CONFIG_FILE%
echo ===================================================

REM --- Validar estructura mínima
if not exist "src\batch\orchestrator.py" (
    echo [ERROR] No se encontró src\batch\orchestrator.py. Ejecuta este .bat desde la raíz del proyecto.
    pause
    exit /b 1
)

REM --- Elegir intérprete Python (prioridad: .venv -> venv -> py -3 -> python)
set "PY_EXE="

if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
) else (
    where py >nul 2>&1
    if %errorlevel%==0 (
        set "PY_EXE=py -3"
    ) else (
        where python >nul 2>&1
        if %errorlevel%==0 (
            set "PY_EXE=python"
        )
    )
)

if "%PY_EXE%"=="" (
    echo [ERROR] No se encontró Python. Instala Python 3 o agrega python/py al PATH.
    echo         Descarga: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM --- Ejecutar como módulo para que funcionen imports "from src..."
%PY_EXE% -m src.batch.orchestrator --dir-a "%DIR_A%" --dir-b "%DIR_B%" --output "%OUTPUT_DIR%" --config "%CONFIG_FILE%"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] El proceso falló. Revisa logs/salida.
    echo         (Tip: si falta alguna libreria, debes instalar dependencias en el Python/venv que se está usando)
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Batch Process Completed.
pause
endlocal



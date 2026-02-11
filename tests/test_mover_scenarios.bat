@echo off
echo ==========================================
echo 1. Generando datos de prueba limpios...
echo ==========================================
uv run tests/generate_mover_test_data.py

echo.
echo ==========================================
echo 2. Escenario A: Copiar solo .csv y .json (Keep Structure)
echo ==========================================
echo Origen: tests/mover_test_data/input
echo Destino: tests/mover_test_data/output_A_copy
echo Extensiones: .csv .json
echo.
uv run mover_archivos_v3.py "tests/mover_test_data/input" "tests/mover_test_data/output_A_copy" --mode copy --extensions .csv .json --keep-structure

echo.
echo ==========================================
echo 3. Escenario B: Mover TODO (incluyendo sufijos raros)
echo ==========================================
echo Origen: tests/mover_test_data/input
echo Destino: tests/mover_test_data/output_B_move
echo Nota: Esto vaciara la carpeta input de los archivos validos.
echo.
uv run mover_archivos_v3.py "tests/mover_test_data/input" "tests/mover_test_data/output_B_move" --mode move --extensions .csv .txt .json .xlsx .xml

echo.
echo ==========================================
echo 4. Verificando resultados...
echo ==========================================
dir tests\mover_test_data\output_A_copy /s /b
echo.
echo ---
echo.
dir tests\mover_test_data\output_B_move /s /b
echo.
echo Test finalizado.
pause

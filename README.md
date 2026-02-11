# Comparador de CSVs (Murex Python Project)

Herramienta de línea de comandos robusta para comparar archivos CSV, diseñada para validar cabeceras, registros y manejar comparaciones complejas basadas en llaves (keys), incluso con datos desordenados o errores mixtos.

## Arquitectura del Proyecto

El proyecto sigue una estructura modular para facilitar la mantenibilidad y escalabilidad:

```text
.
├── main.py                     # Punto de entrada (Orquestador CLI)
├── src/
│   ├── core/
│   │   └── comparator.py       # Lógica central (Clase CSVComparator)
│   └── reporting/
│       ├── console_reporter.py # Lógica de impresión en consola
│       └── json_reporter.py    # Lógica de generación de reportes JSON
├── tests/
│   └── data/                   # Datos de prueba (CSV generados)
└── results/                    # Salida de reportes JSON (nombre + timestamp)
```

### Funciones Principales

**`src/core/comparator.py` - Clase `CSVComparator`**
- `__init__(file1, file2, key_column)`: Inicializa el comparador. Si se provee `key_column`, activa el modo lógico (key-based).
- `validate_headers()`: Verifica la cantidad y nombres de columnas. Es resiliente: reporta errores pero permite continuar (si `run_comparison` lo decide) salvo que falte la llave.
- `compare_records()`: Método fachada que decide si usar comparación posicional o por llave.
- `_compare_with_key()`: Realiza "outer joins" para identificar registros faltantes/extra y compara celdas en registros comunes. Maneja intersección de columnas para evitar fallos por cabeceras erróneas.
- `run_comparison()`: Orquesta la carga, validación y comparación. Retorna un diccionario con todos los hallazgos.

**`src/reporting/`**
- `save_json_report(results, output_arg)`: Guarda el resultado en `results/` con timestamp (HHMMSS).
- `print_comparison_results(results)`: Muestra un resumen amigable en la consola y define el código de salida (exit code).

**`src/batch/validate_headers.py`**
- Script independiente para validar la integridad de las cabeceras en los archivos de entrada.
- Verifica reglas de configuración y consistencia entre pares de archivos (A vs B).

---

## Casos de Uso Implementados

1.  **Validación de Cabeceras**:
    - Detecta si la cantidad de columnas difiere.
    - Detecta si los nombres de las columnas no coinciden (ej: espacio extra `"name "`).
    - **Soporte de extensiones**: Además de `.csv`, soporta `.txt` (como CSV) y `.xls`/`.xlsx` (Excel, primera hoja).

2.  **Comparación Posicional (Default)**:
    - Compara fila por fila y celda por celda (estricto en orden).

3.  **Comparación por Llave (Key-Based)**:
    - Se activa con `--key <columna>`.
    - **Registros Faltantes**: Identifica IDs que están en el archivo 1 pero no en el 2.
    - **Registros Adicionales**: Identifica IDs que están en el archivo 2 pero no en el 1.
    - **Diferencia de Contenido**: Compara celdas de registros con el mismo ID, ignorando el orden de las filas.

4.  **Reporte Integral (Errores Mixtos)**:
    - Si un archivo tiene cabeceras mal nombradas Y registros faltantes, la herramienta reporta AMBOS.
    - Ignora las columnas mal nombradas durante la comparación de celdas para evitar falsos positivos masivos o errores de ejecución.

5.  **Reporte JSON**:
    - Genera un archivo estructurado con detalles `exclusive_to_file` para saber el origen de registros faltantes/extra.

6.  **Funciones Robustas (Murex)**:
    - **Exclusión de Columnas**: `--ignore-columns "col1,col2"` permite saltar columnas volátiles.
    - **Llaves Compuestas**: `--key "col1,col2"` permite usar múltiples columnas como identificador único.
    - **Resumen Estadístico**: Incluye métricas de cobertura y error en el JSON (`matching_percentage`, etc.).

---

## Guía de Instalación y Ejecución

### Requisitos
- Python 3.x instalado.
- [uv](https://github.com/astral-sh/uv) instalado (gestor de entornos y paquetes rápido).

### 1. Ambientar el Proyecto
Este proyecto usa `uv` para gestionar dependencias virtualmente de forma automática.

```bash
# Instalar dependencias (pandas, etc.) y crear entorno virtual implícitamente al correr
uv sync  # O simplemente ejecuta los comandos con 'uv run', él se encarga.
```

(No es necesario crear manualmente el venv si usas `uv run`).

### 2. Ejecutar Comparaciones

**Comparación simple (Posicional):**
```bash
uv run main.py archivo_base.csv archivo_nuevo.csv
```

**Comparación por Llave (Recomendado para datos desordenados):**
```bash
uv run main.py archivo_base.csv archivo_nuevo.csv --key id
```

**Generar Reporte JSON:**
Esto guardará el resultado en la carpeta `results/` con un timestamp.
```bash
uv run main.py archivo_base.csv archivo_nuevo.csv --key id --output reporte.json
```
Resultado: `results/reporte_153000.json`.

**Comparación Avanzada (Llaves Compuestas + Ignorar Columnas):**
```bash
uv run main.py archivo_base.csv archivo_nuevo.csv --key "TradeID,Version" --ignore-columns "RunDate,SystemId"
```

### 3. Generar Datos de Prueba
Para verificar el funcionamiento con scripts de prueba incluidos:
```bash
# Generar datos específicos para pruebas de llave
# (Creará tests/data/key_base.csv, key_shuffled.csv, etc.)
uv run generate_key_data.py
```

```bash
uv run generate_key_data.py
```

## Despliegue en Windows

Para ejecutar esta herramienta en un entorno Windows (Servidor o PC Local):

### 1. Preparar el Paquete
Copie toda la carpeta del proyecto al entorno Windows.
> **Importante**: No copie las carpetas `.venv` ni `results` (se generarán allá).

### 2. Prerrequisitos en Windows
1.  **Instalar Python 3**: [Descargar desde python.org](https://www.python.org/downloads/). Asegúrese de marcar "Add Python to PATH" durante la instalación.
2.  **Instalar UV**: Abra PowerShell o CMD y ejecute:
    ```powershell
    pip install uv
    ```

### 3. Ejecución
Hemos incluido un script nativo `run_batch.bat`. Simplemente haga doble clic sobre él o ejecútelo desde la consola:

```cmd
cd ruta\del\proyecto
run_batch.bat
```

El script se encargará automáticamente de:
1.  Crear el entorno virtual.
2.  Instalar las librerías necesarias.
3.  Ejecutar el comparador con la configuración de `batch_config.json`.

---

## Procesamiento Masivo (Batch)

Módulo diseñado para comparar cientos de archivos (ej: Server A vs Server B) de forma automatizada, resiliente y estructurada.

### 1. Arquitectura Batch
- **Orquestador (`src/batch/orchestrator.py`)**: Script en Python que itera sobre los archivos, gestiona errores (sin detener el proceso) y genera reportes.
- **Configuración (`batch_config.json`)**: Permite definir **llaves dinámicas** según el nombre del archivo.
- **Log (`execution.log`)**: Bitácora detallada de cada paso.
- **Reporte Maestro (`summary_report.xlsx`)**: Excel consolidado con el estado de todos los archivos.

### 2. Ejecución Simplificada
Use el script `run_batch.sh` para ejecutar el proceso completo. Edite las variables `DIR_A` y `DIR_B` dentro del script para apuntar a sus datos reales.

```bash
# Dar permisos de ejecución (solo la primera vez)
chmod +x run_batch.sh

# Ejecutar
./run_batch.sh
```

### Validación de Cabeceras (Preliminar)
Antes de la ejecución masiva, es útil validar que la estructura de los archivos sea correcta:

```bash
uv run src/batch/validate_headers.py --dir-a tests/data/server_a --dir-b tests/data/server_b --config batch_config.json --output results/headers
```
Esto genera un **reporte Excel** (`header_validation.xlsx`) indicando si los archivos tienen las columnas esperadas y si coinciden entre sí.

### 3. Configuración Dinámica (`batch_config.json`)
Este archivo define qué columnas usar como llave primaria (`--key`) automáticamente.

Ejemplo:
```json
{
    "default_keys": ["id"],
    "default_separator": ",",
    "default_ignore_columns": ["system_timestamp"],
    "rules": [
        {
            "pattern": "trade_report_",
            "keys": ["TradeID"] 
        },
        {
            "pattern": "cash_flow_",
            "keys": ["Account", "Date"],
            "ignore_columns": ["input_user", "process_time"],
            "separator": ";"
        }
    ]
}
```
*   **`ignore_columns`**: Puede definirse globalmente (`default_ignore_columns`) o anularse por regla.
*   **`default_separator`**: Define el separador por defecto para todos los archivos (ej: `,` o `;`). Si no se especifica, el sistema usa **`;`** por defecto.
*   **`separator` (en reglas)**: Permite anular el separador global para archivos específicos.
*   Si el archivo empieza con `trade_report_`, usa `TradeID`.
*   Si no coincide con ninguna regla, usa `default_keys` (o lo definido en `--key` como fallback).

### 4. Validaciones Avanzadas y Métricas

El sistema incluye protecciones automáticas y análisis bidireccional:

*   **Detección de Duplicados (`DUPLICATE_KEYS`)**:
    *   Valida la unicidad de las llaves Primarias *antes* de comparar.
    *   Si encuentra duplicados, **aborta** la comparación de ese archivo (para evitar errores cartesianos) y genera un reporte Excel con la hoja **"Duplicate Keys"**, listando los registros problemáticos.

*   **Auditoría Inversa (`MISSING_IN_A`)**:
    *   No solo verifica si falta el archivo destino (`MISSING_IN_B`).
    *   Al final del proceso, detecta archivos "huérfanos" que existen en el Servidor B pero no en el A.

*   **Métricas de Desempeño**:
    *   Mide el tiempo exacto de procesamiento por archivo.
    *   Incluye la columna `Duration (s)` en el reporte maestro para detectar cuellos de botella.

### 5. Salida Generada
Los resultados se guardan en `results/batch_YYYYMMDD_HHMMSS/`:

*   **`summary_report.xlsx`**: Panel de control.
    *   **Status**:
        *   `OK`: Archivos idénticos.
        *   `DIFF`: Diferencias de contenido encontradas.
        *   `ERROR`: Fallo técnico (ej: archivo corrupto).
        *   `DUPLICATE_KEYS`: Llaves duplicadas impiden comparación.
        *   `KEY_NOT_FOUND`: La columna llave configurada no existe en el archivo.
        *   `MISSING_IN_B`: Archivo existe en origen pero no en destino.
        *   `MISSING_IN_A`: Archivo existe en destino pero no en origen.
    *   **Métricas**: Filas, Diferencias, Duración (s).
    *   **Detail Report**: Nombre del archivo Excel con el detalle (si aplica).
*   **`execution.log`**: Bitácora técnica con muestras de errores e IDs duplicados.
*   **`details/`**: Carpeta que contiene reportes Excel (`.xlsx`) detallados para los casos de `DIFF` o `DUPLICATE_KEYS`.

### 5. Generar Datos de Prueba Batch
Para simular un entorno con 200 archivos (incluyendo casos de borde y llaves especiales):

```bash
uv run generate_batch_data.py
```
Esto creará `tests/batch_data/server_a` y `server_b` listos para probar con `./run_batch.sh`.

Para una prueba más agresiva (100 archivos mezclando CSV, TXT, Excel y casos de error):
```bash
uv run tests/generate_large_mixed_data.py
```
Esto creará `tests/large_mixed_data/server_a` y `server_b`.
**Nota**: `run_batch_no_uv.bat` ya está configurado para usar esta ruta por defecto.

---

## Utilidades Adicionales

El proyecto incluye scripts auxiliares para la gestión y limpieza de archivos antes o después de la comparación.

### 1. Inventario de Archivos (`inventario_csv_excel_json.py`)
Escanea una carpeta (recursivamente) para catalogar archivos CSV, incluso aquellos con sufijos extraños (ej: `archivo.csv_PRO_2025`). Detecta automáticamente delimitadores, encodings y cabeceras.

**Salida**:
- **Excel**: Lista detallada con tamaño, fecha, cabeceras, estado (OK/ERROR).
- **JSON**: Lista de patrones de nombre y las llaves (columnas) consolidadas encontradas.

```bash
uv run inventario_csv_excel_json.py "ruta/a/archivos" --output "mi_inventario.xlsx" --csv-mode smart
```

### 2. Limpieza de Nombres (`limpiar_sufijo_csv.py`)
Renombra masivamente archivos que tienen texto basura después de la extensión `.csv`.
Ejemplo: `DATA_2025.csv_OLD_VERSION` -> `DATA_2025.csv`.

```bash
# Ejecutar en modo prueba (Dry Run) para ver qué pasaría
uv run limpiar_sufijo_csv.py "ruta/a/limpiar" --recursive --dry-run

# Ejecutar cambios reales
uv run limpiar_sufijo_csv.py "ruta/a/limpiar" --recursive
```
*Maneja colisiones agregando `(1)`, `(2)` automáticamente.*

### 3. Movimiento Avanzado de Archivos (`mover_archivos_v3.py`)
Herramienta robusta para mover o copiar archivos entre directorios, con reintentos y reporte CSV.

**Características**:
- Modos: `move`, `copy`, `copy_then_delete` (verifica integridad antes de borrar).
- Filtros por extensión.
- Puede mantener la estructura de carpetas (`--keep-structure`).

```bash
# Mover solo archivos .csv y .json manteniendo la estructura de carpetas
uv run mover_archivos_v3.py "origen/" "destino/" --mode move --extensions .csv .json --keep-structure

# Copia segura con verificación
uv run mover_archivos_v3.py "origen/" "destino/" --mode copy_then_delete
```

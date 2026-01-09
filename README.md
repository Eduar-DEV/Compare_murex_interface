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

---

## Casos de Uso Implementados

1.  **Validación de Cabeceras**:
    - Detecta si la cantidad de columnas difiere.
    - Detecta si los nombres de las columnas no coinciden (ej: espacio extra `"name "`).

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
# Generar datos grandes
uv run generate_large_data.py

# Generar datos específicos para pruebas de llave
# (Creará tests/data/key_base.csv, key_shuffled.csv, etc.)
uv run generate_key_data.py
```

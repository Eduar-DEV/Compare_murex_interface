import os
import argparse
import json
import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple
import sys
import csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------
# Utilidades de codificación
# ---------------------------

COMMON_ENCODINGS = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
COMMON_SEPARATORS = [",", ";", "\t", "|", ":"]


def load_json_with_fallback(path: str, preferred: Optional[str] = None) -> Dict:
    """
    Carga JSON probando varias codificaciones comunes.
    Si preferred no funciona, cae a otras.
    """
    tried: List[str] = []
    encodings = []
    if preferred:
        encodings.append(preferred)
    encodings.extend([e for e in COMMON_ENCODINGS if e not in encodings])

    last_err: Optional[Exception] = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return json.load(f)
        except UnicodeDecodeError as e:
            tried.append(enc)
            last_err = e
            continue
        except Exception as e:
            logger.error(f"Failed to load config file with {enc}: {e}")
            raise
    raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Could not decode config file. Tried encodings: {tried}")


def sniff_separator(file_path: str, encoding: str, sample_size: int = 64_000) -> Optional[str]:
    """
    Intenta detectar el separador usando csv.Sniffer sobre una muestra.
    Devuelve un delimitador o None si no se detecta.
    """
    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            sample = f.read(sample_size)
            # Si la muestra no contiene separadores comunes, no intentamos sniffer.
            if not any(sep in sample for sep in COMMON_SEPARATORS):
                return None
            dialect = csv.Sniffer().sniff(sample, delimiters="".join(COMMON_SEPARATORS))
            return dialect.delimiter
    except Exception:
        return None


def read_header_with_fallback(
    file_path: str,
    sep_hint: Optional[str],
    preferred_encoding: Optional[str] = None
) -> Tuple[List[str], str, str]:
    """
    Lee solo el encabezado (nrows=0) de un CSV probando encodings y, si es necesario, separadores.
    Devuelve (headers, encoding_usado, separator_usado).
    Estrategia:
      1) Probar encodings comunes (priorizando preferred_encoding).
      2) Para cada encoding, probar el sep_hint si existe.
      3) Si el hint falla (1 sola columna o error), probar separadores comunes.
      4) Si sigue sin funcionar, usar csv.Sniffer para autodetectar.
    """
    encodings = []
    if preferred_encoding:
        encodings.append(preferred_encoding)
    encodings.extend([e for e in COMMON_ENCODINGS if e not in encodings])

    last_err: Optional[Exception] = None

    def looks_like_single_column(cols: List[str]) -> bool:
        # Heurística: si sólo hay 1 columna, probablemente el separador no fue correcto.
        return len(cols) <= 1

    for enc in encodings:
        # 1) Intento con hint directo (si existe)
        seps_to_try: List[str] = []
        if sep_hint:
            seps_to_try.append(sep_hint)
        # 2) Luego probar otros comunes (evita duplicados)
        seps_to_try.extend([s for s in COMMON_SEPARATORS if s not in seps_to_try])

        # 3) Probar lista de separadores
        for sep in seps_to_try:
            try:
                df = pd.read_csv(file_path, sep=sep, nrows=0, encoding=enc)
                headers = list(df.columns)
                if not looks_like_single_column(headers):
                    return headers, enc, sep
                # Si parece 1 columna, seguimos probando con otro separador
            except UnicodeDecodeError as e:
                last_err = e
                break  # cambia encoding
            except Exception as e:
                # Otros errores de parsing; probamos con otro separador
                last_err = e
                continue

        # 4) Intentar autodetección por sniffer con este encoding
        auto_sep = sniff_separator(file_path, enc)
        if auto_sep:
            try:
                df = pd.read_csv(file_path, sep=auto_sep, nrows=0, encoding=enc)
                headers = list(df.columns)
                if not looks_like_single_column(headers):
                    return headers, enc, auto_sep
            except Exception as e:
                last_err = e
                # caemos a siguiente encoding

    # Si nada funcionó, levantar el último error conocido
    err_msg = f"Cannot decode/parse file '{file_path}'. Tried encodings: {encodings}"
    if last_err:
        raise type(last_err)(str(last_err))
    raise UnicodeDecodeError("utf-8", b"", 0, 1, err_msg)


# ---------------------------
# Lógica principal
# ---------------------------

def load_config(config_path: str, preferred_encoding: Optional[str] = None) -> Dict:
    """Load configuration from JSON file con soporte de encoding."""
    try:
        return load_json_with_fallback(config_path, preferred_encoding)
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        sys.exit(1)


def get_keys_for_file(filename: str, config: Dict) -> List[str]:
    """Determine expected keys for a file based on config rules."""
    rules = config.get("rules", [])
    for rule in rules:
        if rule.get("pattern") and rule["pattern"] in filename:
            return rule.get("keys", [])
    return config.get("default_keys", [])


def get_encoding_for_file(filename: str, config: Dict, cli_default: Optional[str]) -> Optional[str]:
    """
    Determina el encoding a usar para el archivo:
    prioridad: regla específica -> default_encoding en config -> CLI -> None
    """
    for rule in config.get("rules", []):
        if rule.get("pattern") and rule["pattern"] in filename:
            if "encoding" in rule and rule["encoding"]:
                return rule["encoding"]
    if "default_encoding" in config and config["default_encoding"]:
        return config["default_encoding"]
    if cli_default:
        return cli_default
    return None


def get_separator_for_file(filename: str, config: Dict, cli_default: Optional[str]) -> Optional[str]:
    """
    Determina el separador a usar:
    prioridad: regla específica -> default_separator en config -> CLI -> None (autodetección)
    """
    for rule in config.get("rules", []):
        if rule.get("pattern") and rule["pattern"] in filename:
            if "separator" in rule and rule["separator"]:
                return rule["separator"]
    if "default_separator" in config and config["default_separator"]:
        return config["default_separator"]
    if cli_default:
        return cli_default
    return None  # activará autodetección si hace falta


def validate_csv_header(
    file_path: str,
    expected_keys: List[str],
    separator_hint: Optional[str] = None,
    preferred_encoding: Optional[str] = None
) -> Dict:
    """
    Validate headers of a single CSV file.
    Returns a dictionary with status and details.
    Usa fallback de encoding y separador (incluida autodetección).
    """
    try:
        headers, used_enc, used_sep = read_header_with_fallback(file_path, separator_hint, preferred_encoding)

        missing_keys = [key for key in expected_keys if key not in headers]

        if missing_keys:
            return {
                "status": "NOK",
                "reason": f"Missing required keys: {', '.join(missing_keys)}",
                "headers": str(headers),
                "encoding": used_enc,
                "separator": used_sep
            }

        return {
            "status": "OK",
            "reason": "All required keys present",
            "headers": str(headers),
            "encoding": used_enc,
            "separator": used_sep
        }

    except UnicodeDecodeError as e:
        return {
            "status": "ERROR",
            "reason": f"Encoding error: {str(e)}",
            "headers": "",
            "encoding": "",
            "separator": ""
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "reason": str(e),
            "headers": "",
            "encoding": "",
            "separator": ""
        }


def validate_pair(
    file_a: str,
    file_b: str,
    separator_hint_a: Optional[str] = None,
    separator_hint_b: Optional[str] = None,
    preferred_encoding_a: Optional[str] = None,
    preferred_encoding_b: Optional[str] = None
) -> Dict:
    """
    Validate that headers of file_a and file_b are identical.
    Cada lado puede usar su propio separador/encoding (resuelto por reglas/config).
    """
    try:
        header_a, enc_a, sep_a = read_header_with_fallback(file_a, separator_hint_a, preferred_encoding_a)
        header_b, enc_b, sep_b = read_header_with_fallback(file_b, separator_hint_b, preferred_encoding_b)

        if header_a != header_b:
            return {
                "match": False,
                "reason": "Headers do not match between Source A and Source B",
                "diff": f"A: {header_a} | B: {header_b}",
                "encoding_a": enc_a,
                "encoding_b": enc_b,
                "separator_a": sep_a,
                "separator_b": sep_b
            }

        return {
            "match": True,
            "reason": "Headers match",
            "encoding_a": enc_a,
            "encoding_b": enc_b,
            "separator_a": sep_a,
            "separator_b": sep_b
        }

    except UnicodeDecodeError as e:
        return {
            "match": False,
            "reason": f"Encoding error while comparing: {str(e)}",
            "diff": "",
            "encoding_a": "",
            "encoding_b": "",
            "separator_a": "",
            "separator_b": ""
        }
    except Exception as e:
        return {
            "match": False,
            "reason": f"Error comparing files: {str(e)}",
            "diff": "",
            "encoding_a": "",
            "encoding_b": "",
            "separator_a": "",
            "separator_b": ""
        }


def main():
    parser = argparse.ArgumentParser(description="Validate CSV headers before processing.")
    parser.add_argument("--dir-a", required=True, help="Path to directory A")
    parser.add_argument("--dir-b", required=True, help="Path to directory B")
    parser.add_argument("--config", required=True, help="Path to configuration JSON (e.g., batch_config.json)")
    parser.add_argument("--output", required=True, help="Output directory for report")
    parser.add_argument("--separator", default=None, help="CSV separator hint. If omitted, uses config or autodetects")
    parser.add_argument(
        "--encoding",
        default=None,
        help="Default text encoding for CSV/TXT (e.g., utf-8, utf-8-sig, cp1252, latin-1). "
             "Overrides config default_encoding if provided."
    )
    parser.add_argument(
        "--config-encoding",
        default=None,
        help="Encoding hint for reading the config JSON (if not UTF-8)."
    )

    args = parser.parse_args()

    if not os.path.exists(args.output):
        os.makedirs(args.output)

    # Cargar config con soporte de codificación
    config = load_config(args.config, preferred_encoding=args.config_encoding)

    # Resolver defaults desde config/CLI:
    # separator y encoding por archivo se resuelven con funciones get_*_for_file.
    default_file_encoding = args.encoding or config.get("default_encoding")
    # OJO: No fijamos separator global aquí; lo resolvemos por archivo (regla → default → CLI → autodetect)

    results = []

    # Iterar archivos en A
    try:
        files_a = os.listdir(args.dir_a)
    except FileNotFoundError:
        logger.error(f"Directory not found: {args.dir_a}")
        sys.exit(1)

    logger.info(f"Starting validation for {len(files_a)} files...")

    for file_name in files_a:
        if not file_name.lower().endswith('.csv'):
            continue

        path_a = os.path.join(args.dir_a, file_name)
        path_b = os.path.join(args.dir_b, file_name)

        file_result = {
            "File Name": file_name,
            "Validation Status": "UNKNOWN",
            "Details": "",
            "Encoding A": "",
            "Encoding B": "",
            "Separator A": "",
            "Separator B": ""
        }

        # 1) Checar existencia en B
        if not os.path.exists(path_b):
            file_result["Validation Status"] = "NOK"
            file_result["Details"] = "File missing in Source B"
            results.append(file_result)
            continue

        # 2) Determinar claves esperadas
        expected_keys = get_keys_for_file(file_name, config)

        # 3) Resolver encoding y separator por archivo (por reglas/config/CLI)
        enc_for_this_file = get_encoding_for_file(file_name, config, default_file_encoding)
        sep_for_this_file = get_separator_for_file(file_name, config, args.separator)

        # 4) Validar headers en A
        res_a = validate_csv_header(path_a, expected_keys, sep_for_this_file, enc_for_this_file)
        file_result["Encoding A"] = res_a.get("encoding", "")
        file_result["Separator A"] = res_a.get("separator", "")
        if res_a["status"] != "OK":
            file_result["Validation Status"] = "NOK"
            file_result["Details"] = f"Source A: {res_a['reason']}"
            results.append(file_result)
            continue

        # 5) Validar headers en B
        res_b = validate_csv_header(path_b, expected_keys, sep_for_this_file, enc_for_this_file)
        file_result["Encoding B"] = res_b.get("encoding", "")
        file_result["Separator B"] = res_b.get("separator", "")
        if res_b["status"] != "OK":
            file_result["Validation Status"] = "NOK"
            file_result["Details"] = f"Source B: {res_b['reason']}"
            results.append(file_result)
            continue

        # 6) Comparar headers (cada lado puede terminar con separador detectado distinto)
        res_pair = validate_pair(
            path_a, path_b,
            separator_hint_a=res_a.get("separator"),
            separator_hint_b=res_b.get("separator"),
            preferred_encoding_a=res_a.get("encoding"),
            preferred_encoding_b=res_b.get("encoding")
        )
        # guardar los encodings/separadores usados realmente en la comparación si existen
        if "encoding_a" in res_pair and res_pair["encoding_a"]:
            file_result["Encoding A"] = res_pair["encoding_a"]
        if "encoding_b" in res_pair and res_pair["encoding_b"]:
            file_result["Encoding B"] = res_pair["encoding_b"]
        if "separator_a" in res_pair and res_pair["separator_a"]:
            file_result["Separator A"] = res_pair["separator_a"]
        if "separator_b" in res_pair and res_pair["separator_b"]:
            file_result["Separator B"] = res_pair["separator_b"]

        if not res_pair["match"]:
            file_result["Validation Status"] = "NOK"
            file_result["Details"] = res_pair["reason"]
            results.append(file_result)
            continue

        # Éxito
        file_result["Validation Status"] = "OK"
        file_result["Details"] = "Headers Valid and Matching"
        results.append(file_result)

    # Generar reporte
    report_path = os.path.join(args.output, "header_validation.xlsx")
    df_results = pd.DataFrame(results)

    try:
        with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
            df_results.to_excel(writer, index=False, sheet_name="Validation")
        logger.info(f"Validation complete. Report generated at: {report_path}")
    except Exception as e:
        logger.error(f"Failed to save Excel report: {e}")
        csv_path = os.path.join(args.output, "header_validation.csv")
        df_results.to_csv(csv_path, index=False)
        logger.info(f"Saved as CSV fallback at: {csv_path}")


if __name__ == "__main__":
    main()
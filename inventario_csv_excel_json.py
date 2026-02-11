#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import logging
import re
from pathlib import Path
from datetime import datetime

import pandas as pd


# ---------- Identificación de CSV "raros" ----------
def is_csv_like(path: Path, mode: str = "smart") -> bool:
    """
    mode:
      - strict: solo archivos que terminan en .csv
      - smart : termina en .csv o contiene '.csv_' (ej: archivo.csv_PRO_2026...)
      - contains: contiene '.csv' en el nombre (más permisivo)
    """
    name = path.name.lower()

    if mode == "strict":
        return name.endswith(".csv")

    if mode == "smart":
        return name.endswith(".csv") or (".csv_" in name)

    # contains
    return ".csv" in name


# ---------- Extraer patrón a partir del nombre ----------
DATE_8_RE = re.compile(r"\d{8}")  # YYYYMMDD


def extract_pattern(filename: str) -> str:
    """
    Extrae el 'pattern' del nombre:
    - Si encuentra una fecha YYYYMMDD, devuelve el prefijo antes de esa fecha.
      Ej: CDB_Algo_20260126.csv_PRO_... -> CDB_Algo_
    - Si no encuentra fecha, toma lo que está antes de ".csv" si existe.
    """
    m = DATE_8_RE.search(filename)
    if m:
        return filename[:m.start()]

    low = filename.lower()
    idx = low.find(".csv")
    if idx != -1:
        return filename[:idx]
    return filename


# ---------- Leer cabecera sin cargar todo el archivo ----------
def detect_dialect_and_header(file_path: Path, encoding: str | None = None, sample_size: int = 65536):
    """
    Detecta delimitador usando csv.Sniffer (si puede) y obtiene la primera fila como header.
    Devuelve: (headers: list[str], delimiter: str, used_encoding: str)
    """
    encodings_to_try = [encoding] if encoding else ["utf-8-sig", "utf-8", "latin-1"]
    last_error = None

    for enc in encodings_to_try:
        try:
            with open(file_path, "r", encoding=enc, newline="") as f:
                sample = f.read(sample_size)
                f.seek(0)

                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
                    delimiter = dialect.delimiter
                except Exception:
                    # fallback común: ';' si aparece, si no ','
                    delimiter = ";" if ";" in sample else ","

                reader = csv.reader(f, delimiter=delimiter)
                header = next(reader, [])
                header = [h.strip() for h in header if h is not None]
                return header, delimiter, enc

        except Exception as e:
            last_error = e

    raise last_error if last_error else RuntimeError("No se pudo leer el archivo")


# ---------- Inventario ----------
def build_inventory(root: Path, recursive: bool, csv_mode: str, encoding: str | None):
    rows = []
    iterator = root.rglob("*") if recursive else root.glob("*")

    for p in iterator:
        if not p.is_file():
            continue
        if not is_csv_like(p, mode=csv_mode):
            continue

        info = {
            "archivo": p.name,
            "ruta_completa": str(p.resolve()),
            "pattern": extract_pattern(p.name),
            "cabeceras": "",
            "num_columnas": 0,
            "delimitador": "",
            "encoding": "",
            "tamano_bytes": None,
            "fecha_modificacion": None,
            "estado": "OK",
            "error": "",
        }

        try:
            st = p.stat()
            info["tamano_bytes"] = st.st_size
            info["fecha_modificacion"] = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")

            headers, delimiter, used_enc = detect_dialect_and_header(p, encoding=encoding)
            info["delimitador"] = delimiter
            info["encoding"] = used_enc
            info["num_columnas"] = len(headers)
            info["cabeceras"] = " | ".join(headers)

            if len(headers) == 0:
                info["estado"] = "WARNING"
                info["error"] = "No se detectó cabecera (archivo vacío o primera fila vacía)."

        except Exception as e:
            info["estado"] = "ERROR"
            info["error"] = f"{type(e).__name__}: {e}"

        rows.append(info)

    return rows


# ---------- Excel ----------
def write_excel(rows, output: Path):
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["estado", "archivo"], ascending=[True, True])

    output.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="inventario")

        # Hoja extra (opcional): 1 cabecera por fila
        expanded = []
        for r in rows:
            if r.get("estado") == "OK" and r.get("cabeceras"):
                headers = r["cabeceras"].split(" | ")
                for h in headers:
                    expanded.append({
                        "archivo": r["archivo"],
                        "pattern": r["pattern"],
                        "ruta_completa": r["ruta_completa"],
                        "cabecera": h
                    })
        if expanded:
            pd.DataFrame(expanded).to_excel(writer, index=False, sheet_name="cabeceras_detalle")


# ---------- JSON (patterns + keys en orden original, sin duplicar patterns) ----------
def build_patterns_json_preserve_order(rows):
    """
    Genera lista JSON:
      [{ "pattern": "...", "keys": [cab1, cab2, ...] }, ...]

    Reglas:
    - Agrupa por pattern (no duplica patterns).
    - keys = unión de todas las cabeceras por pattern.
    - Respeta el orden original:
        * se mantiene el orden en que aparecen en cada archivo,
        * y sólo se agregan al final las cabeceras nuevas.
    """
    # pattern -> {"keys": [..], "seen": set(..)}
    agg = {}

    for r in rows:
        if r.get("estado") != "OK":
            continue

        pattern = (r.get("pattern") or "").strip()
        if not pattern:
            continue

        headers_str = (r.get("cabeceras") or "").strip()
        headers = [h.strip() for h in headers_str.split(" | ")] if headers_str else []
        headers = [h for h in headers if h]  # limpiar vacíos

        if pattern not in agg:
            agg[pattern] = {"keys": [], "seen": set()}

        for h in headers:
            if h not in agg[pattern]["seen"]:
                agg[pattern]["keys"].append(h)
                agg[pattern]["seen"].add(h)

    # salida estable
    result = []
    for pattern in sorted(agg.keys()):
        result.append({
            "pattern": pattern,
            "keys": agg[pattern]["keys"]
        })
    return result


def write_json(data, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(
        description="Inventario de CSV (incluye nombres tipo archivo.csv_PRO_...) y exporta a Excel + JSON."
    )
    parser.add_argument("ruta", help="Ruta a escanear (carpeta).")
    parser.add_argument("--output", default="inventario_csv.xlsx", help="Excel de salida (.xlsx).")
    parser.add_argument("--json-output", default="patterns_keys.json", help="JSON de salida (pattern/keys).")
    parser.add_argument("--no-recursive", action="store_true", help="Si se indica, NO busca en subcarpetas.")
    parser.add_argument("--csv-mode", choices=["strict", "smart", "contains"], default="smart",
                        help="Cómo identificar CSV: strict (.csv final), smart (.csv o .csv_), contains (contiene '.csv').")
    parser.add_argument("--encoding", default=None, help="Forzar encoding (utf-8, latin-1, etc).")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    root = Path(args.ruta).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"La ruta no existe o no es directorio: {root}")

    recursive = not args.no_recursive
    excel_out = Path(args.output).expanduser().resolve()
    json_out = Path(args.json_output).expanduser().resolve()

    logging.info(f"Escaneando: {root} | recursive={recursive} | csv_mode={args.csv_mode}")
    rows = build_inventory(root, recursive=recursive, csv_mode=args.csv_mode, encoding=args.encoding)

    logging.info(f"Encontrados (tipo CSV): {len(rows)}")
    write_excel(rows, excel_out)

    patterns_json = build_patterns_json_preserve_order(rows)
    write_json(patterns_json, json_out)

    ok = sum(1 for r in rows if r["estado"] == "OK")
    warn = sum(1 for r in rows if r["estado"] == "WARNING")
    err = sum(1 for r in rows if r["estado"] == "ERROR")

    logging.info(f"OK={ok} | WARNING={warn} | ERROR={err}")
    logging.info(f"Excel generado: {excel_out}")
    logging.info(f"JSON generado:  {json_out} | entries={len(patterns_json)}")


if __name__ == "__main__":
    main()
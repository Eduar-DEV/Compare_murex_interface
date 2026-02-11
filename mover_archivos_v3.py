#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from datetime import datetime


def setup_logging(log_file: Path | None, verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers,
    )


def normalize_windows_long_path(p: Path) -> str:
    """Windows: prefijo \\?\ para rutas largas."""
    s = str(p)
    if os.name == "nt":
        s = s.replace("/", "\\")
        if not s.startswith("\\\\?\\"):
            if s.startswith("\\\\"):
                s = "\\\\?\\UNC\\" + s.lstrip("\\")
            else:
                s = "\\\\?\\" + s
    return s


def unique_destination_path(dest_dir: Path, filename: str) -> Path:
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    i = 1
    while True:
        c = dest_dir / f"{stem} ({i}){suffix}"
        if not c.exists():
            return c
        i += 1


def parse_extensions(ext_list: list[str] | None) -> set[str] | None:
    if not ext_list:
        return None
    out = set()
    for e in ext_list:
        e = e.strip().lower()
        if not e:
            continue
        if not e.startswith("."):
            e = "." + e
        out.add(e)
    return out or None


def should_include(file_path: Path, extensions: set[str] | None) -> bool:
    """
    Incluye archivos por:
      1) coincidencia normal de extensión (suffix): ej. foo.xlsx
      2) coincidencia por "extensión + _" dentro del nombre: ej. foo.xlsx_PRO_2026...
         (esto cubre .csv_ .txt_ .xlsx_ etc)
    """
    if extensions is None:
        return True

    name = file_path.name.lower()
    suffix = file_path.suffix.lower()

    # Caso normal: termina en .txt / .xlsx / .csv / etc
    if suffix in extensions:
        return True

    # Caso "raro": contiene ".ext_" en el nombre (ej: archivo.xlsx_PRO_...)
    for ext in extensions:
        if f"{ext}_" in name:
            return True

    return False


def is_excluded(path: Path, excluded_dirnames: set[str]) -> bool:
    parts = {p.lower() for p in path.parts}
    return any(ed.lower() in parts for ed in excluded_dirnames)


def same_file_quick(src: Path, dst: Path) -> bool:
    """
    Verificación ligera: tamaño y mtime cercano.
    Para verificación fuerte podríamos usar hash, pero es más lento.
    """
    try:
        ss = src.stat()
        ds = dst.stat()
        if ss.st_size != ds.st_size:
            return False
        # tolerancia por distintos FS
        return abs(ss.st_mtime - ds.st_mtime) < 2.0
    except Exception:
        return False


def op_file(
    src: Path,
    dst: Path,
    mode: str,
    dry_run: bool,
) -> None:
    """
    mode:
      - move: shutil.move
      - copy: shutil.copy2
      - copy_then_delete: copy2 + verificación + unlink
    """
    if dry_run:
        return

    src_s = normalize_windows_long_path(src)
    dst_s = normalize_windows_long_path(dst)

    if mode == "move":
        shutil.move(src_s, dst_s)
        return

    if mode == "copy":
        shutil.copy2(src_s, dst_s)
        return

    if mode == "copy_then_delete":
        shutil.copy2(src_s, dst_s)

        # Verificación rápida antes de borrar el origen
        if not same_file_quick(src, dst):
            raise RuntimeError(
                "Verificación fallida tras copia (size/mtime no coincide). No se borra el origen."
            )
        src.unlink()
        return

    raise ValueError(f"Modo no soportado: {mode}")


def do_with_retries(action, retries: int, sleep_ms: int):
    last = None
    for attempt in range(retries + 1):
        try:
            return action()
        except Exception as e:
            last = e
            if attempt < retries:
                time.sleep(sleep_ms / 1000)
            else:
                raise last


def run(
    source_dir: Path,
    dest_dir: Path,
    dry_run: bool,
    keep_structure: bool,
    extensions: set[str] | None,
    avoid_overwrite: bool,
    excluded_dirnames: set[str],
    retries: int,
    sleep_ms: int,
    report_csv: Path | None,
    mode: str,
    skip_existing: bool,
) -> dict:
    stats = {"ok": 0, "skipped": 0, "errors": 0}
    rows = []

    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError(f"El origen no existe o no es directorio: {source_dir}")

    dest_dir.mkdir(parents=True, exist_ok=True)

    for path in source_dir.rglob("*"):
        try:
            if is_excluded(path, excluded_dirnames):
                stats["skipped"] += 1
                rows.append([str(path), "", "SKIPPED", "excluded"])
                continue

            if not path.is_file():
                stats["skipped"] += 1
                rows.append([str(path), "", "SKIPPED", "not_file"])
                continue

            if not should_include(path, extensions):
                stats["skipped"] += 1
                rows.append([str(path), "", "SKIPPED", "extension_filter"])
                continue

            # destino
            if keep_structure:
                rel = path.relative_to(source_dir)
                target_dir = dest_dir / rel.parent
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / path.name
            else:
                target_path = dest_dir / path.name

            if avoid_overwrite:
                target_path = unique_destination_path(target_path.parent, target_path.name)

            # saltar si ya existe (solo si NO estamos renombrando)
            if skip_existing and target_path.exists() and not avoid_overwrite:
                stats["skipped"] += 1
                rows.append([str(path), str(target_path), "SKIPPED", "dest_exists"])
                continue

            logging.info(f"{mode.upper()}: {path} -> {target_path}")

            def action():
                return op_file(path, target_path, mode=mode, dry_run=dry_run)

            do_with_retries(action, retries=retries, sleep_ms=sleep_ms)

            stats["ok"] += 1
            rows.append([str(path), str(target_path), "OK", mode])

        except Exception as e:
            stats["errors"] += 1
            reason = f"{type(e).__name__}: {e}"
            rows.append([str(path), str(target_path) if "target_path" in locals() else "", "ERROR", reason])
            logging.error(f"ERROR: {path} -> {reason}")

    if report_csv:
        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(report_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["source", "dest", "status", "reason"])
            w.writerows(rows)

    return stats


def main():
    p = argparse.ArgumentParser(
        description="Copia o mueve archivos recursivamente (con reporte CSV)."
    )
    p.add_argument("source")
    p.add_argument("dest")

    p.add_argument(
        "--mode",
        choices=["move", "copy", "copy_then_delete"],
        default="move",
        help="move=movimiento directo, copy=copia, copy_then_delete=copia y luego borra si verifica.",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--keep-structure", action="store_true")
    p.add_argument("--extensions", nargs="*")
    p.add_argument("--overwrite", action="store_true", help="Sobrescribe si existe el mismo nombre (NO renombra).")
    p.add_argument("--skip-existing", action="store_true",
                   help="Si destino existe, omite (solo útil cuando usas --overwrite).")
    p.add_argument("--exclude-dirs", nargs="*", default=[], help="Ej: .git node_modules venv")
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--sleep-ms", type=int, default=300)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--log-file", default=None)
    p.add_argument("--report-csv", default="reporte_operacion.csv")

    args = p.parse_args()

    source_dir = Path(args.source).expanduser().resolve()
    dest_dir = Path(args.dest).expanduser().resolve()
    log_file = Path(args.log_file).expanduser().resolve() if args.log_file else None
    report_csv = Path(args.report_csv).expanduser().resolve() if args.report_csv else None

    setup_logging(log_file, args.verbose)

    extensions = parse_extensions(args.extensions)
    excluded = set(args.exclude_dirs)

    logging.info("=== Inicio ===")
    logging.info(f"Origen: {source_dir}")
    logging.info(f"Destino: {dest_dir}")
    logging.info(f"Mode: {args.mode} | Dry-run: {args.dry_run} | Keep-structure: {args.keep_structure}")
    logging.info(f"Overwrite: {args.overwrite} | Skip-existing: {args.skip_existing}")
    logging.info(f"Extensions: {sorted(list(extensions)) if extensions else 'ALL'}")
    logging.info(f"Exclude dirs: {sorted(list(excluded))}")
    logging.info(f"Report CSV: {report_csv}")

    start = datetime.now()
    stats = run(
        source_dir=source_dir,
        dest_dir=dest_dir,
        dry_run=args.dry_run,
        keep_structure=args.keep_structure,
        extensions=extensions,
        avoid_overwrite=not args.overwrite,   # si NO overwrite => renombrar colisiones
        excluded_dirnames=excluded,
        retries=args.retries,
        sleep_ms=args.sleep_ms,
        report_csv=report_csv,
        mode=args.mode,
        skip_existing=args.skip_existing,
    )
    elapsed = datetime.now() - start

    logging.info("=== Resumen ===")
    logging.info(f"OK:       {stats['ok']}")
    logging.info(f"Omitidos: {stats['skipped']}")
    logging.info(f"Errores:  {stats['errors']}")
    logging.info(f"Tiempo:   {elapsed}")
    logging.info("=== Fin ===")


if __name__ == "__main__":
    sys.exit(main())

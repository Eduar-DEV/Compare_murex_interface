#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path


def unique_target(path: Path) -> Path:
    """Evita colisiones: si existe, agrega (1), (2), etc."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    i = 1
    while True:
        candidate = path.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def strip_after_csv(filename: str) -> str | None:
    """
    Si el nombre contiene '.csv' (en cualquier casing) y tiene texto después,
    retorna el nombre recortado hasta '.csv'. Si no, retorna None.
    """
    low = filename.lower()
    idx = low.find(".csv")
    if idx == -1:
        return None

    new_name = filename[:idx + 4]  # incluye ".csv"
    if new_name == filename:
        return None  # ya termina en .csv, no se cambia

    return new_name


def main():
    p = argparse.ArgumentParser(
        description="Renombra archivos para borrar todo lo posterior a '.csv' (ej: *.csv_PRO_* -> *.csv)."
    )
    p.add_argument("ruta", help="Carpeta a procesar")
    p.add_argument("--recursive", action="store_true", help="Procesar subcarpetas")
    p.add_argument("--dry-run", action="store_true", help="Simula sin renombrar")
    args = p.parse_args()

    root = Path(args.ruta).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Ruta inválida: {root}")

    iterator = root.rglob("*") if args.recursive else root.iterdir()

    renamed = 0
    skipped = 0

    for f in iterator:
        if not f.is_file():
            continue

        new_name = strip_after_csv(f.name)
        if not new_name:
            skipped += 1
            continue

        target = unique_target(f.with_name(new_name))

        print(f"{f.name}  ->  {target.name}")

        if not args.dry_run:
            f.rename(target)

        renamed += 1

    print("\nResumen")
    print(f"Renombrados: {renamed}")
    print(f"Sin cambios: {skipped}")
    print(f"Dry-run: {args.dry_run}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
from typing import Optional


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


# Extensiones a limpiar (insensible a mayúsculas)
TARGET_EXTS = (".csv", ".txt", ".xls", ".pdf")


def strip_after_ext(filename: str) -> Optional[str]:
    """
    Si el nombre contiene alguna de las extensiones objetivo (.csv, .txt, .xls, .pdf)
    (en cualquier casing) y tiene texto después, retorna el nombre recortado hasta
    la extensión. Esto incluye casos con '_PRO' (ej.: .csv_PRO* -> .csv).
    Si no hay cambios que hacer, retorna None.
    """
    low = filename.lower()

    # Hallar la primera ocurrencia de cualquiera de las extensiones
    first_hit_idx = None
    hit_ext = None
    for ext in TARGET_EXTS:
        idx = low.find(ext)
        if idx != -1:
            if first_hit_idx is None or idx < first_hit_idx:
                first_hit_idx = idx
                hit_ext = ext

    if first_hit_idx is None or hit_ext is None:
        return None

    cut_at = first_hit_idx + len(hit_ext)  # posición justo después de la extensión

    # Si el nombre ya termina exactamente en la extensión, no hay cambios
    if cut_at == len(filename):
        return None

    # En cualquier otro caso, recortamos hasta la extensión (elimina "_PRO" y cualquier sufijo)
    new_name = filename[:cut_at]

    # Normalizamos el casing de la extensión a minúsculas (opcional, pero consistente)
    # Conserva el nombre base tal cual, solo fuerza la extensión a minúsculas.
    base = filename[:first_hit_idx]
    new_name = base + hit_ext  # hit_ext ya está en minúsculas

    return new_name


def main():
    p = argparse.ArgumentParser(
        description=(
            "Renombra archivos para borrar todo lo posterior a '.csv', '.txt', '.xls' y '.pdf' "
            "(incluye casos como *.csv_PRO_* -> *.csv)."
        )
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

        new_name = strip_after_ext(f.name)
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
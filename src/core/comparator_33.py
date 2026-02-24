import os
import re
import unicodedata
from typing import Dict, Any, List, Optional

import pandas as pd


class CSVComparator:
    def __init__(
        self,
        file1_path: str,
        file2_path: str,
        key_columns: Optional[Any] = None,
        ignore_columns: Optional[List[str]] = None,
        separator: str = ';'
    ):
        self.file1_path = file1_path
        self.file2_path = file2_path
        self.separator = separator

        # Normaliza key_columns a lista
        if isinstance(key_columns, str):
            self.key_columns = [k.strip() for k in key_columns.split(',')]
        else:
            self.key_columns = key_columns

        self.ignore_columns = ignore_columns if ignore_columns else []

        self.df1: Optional[pd.DataFrame] = None
        self.df2: Optional[pd.DataFrame] = None
        self.errors: List[str] = []
        self.differences: List[str] = []
        self.structured_differences: List[Dict[str, Any]] = []

    # ---------------------------
    # Utilidades de normalización
    # ---------------------------
    def _normalize_unicode_cell(self, v: Any) -> str:
        """Normaliza texto a NFC, reemplaza NBSP por espacio normal y colapsa espacios."""
        if pd.isna(v):
            return ""
        s = str(v)
        # Normaliza forma canónica (evita diferencias por acentos compuestos)
        s = unicodedata.normalize('NFC', s)
        # Reemplaza NBSP por espacio normal
        s = s.replace('\u00A0', ' ')
        # Colapsa espacios y recorta
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.applymap(self._normalize_unicode_cell)

    def _normalize_val(self, val: Any) -> str:
        """Normaliza valor para comparación estricta (no iguala 80.0 y 80)."""
        if pd.isna(val):
            return ""
        s = str(val).strip()
        s = unicodedata.normalize('NFC', s).replace('\u00A0', ' ')
        return s

    def _report_replacement_chars(self, df: pd.DataFrame, which: str) -> None:
        """Reporta si el DataFrame trae ya el carácter de reemplazo U+FFFD (�)."""
        try:
            mask = df.astype(str).apply(lambda col: col.str.contains('\uFFFD', na=False))
            count = int(mask.values.sum())
            if count > 0:
                self.differences.append(
                    f"Advertencia: Se encontraron caracteres de reemplazo '�' en {which} en {count} celdas."
                )
                self.structured_differences.append({
                    "type": "replacement_char_warning",
                    "file": which,
                    "count": count
                })
        except Exception:
            # No bloquear por diagnósticos
            pass

    # ---------------------------
    # Lectura robusta de CSV
    # ---------------------------
    def _read_csv_robust(self, filepath: str) -> pd.DataFrame:
        """
        Lee CSV probando varias codificaciones SIN reemplazar caracteres.
        Si ninguna funciona, levanta excepción. Evita introducir U+FFFD.
        """
        encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin1', 'iso-8859-1']
        last_exc: Optional[Exception] = None

        for enc in encodings:
            # Intento con pandas >= 2 (encoding_errors)
            try:
                return pd.read_csv(
                    filepath,
                    dtype=str,
                    sep=self.separator,
                    encoding=enc,
                    encoding_errors='strict'  # type: ignore[arg-type]
                )
            except TypeError:
                # pandas < 2: validar con open() en modo estricto
                try:
                    with open(filepath, 'r', encoding=enc) as _f:
                        _ = _f.read(1024)  # fuerza decodificación temprana
                    return pd.read_csv(filepath, dtype=str, sep=self.separator, encoding=enc)
                except Exception as e:
                    last_exc = e
                    continue
            except Exception as e:
                last_exc = e
                continue

        # Si nada funcionó, fallar explícitamente
        fname = os.path.basename(filepath)
        raise UnicodeDecodeError("codec", b"", 0, 1,
                                 f"No se pudo decodificar {fname} con {encodings}. Último error: {last_exc}")

    # ---------------------------
    # Flujo principal
    # ---------------------------
    def load_files(self) -> bool:
        """Carga los CSV en DataFrames, aplica exclusiones y normalización."""
        if not os.path.exists(self.file1_path):
            self.errors.append(f"File not found: {self.file1_path}")
            return False
        if not os.path.exists(self.file2_path):
            self.errors.append(f"File not found: {self.file2_path}")
            return False

        try:
            self.df1 = self._read_csv_robust(self.file1_path)
            self.df2 = self._read_csv_robust(self.file2_path)

            # Eliminar columnas ignoradas (si existen)
            if self.ignore_columns:
                self.df1.drop(columns=self.ignore_columns, errors='ignore', inplace=True)
                self.df2.drop(columns=self.ignore_columns, errors='ignore', inplace=True)

            # Normalización Unicode a nivel de DataFrame
            self.df1 = self._normalize_dataframe(self.df1)
            self.df2 = self._normalize_dataframe(self.df2)

            # Diagnóstico: ¿ya venían '�' en los datos?
            self._report_replacement_chars(self.df1, "File 1")
            self._report_replacement_chars(self.df2, "File 2")

            return True
        except Exception as e:
            self.errors.append(f"Error loading files: {str(e)}")
            return False

    def validate_headers(self) -> bool:
        """Compara headers (conteo y nombres) y valida existencia de llaves."""
        if self.df1 is None or self.df2 is None:
            return False

        headers1 = list(self.df1.columns)
        headers2 = list(self.df2.columns)

        # Validar columnas llave
        if self.key_columns:
            key_missing = False
            for k in self.key_columns:
                if k not in headers1:
                    self.errors.append(f"Key column '{k}' not found in File 1 headers.")
                    key_missing = True
                if k not in headers2:
                    self.errors.append(f"Key column '{k}' not found in File 2 headers.")
                    key_missing = True
            if key_missing:
                return False

        headers_match = True

        if len(headers1) != len(headers2):
            self.differences.append(
                f"Header count mismatch: File 1 has {len(headers1)}, File 2 has {len(headers2)}"
            )
            self.structured_differences.append({
                "type": "header_count_mismatch",
                "file1_count": len(headers1),
                "file2_count": len(headers2)
            })
            headers_match = False

        if headers1 != headers2:
            self.differences.append(f"Header name mismatch:\nFile 1: {headers1}\nFile 2: {headers2}")
            self.structured_differences.append({
                "type": "header_name_mismatch",
                "file1_headers": headers1,
                "file2_headers": headers2
            })
            headers_match = False

        return headers_match

    def validate_key_uniqueness(self) -> bool:
        """Valida que las llaves sean únicas en ambos archivos."""
        if self.key_columns is None:
            return True

        unique = True

        # File 1
        if self.df1 is not None:
            dupes1 = self.df1[self.df1.duplicated(subset=self.key_columns, keep=False)]
            if not dupes1.empty:
                if len(self.key_columns) == 1:
                    ids = dupes1[self.key_columns[0]].unique().tolist()
                else:
                    ids = dupes1[self.key_columns].drop_duplicates().apply(tuple, axis=1).tolist()
                ids_preview = str(ids[:5]) + "..." if len(ids) > 5 else str(ids)
                self.errors.append(f"Duplicate keys found in File 1. Count: {len(dupes1)}. IDs: {ids_preview}")
                self.structured_differences.append({
                    "type": "duplicate_keys",
                    "file": self.file1_path,
                    "count": len(dupes1),
                    "ids": [str(x) for x in ids],
                    "full_rows": dupes1.to_dict('records')
                })
                unique = False

        # File 2
        if self.df2 is not None:
            dupes2 = self.df2[self.df2.duplicated(subset=self.key_columns, keep=False)]
            if not dupes2.empty:
                if len(self.key_columns) == 1:
                    ids = dupes2[self.key_columns[0]].unique().tolist()
                else:
                    ids = dupes2[self.key_columns].drop_duplicates().apply(tuple, axis=1).tolist()
                ids_preview = str(ids[:5]) + "..." if len(ids) > 5 else str(ids)
                self.errors.append(f"Duplicate keys found in File 2. Count: {len(dupes2)}. IDs: {ids_preview}")
                self.structured_differences.append({
                    "type": "duplicate_keys",
                    "file": self.file2_path,
                    "count": len(dupes2),
                    "ids": [str(x) for x in ids],
                    "full_rows": dupes2.to_dict('records')
                })
                unique = False

        return unique

    def compare_records(self) -> bool:
        """Compara registros con o sin llave."""
        if self.df1 is None or self.df2 is None:
            return False

        if self.key_columns:
            return self._compare_with_key()
        return self._compare_positional()

    def _compare_with_key(self) -> bool:
        merged = pd.merge(
            self.df1, self.df2,
            on=self.key_columns, how='outer',
            indicator=True, suffixes=('_f1', '_f2')
        )

        # 1) Faltantes (en file1, no en file2)
        missing = merged[merged['_merge'] == 'left_only']
        if not missing.empty:
            if len(self.key_columns) == 1:
                ids = missing[self.key_columns[0]].tolist()
            else:
                ids = missing[self.key_columns].apply(tuple, axis=1).tolist()
            try:
                ids.sort()
            except Exception:
                pass

            missing_keys_df = missing[self.key_columns].drop_duplicates()
            full_rows_df = pd.merge(self.df1, missing_keys_df, on=self.key_columns, how='inner')
            full_rows = full_rows_df.to_dict('records')

            self.differences.append(
                f"Missing records (in File 1 but not File 2): {len(ids)} records. IDs: {ids[:10]}..."
            )
            self.structured_differences.append({
                "type": "missing_records",
                "exclusive_to_file": self.file1_path,
                "count": len(ids),
                "ids": [str(x) for x in ids],
                "full_rows": full_rows
            })

        # 2) Adicionales (en file2, no en file1)
        additional = merged[merged['_merge'] == 'right_only']
        if not additional.empty:
            if len(self.key_columns) == 1:
                ids = additional[self.key_columns[0]].tolist()
            else:
                ids = additional[self.key_columns].apply(tuple, axis=1).tolist()
            try:
                ids.sort()
            except Exception:
                pass

            additional_keys_df = additional[self.key_columns].drop_duplicates()
            full_rows_df = pd.merge(self.df2, additional_keys_df, on=self.key_columns, how='inner')
            full_rows = full_rows_df.to_dict('records')

            self.differences.append(
                f"Additional records (in File 2 but not File 1): {len(ids)} records. IDs: {ids[:10]}..."
            )
            self.structured_differences.append({
                "type": "additional_records",
                "exclusive_to_file": self.file2_path,
                "count": len(ids),
                "ids": [str(x) for x in ids],
                "full_rows": full_rows
            })

        # 3) Comparar contenido de los comunes
        common = merged[merged['_merge'] == 'both'].copy()

        cols1 = set(self.df1.columns)
        cols2 = set(self.df2.columns)
        common_columns = cols1.intersection(cols2)
        columns_to_check = [c for c in common_columns if c not in self.key_columns]

        skipped_cols = (cols1.union(cols2)) - common_columns
        if skipped_cols:
            self.differences.append(f"Skipping comparison for mismatched columns: {list(skipped_cols)}")

        if columns_to_check:
            is_diff_mask = pd.Series([False] * len(common), index=common.index)
            norm_cols_f1: Dict[str, pd.Series] = {}
            norm_cols_f2: Dict[str, pd.Series] = {}

            for col in columns_to_check:
                col_f1 = f"{col}_f1"
                col_f2 = f"{col}_f2"
                s1 = common[col_f1].apply(self._normalize_val)
                s2 = common[col_f2].apply(self._normalize_val)
                norm_cols_f1[col] = s1
                norm_cols_f2[col] = s2
                is_diff_mask |= (s1 != s2)

            diff_rows = common[is_diff_mask]

            for idx, row in diff_rows.iterrows():
                if len(self.key_columns) == 1:
                    key_val = str(row[self.key_columns[0]])
                else:
                    key_val = str(tuple(row[k] for k in self.key_columns))

                row_cell_diffs = []
                for col in columns_to_check:
                    val1_norm = norm_cols_f1[col][idx]
                    val2_norm = norm_cols_f2[col][idx]
                    if val1_norm != val2_norm:
                        self.differences.append(f"   Key '{key_val}', Col '{col}': '{val1_norm}' != '{val2_norm}'")
                        row_cell_diffs.append({
                            "col": col,
                            "file1_value": val1_norm,
                            "file2_value": val2_norm
                        })

                row_f1 = {k: row[k] for k in self.key_columns}
                row_f2 = {k: row[k] for k in self.key_columns}
                for col in common_columns:
                    if col in self.key_columns:
                        continue
                    row_f1[col] = row.get(f"{col}_f1")
                    row_f2[col] = row.get(f"{col}_f2")

                self.structured_differences.append({
                    "type": "content_mismatch",
                    "key": key_val,
                    "diff_count": len(row_cell_diffs),
                    "cell_diffs": row_cell_diffs,
                    "full_row_file1": row_f1,
                    "full_row_file2": row_f2
                })

        has_content_diffs = any(d['type'] == 'content_mismatch' for d in self.structured_differences)
        return missing.empty and additional.empty and not has_content_diffs

    def _compare_positional(self) -> bool:
        if self.df1 is None or self.df2 is None:
            return False

        if self.df1.shape != self.df2.shape:
            self.differences.append(f"Shape mismatch: File 1 {self.df1.shape}, File 2 {self.df2.shape}")
            self.structured_differences.append({
                "type": "shape_mismatch",
                "file1_shape": self.df1.shape,
                "file2_shape": self.df2.shape
            })

        try:
            comparison = self.df1.equals(self.df2)
            if not comparison:
                self.differences.append("Content mismatch found in records.")
                diff_mask = (self.df1 != self.df2) & ~(self.df1.isnull() & self.df2.isnull())
                if self.df1.shape == self.df2.shape:
                    stacked_diff = diff_mask.stack()
                    changed = stacked_diff[stacked_diff]
                    if not changed.empty:
                        self.differences.append(f"Found {len(changed)} specific cell differences.")
                        cell_diffs = []
                        for idx, _ in changed.head(50).items():
                            row_idx, col_name = idx
                            val1 = self.df1.at[row_idx, col_name]
                            val2 = self.df2.at[row_idx, col_name]
                            self.differences.append(f"   Row {row_idx}, Col '{col_name}': '{val1}' != '{val2}'")
                            cell_diffs.append({
                                "row": int(row_idx),
                                "col": col_name,
                                "file1_value": str(val1),
                                "file2_value": str(val2)
                            })
                        self.structured_differences.append({
                            "type": "content_mismatch",
                            "diff_count": len(changed),
                            "details": cell_diffs
                        })
            return comparison
        except Exception as e:
            self.errors.append(f"Error during record comparison: {str(e)}")
            return False

    def run_comparison(self) -> Dict[str, Any]:
        """Ejecuta validaciones y comparación, devolviendo resumen y detalle."""
        if not self.load_files():
            return {"success": False, "errors": self.errors, "differences": [], "structured_differences": []}

        headers_ok = self.validate_headers()

        # Errores fatales por llaves
        is_fatal = False
        if self.key_columns:
            if any("Key column" in err for err in self.errors):
                is_fatal = True

        # Unicidad de llave (crítico)
        if not is_fatal and self.key_columns:
            if not self.validate_key_uniqueness():
                is_fatal = True

        records_ok = False
        if not is_fatal:
            records_ok = self.compare_records()

        total_f1 = len(self.df1) if self.df1 is not None else 0
        total_f2 = len(self.df2) if self.df2 is not None else 0

        missing_count = 0
        additional_count = 0
        content_diff_rows = 0

        for d in self.structured_differences:
            if d['type'] == 'missing_records':
                missing_count = d['count']
            elif d['type'] == 'additional_records':
                additional_count = d['count']
            elif d['type'] == 'content_mismatch':
                content_diff_rows += 1

        matching_rows = 0
        if self.key_columns and self.df1 is not None:
            matching_rows = total_f1 - missing_count

        match_pct = 0.0
        if (total_f1 + additional_count) > 0:
            universe = total_f1 + additional_count
            match_pct = round((matching_rows / universe) * 100, 2)

        summary = {
            "total_rows_file1": total_f1,
            "total_rows_file2": total_f2,
            "missing_records": missing_count,
            "additional_records": additional_count,
            "rows_with_differences": content_diff_rows,
            "matching_rows_perfect": matching_rows - content_diff_rows,
            "matching_percentage": match_pct
        }

        success = headers_ok and records_ok and not self.errors and not self.differences

        return {
            "success": success,
            "summary": summary,
            "errors": self.errors,
            "differences": self.differences,
            "structured_differences": self.structured_differences
        }
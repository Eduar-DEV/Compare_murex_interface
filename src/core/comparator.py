import pandas as pd
from typing import Dict, Any, List, Optional
import os

class CSVComparator:
    def __init__(self, file1_path: str, file2_path: str, key_columns: Optional[Any] = None, ignore_columns: Optional[List[str]] = None):
        self.file1_path = file1_path
        self.file2_path = file2_path
        # Normalize key_columns to list
        if isinstance(key_columns, str):
            self.key_columns = [k.strip() for k in key_columns.split(',')]
        else:
            self.key_columns = key_columns
            
        self.ignore_columns = ignore_columns if ignore_columns else []
        
        self.df1 = None
        self.df2 = None
        self.errors = []
        self.differences = []
        self.structured_differences = []

    def load_files(self) -> bool:
        """Loads the CSV files into pandas DataFrames."""
        if not os.path.exists(self.file1_path):
            self.errors.append(f"File not found: {self.file1_path}")
            return False
        if not os.path.exists(self.file2_path):
            self.errors.append(f"File not found: {self.file2_path}")
            return False

        try:
            # Read as string to preserve exact formatting (e.g. 80 vs 80.0)
            self.df1 = pd.read_csv(self.file1_path, dtype=str)
            self.df2 = pd.read_csv(self.file2_path, dtype=str)
            
            # Drop ignored columns
            if self.ignore_columns:
                self.df1.drop(columns=self.ignore_columns, errors='ignore', inplace=True)
                self.df2.drop(columns=self.ignore_columns, errors='ignore', inplace=True)
            
            return True
        except Exception as e:
            self.errors.append(f"Error loading files: {str(e)}")
            return False

    def validate_headers(self) -> bool:
        """Compares headers of both files (count and names)."""
        if self.df1 is None or self.df2 is None:
            return False

        headers1 = list(self.df1.columns)
        headers2 = list(self.df2.columns)
        
        # Check if key column exists (Critical for key-based comparison)
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

        # General header comparison (Non-critical, just report differences)
        headers_match = True
        
        if len(headers1) != len(headers2):
            self.differences.append(f"Header count mismatch: File 1 has {len(headers1)}, File 2 has {len(headers2)}")
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

    def compare_records(self) -> bool:
        """Compares the records of both files."""
        if self.df1 is None or self.df2 is None:
            return False

        # Key-based comparison
        if self.key_columns:
            return self._compare_with_key()
            
        # Positional comparison (Legacy/Default)
        return self._compare_positional()

    def _normalize_val(self, val: Any) -> str:
        """
        Normalize value for comparison.
        Strict Mode: Returns string representation stripped of whitespace.
        "80.0" and "80" are DIFFERENT.
        """
        if pd.isna(val):
            return ""
        return str(val).strip()

    def _compare_with_key(self) -> bool:
        merged = pd.merge(self.df1, self.df2, on=self.key_columns, how='outer', indicator=True, suffixes=('_f1', '_f2'))
        
        # 1. Identify Missing records (present in file1, missing in file2) -> left_only
        missing = merged[merged['_merge'] == 'left_only']
        if not missing.empty:
            # Get IDs for summary
            if len(self.key_columns) == 1:
                ids = missing[self.key_columns[0]].tolist()
            else:
                ids = missing[self.key_columns].apply(tuple, axis=1).tolist()
            
            try:
                ids.sort()
            except:
                pass 
            
            # Retrieve full rows from DF1
            # We filter DF1 to get exact original data
            missing_keys_df = missing[self.key_columns].drop_duplicates()
            full_rows_df = pd.merge(self.df1, missing_keys_df, on=self.key_columns, how='inner')
            full_rows = full_rows_df.to_dict('records')

            self.differences.append(f"Missing records (in File 1 but not File 2): {len(ids)} records. IDs: {ids[:10]}...")
            self.structured_differences.append({
                "type": "missing_records", # Present in file1, missing in file2
                "exclusive_to_file": self.file1_path,
                "count": len(ids),
                "ids": [str(x) for x in ids],
                "full_rows": full_rows
            })

        # 2. Identify Additional records (missing in file1, present in file2) -> right_only
        additional = merged[merged['_merge'] == 'right_only']
        if not additional.empty:
            # Get IDs for summary
            if len(self.key_columns) == 1:
                ids = additional[self.key_columns[0]].tolist()
            else:
                ids = additional[self.key_columns].apply(tuple, axis=1).tolist()

            try:
                ids.sort()
            except:
                pass
            
            # Retrieve full rows from DF2
            additional_keys_df = additional[self.key_columns].drop_duplicates()
            full_rows_df = pd.merge(self.df2, additional_keys_df, on=self.key_columns, how='inner')
            full_rows = full_rows_df.to_dict('records')
                
            self.differences.append(f"Additional records (in File 2 but not File 1): {len(ids)} records. IDs: {ids[:10]}...")
            self.structured_differences.append({
                "type": "additional_records", # Present in file2, missing in file1
                "exclusive_to_file": self.file2_path,
                "count": len(ids),
                "ids": [str(x) for x in ids],
                "full_rows": full_rows
            })

        # 3. Compare content of common records
        common = merged[merged['_merge'] == 'both'].copy()
        
        # Intersect columns to avoid errors if headers mismatch
        cols1 = set(self.df1.columns)
        cols2 = set(self.df2.columns)
        common_columns = cols1.intersection(cols2)
        columns_to_check = [c for c in common_columns if c not in self.key_columns]
        
        # Warn about skipped columns if any
        skipped_cols = (cols1.union(cols2)) - common_columns
        if skipped_cols:
            self.differences.append(f"Skipping comparison for mismatched columns: {list(skipped_cols)}")
            
        if not columns_to_check:
             # No content columns to check
             pass
        else:
             # Identify rows with ANY difference
             # We need to apply normalization to compare correctly
             is_diff_mask = pd.Series([False] * len(common), index=common.index)
             
             # Store normalized series to avoid re-computing
             norm_cols_f1 = {}
             norm_cols_f2 = {}
             
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
                 # 1. Build Key Representation
                 if len(self.key_columns) == 1:
                     key_val = str(row[self.key_columns[0]])
                 else:
                     key_val = str(tuple(row[k] for k in self.key_columns))
                 
                 # 2. Identify specific cell diffs
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
                 
                 # 3. Construct Full Rows (Raw values)
                 # We need to grab columns ending in _f1 and _f2 and map them back to original names
                 # Also include the key columns!
                 row_f1 = {k: row[k] for k in self.key_columns}
                 row_f2 = {k: row[k] for k in self.key_columns}
                 
                 for col in common_columns: 
                     if col in self.key_columns: continue
                     row_f1[col] = row[f"{col}_f1"]
                     row_f2[col] = row[f"{col}_f2"]
                     
                 # 4. Append Structured Diff
                 self.structured_differences.append({
                     "type": "content_mismatch",
                     "key": key_val,
                     "diff_count": len(row_cell_diffs),
                     "cell_diffs": row_cell_diffs,
                     "full_row_file1": row_f1,
                     "full_row_file2": row_f2
                 })

        # Return True if no differences (missing, additional, or content)
        # We check structured_differences for any content_mismatch types
        has_content_diffs = any(d['type'] == 'content_mismatch' for d in self.structured_differences)
        return missing.empty and additional.empty and not has_content_diffs

    def _compare_positional(self) -> bool:
        # First check shape
        if self.df1.shape != self.df2.shape:
             self.differences.append(f"Shape mismatch: File 1 {self.df1.shape}, File 2 {self.df2.shape}")
             self.structured_differences.append({
                 "type": "shape_mismatch",
                 "file1_shape": self.df1.shape,
                 "file2_shape": self.df2.shape
             })
             # We can still attempt comparison but it's a major diff
        
        # Check for equality
        try:
            # We enforce string comparison to avoid subtle float diffs for MVP if needed, 
            # but pandas eq is good start.
            comparison = self.df1.equals(self.df2)
            if not comparison:
                self.differences.append("Content mismatch found in records.")
                
                # Simple logic to find WHERE
                # This is an MVP approach.
                diff_mask = (self.df1 != self.df2) & ~(self.df1.isnull() & self.df2.isnull())
                if self.df1.shape == self.df2.shape:
                    stacked_diff = diff_mask.stack()
                    changed = stacked_diff[stacked_diff]
                    if not changed.empty:
                        self.differences.append(f"Found {len(changed)} specific cell differences.")
                        
                        cell_diffs = []
                        # Could list first few
                        for idx, val in changed.head(50).items(): # Increased limit for json
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
        """Runs the full comparison and returns results."""
        if not self.load_files():
            return {"success": False, "errors": self.errors, "differences": [], "structured_differences": []}

        headers_ok = self.validate_headers()
        
        # Check if we have fatal errors (like missing key column)
        is_fatal = False
        if self.key_columns:
             if any("Key column" in err for err in self.errors):
                 is_fatal = True
        
        records_ok = False
        if not is_fatal:
            records_ok = self.compare_records()
        
        # Calculate summary statistics
        total_f1 = len(self.df1) if self.df1 is not None else 0
        total_f2 = len(self.df2) if self.df2 is not None else 0
        
        missing_count = 0
        additional_count = 0
        content_diff_rows = 0 # Distinct rows with differences
        
        for d in self.structured_differences:
            if d['type'] == 'missing_records':
                missing_count = d['count']
            elif d['type'] == 'additional_records':
                additional_count = d['count']
            elif d['type'] == 'content_mismatch':
                # Now each entry is one row with difference
                content_diff_rows += 1
        
        # Matching rows logic (approximate for MVP, assuming Key-based)
        # For positional, this logic might need adjustment but serves well for Murex scope.
        # Ideally, matching_rows = (Total Unique Keys in Common)
        # Total Unique Keys = (Total F1 - Missing) or (Total F2 - Additional)
        # If headers/load failed, we can't truly say.
        
        matching_rows = 0
        if self.key_columns and self.df1 is not None:
             matching_rows = total_f1 - missing_count
             
        match_pct = 0.0
        if (total_f1 + additional_count) > 0:
             # Total Universe of Keys = F1 + Additional
             universe = total_f1 + additional_count
             match_pct = round((matching_rows / universe) * 100, 2)

        summary = {
            "total_rows_file1": total_f1,
            "total_rows_file2": total_f2,
            "missing_records": missing_count,
            "additional_records": additional_count,
            "rows_with_differences": content_diff_rows,
            "matching_rows_perfect": matching_rows - content_diff_rows, # Rows with NO differences
            "matching_percentage": match_pct
        }

        # Overall success is True only if everything is perfect
        success = headers_ok and records_ok and not self.errors and not self.differences
        
        return {
            "success": success,
            "summary": summary,
            "errors": self.errors,
            "differences": self.differences,
            "structured_differences": self.structured_differences
        }

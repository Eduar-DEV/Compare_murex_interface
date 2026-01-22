import json
import os
import argparse
import datetime
import pandas as pd
from typing import List, Dict, Optional, Any
from src.core.comparator import CSVComparator
from src.reporting.excel_reporter import generate_excel_report

class BatchOrchestrator:
    def __init__(self, dir_a: str, dir_b: str, output_dir: str, keys: List[str] = None, ignore_columns: List[str] = None, config_file: str = None):
        self.dir_a = dir_a
        self.dir_b = dir_b
        self.output_dir = output_dir
        self.keys = keys if keys else []
        self.ignore_columns = ignore_columns if ignore_columns else []
        self.config_file = config_file
        self.config = self._load_config()
        self.results_summary = []
        
        # Create output directory with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.batch_output_dir = os.path.join(self.output_dir, f"batch_{timestamp}")
        self.details_dir = os.path.join(self.batch_output_dir, "details")
        
        os.makedirs(self.batch_output_dir, exist_ok=True)
        os.makedirs(self.details_dir, exist_ok=True)
        
        # Initialize Log File
        self.log_file = os.path.join(self.batch_output_dir, "execution.log")
        with open(self.log_file, 'w') as f:
            f.write(f"Batch Execution Started: {timestamp}\n")
            f.write(f"Source A: {dir_a}\nSource B: {dir_b}\n")
            f.write(f"Config File: {self.config_file}\n")
            if not self.config_file:
                f.write(f"Default Keys (CLI): {self.keys}\n")
            f.write(f"Ignore Cols: {self.ignore_columns}\n\n")

    def _load_config(self) -> Optional[Dict[str, Any]]:
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARNING] Failed to load config file: {e}")
                return None
        return None

    def log(self, message: str):
        print(message)
        with open(self.log_file, 'a') as f:
            f.write(f"{datetime.datetime.now().strftime('%H:%M:%S')} - {message}\n")

    def _resolve_file_config(self, filename: str) -> (List[str], List[str]):
        """
        Resolves the configuration (keys, ignore_columns) for a specific file.
        Priority: 1. Rule Pattern -> 2. Config Default -> 3. CLI Args
        """
        resolved_keys = self.keys
        resolved_ignore = self.ignore_columns
        
        if self.config:
            # 1. Defaults from config (override CLI)
            if "default_keys" in self.config:
                resolved_keys = self.config["default_keys"]
            if "default_ignore_columns" in self.config:
                resolved_ignore = self.config["default_ignore_columns"]

            # 2. Rules from config (override defaults)
            for rule in self.config.get("rules", []):
                pattern = rule.get("pattern", "")
                if pattern and filename.startswith(pattern):
                    if "keys" in rule:
                        resolved_keys = rule["keys"]
                    if "ignore_columns" in rule:
                        resolved_ignore = rule["ignore_columns"]
                    break
        
        return resolved_keys, resolved_ignore

    def run(self):
        self.log("Scanning directory A...")
        files_a = [f for f in os.listdir(self.dir_a) if f.lower().endswith('.csv')]
        files_a.sort()
        
        total_files = len(files_a)
        self.log(f"Found {total_files} files in Source A.")
        
        for idx, filename in enumerate(files_a, 1):
            path_a = os.path.join(self.dir_a, filename)
            path_b = os.path.join(self.dir_b, filename)
            
            # Resolve config specifically for this file
            current_keys, current_ignore = self._resolve_file_config(filename)
            
            self.log(f"[{idx}/{total_files}] Processing {filename} (Keys: {current_keys}, Ignore: {current_ignore})...")
            
            result_entry = {
                "File Name": filename,
                "Status": "UNKNOWN",
                "Keys Used": ", ".join(current_keys),
                "Total Rows A": 0,
                "Total Rows B": 0,
                "Diff Count": 0,
                "Missing Records": 0,
                "Additional Records": 0,
                "Detail Report": ""
            }
            
            if not current_keys:
                 self.log(f"  [ERROR] No keys defined for this file. Skipping.")
                 result_entry["Status"] = "NO_KEYS"
                 self.results_summary.append(result_entry)
                 continue
            
            if not os.path.exists(path_b):
                self.log(f"  [MISSING] Target file not found in B: {path_b}")
                result_entry["Status"] = "MISSING_IN_B"
                self.results_summary.append(result_entry)
                continue
                
            try:
                # Initialize Comparator
                comparator = CSVComparator(path_a, path_b, key_columns=current_keys, ignore_columns=current_ignore)
                comparison_results = comparator.run_comparison()
                
                # Extract Stats
                summary = comparison_results.get("summary", {})
                result_entry["Total Rows A"] = summary.get("total_rows_file1", 0)
                result_entry["Total Rows B"] = summary.get("total_rows_file2", 0)
                result_entry["Missing Records"] = summary.get("missing_records", 0)
                result_entry["Additional Records"] = summary.get("additional_records", 0)
                result_entry["Diff Count"] = summary.get("matching_records_with_differences", 0)
                
                # Determine Status
                errors = comparison_results.get("errors", [])
                
                if errors:
                    # Generic Error Status
                    result_entry["Status"] = "ERROR"
                    error_msg = "; ".join(errors)
                    
                    # 1. Check for specific "Key Not Found" error
                    if any("Key column" in err and "not found" in err for err in errors):
                        result_entry["Status"] = "KEY_NOT_FOUND"
                        self.log(f"  [KEY ERROR] {error_msg}")
                    
                    # 2. Check for Duplicate Keys
                    elif any("Duplicate keys" in err for err in errors):
                        result_entry["Status"] = "DUPLICATE_KEYS"
                        self.log(f"  [DUPLICATE ERROR] {error_msg}")
                        
                        # Generate Detail Report for Duplicates
                        detail_filename = f"report_{filename.replace('.csv', '.xlsx')}"
                        detail_path = os.path.join(self.details_dir, detail_filename)
                        generate_excel_report(comparison_results, detail_path)
                        result_entry["Detail Report"] = detail_filename
                        self.log(f"  [INFO] Excel report generated: {detail_filename}")
                        
                    else:
                        self.log(f"  [ERROR] Comparison failed: {error_msg}")
                        
                    result_entry["Notes"] = error_msg
                elif comparison_results["success"]:
                    result_entry["Status"] = "OK"
                    self.log(f"  [OK] Files match perfectly.")
                else:
                    result_entry["Status"] = "DIFF"
                    self.log(f"  [DIFF] Differences found (M:{result_entry['Missing Records']}, A:{result_entry['Additional Records']}, D:{result_entry['Diff Count']})")
                    
                    # Generate Detail Report logic
                    detail_filename = f"report_{filename.replace('.csv', '.xlsx')}"
                    detail_path = os.path.join(self.details_dir, detail_filename)
                    generate_excel_report(comparison_results, detail_path)
                    result_entry["Detail Report"] = detail_filename
                    self.log(f"  [INFO] Excel report generated: {detail_filename}")
                    
            except Exception as e:
                self.log(f"  [EXCEPTION] Error processing file: {str(e)}")
                result_entry["Status"] = "EXCEPTION"
                
            self.results_summary.append(result_entry)
            
        self._generate_master_report()
        self.log("\nBatch Execution Completed.")
        self.log(f"Master report saved to: {os.path.join(self.batch_output_dir, 'summary_report.xlsx')}")

    def _generate_master_report(self):
        df_summary = pd.DataFrame(self.results_summary)
        output_path = os.path.join(self.batch_output_dir, "summary_report.xlsx")
        
        # Simple Excel writer
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Batch Summary', index=False)
            
            # Auto-adjust columns (basic)
            ws = writer.sheets['Batch Summary']
            for column_cells in ws.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                ws.column_dimensions[column_cells[0].column_letter].width = length + 2

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch CSV Comparator Orchestrator")
    parser.add_argument("--dir-a", required=True, help="Directory containing Source A CSV files")
    parser.add_argument("--dir-b", required=True, help="Directory containing Source B CSV files")
    parser.add_argument("--output", default="results", help="Base output directory")
    parser.add_argument("--key", help="Comma-separated key columns (default fallback)", default=None)
    parser.add_argument("--ignore-columns", help="Column name(s) to ignore during comparison (comma separated)", default=None)
    parser.add_argument("--config", help="Path to JSON configuration file for dynamic keys", default=None)
    
    args = parser.parse_args()
    
    keys = []
    if args.key:
        keys = [k.strip() for k in args.key.split(',')]
    
    ignore_cols = None
    if args.ignore_columns:
        ignore_cols = [c.strip() for c in args.ignore_columns.split(',')]
    
    orchestrator = BatchOrchestrator(args.dir_a, args.dir_b, args.output, keys, ignore_columns=ignore_cols, config_file=args.config)
    orchestrator.run()

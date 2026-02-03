
import os
import argparse
import json
import logging
import pandas as pd
from typing import Dict, List, Optional
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        sys.exit(1)

def get_keys_for_file(filename: str, config: Dict) -> List[str]:
    """Determine expected keys for a file based on config rules."""
    rules = config.get("rules", [])
    for rule in rules:
        if rule.get("pattern") in filename:
            return rule.get("keys", [])
    return config.get("default_keys", [])

def validate_csv_header(file_path: str, expected_keys: List[str], separator: str = ";") -> Dict:
    """
    Validate headers of a single CSV file.
    Returns a dictionary with status and details.
    """
    try:
        # Read only the header
        df = pd.read_csv(file_path, sep=separator, nrows=0)
        headers = list(df.columns)
        
        missing_keys = [key for key in expected_keys if key not in headers]
        
        if missing_keys:
            return {
                "status": "NOK",
                "reason": f"Missing required keys: {', '.join(missing_keys)}",
                "headers": str(headers)
            }
        
        return {
            "status": "OK",
            "reason": "All required keys present",
            "headers": str(headers)
        }
            
    except Exception as e:
        return {
            "status": "ERROR",
            "reason": str(e),
            "headers": ""
        }

def validate_pair(file_a: str, file_b: str, separator: str = ";") -> Dict:
    """
    Validate that headers of file_a and file_b are identical.
    """
    try:
        # Read headers
        df_a = pd.read_csv(file_a, sep=separator, nrows=0)
        df_b = pd.read_csv(file_b, sep=separator, nrows=0)
        
        header_a = list(df_a.columns)
        header_b = list(df_b.columns)
        
        if header_a != header_b:
             return {
                "match": False,
                "reason": "Headers do not match between Source A and Source B",
                "diff": f"A: {header_a} | B: {header_b}"
            }
            
        return {"match": True, "reason": "Headers match"}
        
    except Exception as e:
        return {
            "match": False,
            "reason": f"Error comparing files: {str(e)}",
            "diff": ""
        }

def main():
    parser = argparse.ArgumentParser(description="Validate CSV headers before processing.")
    parser.add_argument("--dir-a", required=True, help="Path to directory A")
    parser.add_argument("--dir-b", required=True, help="Path to directory B")
    parser.add_argument("--config", required=True, help="Path to configuration JSON")
    parser.add_argument("--output", required=True, help="Output directory for report")
    parser.add_argument("--separator", default=";", help="CSV separator (default: ;)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        
    config = load_config(args.config)
    default_separator = config.get("default_separator", ";")
    if args.separator == ";": # If default was passed, use config if available
         separator = default_separator
    else:
         separator = args.separator

    results = []
    
    # Iterate over files in Directory A
    try:
        files_a = os.listdir(args.dir_a)
    except FileNotFoundError:
        logger.error(f"Directory not found: {args.dir_a}")
        sys.exit(1)

    logger.info(f"Starting validation for {len(files_a)} files...")

    for file_name in files_a:
        if not file_name.endswith('.csv'):
            continue
            
        path_a = os.path.join(args.dir_a, file_name)
        path_b = os.path.join(args.dir_b, file_name)
        
        file_result = {
            "File Name": file_name,
            "Validation Status": "UNKNOWN",
            "Details": ""
        }
        
        # 1. Check if file exists in B
        if not os.path.exists(path_b):
            file_result["Validation Status"] = "NOK"
            file_result["Details"] = "File missing in Source B"
            results.append(file_result)
            continue
            
        # 2. Get Expected Keys
        expected_keys = get_keys_for_file(file_name, config)
        
        # 3. Validate Header Structure (Keys present in A)
        res_a = validate_csv_header(path_a, expected_keys, separator)
        if res_a["status"] != "OK":
            file_result["Validation Status"] = "NOK"
            file_result["Details"] = f"Source A: {res_a['reason']}"
            results.append(file_result)
            continue
            
        # 4. Validate Header Structure (Keys present in B)
        res_b = validate_csv_header(path_b, expected_keys, separator)
        if res_b["status"] != "OK":
            file_result["Validation Status"] = "NOK"
            file_result["Details"] = f"Source B: {res_b['reason']}"
            results.append(file_result)
            continue
            
        # 5. Compare A and B Headers
        res_pair = validate_pair(path_a, path_b, separator)
        if not res_pair["match"]:
            file_result["Validation Status"] = "NOK"
            file_result["Details"] = res_pair["reason"]
            results.append(file_result)
            continue
            
        # Success
        file_result["Validation Status"] = "OK"
        file_result["Details"] = "Headers Valid and Matching"
        results.append(file_result)

    # Generate Report
    report_path = os.path.join(args.output, "header_validation.xlsx")
    df_results = pd.DataFrame(results)
    
    try:
        df_results.to_excel(report_path, index=False)
        logger.info(f"Validation complete. Report generated at: {report_path}")
    except Exception as e:
        logger.error(f"Failed to save Excel report: {e}")
        # Build CSV fallback if Excel fails (e.g. missing openpyxl although it is in deps)
        csv_path = os.path.join(args.output, "header_validation.csv")
        df_results.to_csv(csv_path, index=False)
        logger.info(f"Saved as CSV fallback at: {csv_path}")

if __name__ == "__main__":
    main()

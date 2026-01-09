import json
import os
from datetime import datetime
from typing import Dict, Any

def save_json_report(results: Dict[str, Any], output_arg: str):
    """
    Saves the comparison results to a JSON file.
    Enforces 'results/' directory and appends timestamp to filename.
    """
    try:
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        
        # Add timestamp to filename
        timestamp = datetime.now().strftime("%H%M%S")
        filename_root, filename_ext = os.path.splitext(os.path.basename(output_arg))
        output_filename = f"{filename_root}_{timestamp}{filename_ext}"
        
        output_path = os.path.join(results_dir, output_filename)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"[INFO] JSON results saved to: {output_path}")
    except Exception as e:
        print(f"[ERROR] Failed to write JSON output: {e}")

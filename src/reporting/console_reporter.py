import sys
from typing import Dict, Any

def print_comparison_results(results: Dict[str, Any]):
    """
    Prints comparison results to the console and exits with appropriate code.
    """
    if results["errors"]:
        print("\n[ERROR] Comparison could not completed:")
        for err in results["errors"]:
            print(f"  - {err}")
        sys.exit(1)

    if results["differences"]:
        print("\n[FAIL] Differences found:")
        for diff in results["differences"]:
            print(f"  - {diff}")
        sys.exit(0) # Logic per original main.py
    
    print("\n[SUCCESS] Files are identical.")

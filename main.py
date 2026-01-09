import argparse
from src.core.comparator import CSVComparator
from src.reporting.json_reporter import save_json_report
from src.reporting.console_reporter import print_comparison_results
from src.reporting.excel_reporter import generate_excel_report

def main():
    parser = argparse.ArgumentParser(description="Compare two CSV files.")
    parser.add_argument("file1", help="Path to the first CSV file")
    parser.add_argument("file2", help="Path to the second CSV file")
    parser.add_argument("--output", help="Name of the file to save JSON results (will be saved in 'results/' folder)", default=None)
    parser.add_argument("--key", help="Column name(s) to use as key for record comparison (comma separated)", default=None)
    parser.add_argument("--ignore-columns", help="Column name(s) to ignore during comparison (comma separated)", default=None)
    parser.add_argument("--excel", help="Name of the file to save Excel results (will be saved in 'results/' folder)", default=None)

    args = parser.parse_args()

    print(f"Comparing '{args.file1}' and '{args.file2}'...")
    
    # Process comma-separated lists
    key_params = args.key # Comparator handles splitting logic if string is passed, or we can do it here.
    # The comparator accepts str or list, let's pass str directly or split here for clarity?
    # Comparator updated logic: "if isinstance(key_columns, str): split...". So passing args.key directly works.
    
    ignore_cols = None
    if args.ignore_columns:
        ignore_cols = [c.strip() for c in args.ignore_columns.split(',')]

    comparator = CSVComparator(args.file1, args.file2, key_columns=args.key, ignore_columns=ignore_cols)
    results = comparator.run_comparison()

    if args.output:
        save_json_report(results, args.output)

    if args.excel:
        generate_excel_report(results, args.excel)

    print_comparison_results(results)

if __name__ == "__main__":
    main()

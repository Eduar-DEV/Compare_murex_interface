import os
import random
import pandas as pd
from pathlib import Path

def create_mixed_data():
    base_a = Path("tests/large_mixed_data/server_a")
    base_b = Path("tests/large_mixed_data/server_b")
    
    # Cleanup
    if base_a.exists():
        import shutil
        shutil.rmtree(base_a)
    if base_b.exists():
        import shutil
        shutil.rmtree(base_b)
    
    base_a.mkdir(parents=True, exist_ok=True)
    base_b.mkdir(parents=True, exist_ok=True)

    def save_file(df, path):
        ext = path.suffix.lower()
        if ext == '.xlsx':
            df.to_excel(path, index=False)
        else:
            # Default sep ; for consistent testing unless config differs
            df.to_csv(path, sep=';', index=False)

    print("Generating 100 files with correct schemas...")
    
    for i in range(1, 101):
        filenum = f"{i:03d}"
        
        # Define Schema based on Pattern
        if 1 <= i <= 20:
            prefix = "trade_report"
            ext = ".csv"
            case = "mixed"
            data = {"id": [f"TR_{k}" for k in range(10)], "val": [k for k in range(10)]}
            
        elif 21 <= i <= 40:
            prefix = "cash_flow"
            ext = ".txt"
            case = "header_diff"
            # Keys: account_id, value_date
            data = {
                "account_id": [f"ACC_{k}" for k in range(10)],
                "value_date": ["20250101"] * 10,
                "amount": [100.0 * k for k in range(10)]
            }
            
        elif 41 <= i <= 60:
            prefix = "positions"
            ext = ".xlsx"
            case = "content_diff"
            # Keys: instrument_id
            data = {
                "instrument_id": [f"INS_{k}" for k in range(10)],
                "qty": [1000 * k for k in range(10)]
            }
            
        elif 61 <= i <= 80:
            prefix = "special_report"
            ext = ".csv"
            case = "duplicates"
            # Keys: deal_id
            data = {
                "deal_id": [f"DL_{k}" for k in range(10)],
                "status": ["NEW"] * 10
            }
            
        else:
            prefix = "stress_test"
            ext = random.choice([".csv", ".xlsx", ".txt"])
            case = "ok"
            # Keys: id
            data = {"id": [f"ST_{k}" for k in range(10)], "res": ["PASS"] * 10}

        filename = f"{prefix}_{filenum}{ext}"
        path_a = base_a / filename
        path_b = base_b / filename
        
        df = pd.DataFrame(data)
        
        # Logic
        if case == "ok":
            save_file(df, path_a)
            save_file(df, path_b)
            
        elif case == "mixed":
            sub = i % 4
            if sub == 0: save_file(df, path_a); save_file(df, path_b)
            elif sub == 1: save_file(df, path_a) # Missing in B
            elif sub == 2: save_file(df, path_b) # Missing in A
            elif sub == 3: # Diff
                save_file(df, path_a)
                df.at[0, "val"] = 9999
                save_file(df, path_b)

        elif case == "header_diff":
            save_file(df, path_a)
            df_b = df.copy()
            df_b.rename(columns={"amount": "amt"}, inplace=True)
            save_file(df_b, path_b)

        elif case == "content_diff":
            save_file(df, path_a)
            df_b = df.copy()
            if not df_b.empty:
                col = list(df_b.columns)[-1]
                df_b[col] = df_b[col].astype(str)
                df_b.at[0, col] = "MODIFIED"
            save_file(df_b, path_b)

        elif case == "duplicates":
            # Dup in A
            df_dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
            save_file(df_dup, path_a)
            save_file(df, path_b)

    print("Generation complete.")

if __name__ == "__main__":
    create_mixed_data()

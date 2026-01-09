import pandas as pd
import numpy as np
import os
import random

def generate_data(num_rows=200):
    """Generates a dataframe with synthetic trade data."""
    data = {
        'id': range(1, num_rows + 1),
        'trade_id': [f"TRD_{i:04d}" for i in range(1, num_rows + 1)],
        'notional': np.random.uniform(1000, 1000000, num_rows).round(2),
        'currency': np.random.choice(['USD', 'EUR', 'GBP', 'JPY'], num_rows),
        'counterparty': np.random.choice(['BankA', 'BankB', 'FundC', 'CorpD'], num_rows),
        'status': np.random.choice(['VERIFIED', 'PENDING', 'CANCELLED'], num_rows)
    }
    return pd.DataFrame(data)

def main():
    os.makedirs('tests/data', exist_ok=True)
    
    # 1. Generate Base File
    print("Generating base large file...")
    df_base = generate_data(150) # 150 rows as requested > 100
    df_base.to_csv('tests/data/large_base.csv', index=False)
    
    # 2. Generate Identical File
    print("Generating identical large file...")
    df_base.to_csv('tests/data/large_identical.csv', index=False)
    
    # 3. Generate Diff File (random modifications)
    print("Generating large file with differences...")
    df_diff = df_base.copy()
    
    # Modify 3 random cells
    for _ in range(3):
        row_idx = random.randint(0, 149)
        col = random.choice(['notional', 'currency', 'status'])
        
        original_val = df_diff.at[row_idx, col]
        if col == 'notional':
            new_val = original_val + 100
        else:
            new_val = original_val + "_MOD"
            
        df_diff.at[row_idx, col] = new_val
        print(f"  - Modifying Row {row_idx}, Col {col}: {original_val} -> {new_val}")
        
    df_diff.to_csv('tests/data/large_diff.csv', index=False)
    print("Done. Files created in tests/data/")

if __name__ == "__main__":
    main()

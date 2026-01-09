import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

def random_date(start, end, fmt):
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return (start + timedelta(seconds=random_second)).strftime(fmt)

def generate_data(num_records=1000):
    ids = list(range(1, num_records + 1))
    
    data = {
        'id': ids,
        'name': [f'User_{i}' for i in ids],
        'age': np.random.randint(18, 90, num_records),
        'salary': np.round(np.random.uniform(30000, 150000, num_records), 2),
        'height_m': np.round(np.random.uniform(1.50, 2.10, num_records), 2),
        'is_active': np.random.choice([True, False], num_records),
        'join_date_iso': [random_date(datetime(2000, 1, 1), datetime(2023, 1, 1), '%Y-%m-%d') for _ in range(num_records)],
        'last_login_fmt2': [random_date(datetime(2023, 1, 1), datetime(2024, 1, 1), '%d/%m/%Y %H:%M') for _ in range(num_records)],
        'category': np.random.choice(['A', 'B', 'C', 'Special'], num_records),
        'score_high_precision': np.random.uniform(0, 100, num_records), # No rounding, lots of decimals
        'zip_code': [f"{random.randint(10000, 99999)}" for _ in range(num_records)],
        'comment_text': [f"Comment, with, commas for id {i}" for i in ids], # Testing quoting
        'mixed_numeric': [int(x) if i % 2 == 0 else float(x) for i, x in enumerate(np.random.randint(1, 100, num_records))], # Int/Float mix
        'currency': ['USD' for _ in range(num_records)],
        'null_col': [None if i % 10 == 0 else 'Value' for i in range(num_records)] # Some NaNs
    }
    
    return pd.DataFrame(data)

def main():
    os.makedirs('tests/data', exist_ok=True)
    print("Generating base dataset...")
    df = generate_data(1000)
    
    # Save base
    df.to_csv('tests/data/complex_1k_base.csv', index=False)
    print("Saved tests/data/complex_1k_base.csv")
    
    # Create a modified version "target"
    df_mod = df.copy()
    
    # 1. Delete some records (e.g., IDs 50-55)
    df_mod = df_mod[~df_mod['id'].isin(range(50, 56))]
    
    # 2. Add some records
    new_rows = generate_data(10)
    new_rows['id'] = range(1001, 1011)
    df_mod = pd.concat([df_mod, new_rows], ignore_index=True)
    
    # 3. Modify content
    # Change salary of ID 1 (float diff)
    df_mod.loc[df_mod['id'] == 1, 'salary'] = df_mod.loc[df_mod['id'] == 1, 'salary'] + 0.01
    
    # Change date format for one record (logical diff? or just string diff)
    # The comparator compares strings, so this will be a diff.
    df_mod.loc[df_mod['id'] == 2, 'join_date_iso'] = '2025-01-01'
    
    # Change precision of ID 3 score (subtle float)
    val = df_mod.loc[df_mod['id'] == 3, 'score_high_precision'].values[0]
    df_mod.loc[df_mod['id'] == 3, 'score_high_precision'] = val + 0.000000001
    
    # Shuffle
    df_mod = df_mod.sample(frac=1).reset_index(drop=True)
    
    df_mod.to_csv('tests/data/complex_1k_target.csv', index=False)
    print("Saved tests/data/complex_1k_target.csv")

if __name__ == "__main__":
    main()

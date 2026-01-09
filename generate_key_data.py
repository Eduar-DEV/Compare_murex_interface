import pandas as pd
import os

def main():
    os.makedirs('tests/data', exist_ok=True)
    
    # Base data
    data = {
        'id': [1, 2, 3, 4, 5],
        'name': ['A', 'B', 'C', 'D', 'E'],
        'val': [10, 20, 30, 40, 50]
    }
    df = pd.DataFrame(data)
    df.to_csv('tests/data/key_base.csv', index=False)
    
    # 1. Shuffled (same content, different order)
    df_shuffled = df.sample(frac=1).reset_index(drop=True)
    df_shuffled.to_csv('tests/data/key_shuffled.csv', index=False)
    
    # 2. Missing record (remove ID 3)
    df_missing = df[df['id'] != 3]
    df_missing.to_csv('tests/data/key_missing.csv', index=False)
    
    # 3. Additional record (add ID 6)
    df_extra = pd.concat([df, pd.DataFrame({'id': [6], 'name': ['F'], 'val': [60]})], ignore_index=True)
    df_extra.to_csv('tests/data/key_extra.csv', index=False)
    
    # 4. Modified content (ID 2 val changed)
    df_mod = df.copy()
    df_mod.loc[df_mod['id'] == 2, 'val'] = 999
    df_mod.to_csv('tests/data/key_mod_content.csv', index=False)

if __name__ == "__main__":
    main()

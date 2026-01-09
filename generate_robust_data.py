import pandas as pd
import os

def main():
    os.makedirs('tests/data', exist_ok=True)
    
    # 1. Composite Key Data
    # id is repeated, but (id, version) is unique
    data_composite = {
        'id': [1, 1, 2, 2, 3],
        'version': ['v1', 'v2', 'v1', 'v3', 'v1'],
        'val': [10, 11, 20, 22, 30]
    }
    df_comp_base = pd.DataFrame(data_composite)
    df_comp_base.to_csv('tests/data/comp_base.csv', index=False)
    
    # Modify one: (2, v3) -> val changed
    # Add one: (3, v2)
    df_comp_target = df_comp_base.copy()
    df_comp_target.loc[(df_comp_target['id'] == 2) & (df_comp_target['version'] == 'v3'), 'val'] = 999
    
    new_row = pd.DataFrame({'id': [3], 'version': ['v2'], 'val': [35]})
    df_comp_target = pd.concat([df_comp_target, new_row], ignore_index=True)
    
    df_comp_target.to_csv('tests/data/comp_target.csv', index=False)
    
    # 2. Ignore Columns Data
    # 'noise_col' differs completely but should be ignored
    data_ignore = {
        'id': [1, 2, 3],
        'val': [10, 20, 30],
        'noise': ['A', 'B', 'C']
    }
    df_ignore_base = pd.DataFrame(data_ignore)
    
    data_ignore_target = {
        'id': [1, 2, 3],
        'val': [10, 20, 30],
        'noise': ['X', 'Y', 'Z'] # Totally different
    }
    df_ignore_target = pd.DataFrame(data_ignore_target)
    
    df_ignore_base.to_csv('tests/data/ignore_base.csv', index=False)
    df_ignore_target.to_csv('tests/data/ignore_target.csv', index=False)

if __name__ == "__main__":
    main()

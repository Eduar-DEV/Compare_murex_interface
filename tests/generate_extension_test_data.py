import os
import pandas as pd
from pathlib import Path

def create_extension_test_data():
    base_dir = Path("tests/extension_data")
    if base_dir.exists():
        import shutil
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. TXT File (Semicolon separated)
    txt_content = "id;name;value\n1;A;100\n2;B;200\n3;C;300"
    with open(base_dir / "test.txt", "w", encoding="utf-8") as f:
        f.write(txt_content)
        
    # 2. Excel File (Original)
    df = pd.DataFrame({
        "id": ["1", "2", "3"],
        "name": ["A", "B", "C"],
        "value": ["100", "200", "300"]
    })
    df.to_excel(base_dir / "test.xlsx", index=False)
    
    # 3. Excel File (With Diff)
    df_diff = pd.DataFrame({
        "id": ["1", "2", "3"],
        "name": ["A", "B_MOD", "C"], # Modified B
        "value": ["100", "200", "300"]
    })
    df_diff.to_excel(base_dir / "test_diff.xlsx", index=False)
    
    print(f"Created test data in {base_dir}")

if __name__ == "__main__":
    create_extension_test_data()

import os
from pathlib import Path

def create_dummy_file(path: Path, content: str = "dummy content"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created: {path}")

def generate_test_data(base_dir: str):
    root = Path(base_dir).resolve()
    if root.exists():
        print(f"Cleaning up {root}...")
        import shutil
        shutil.rmtree(root)
    
    root.mkdir(parents=True, exist_ok=True)
    
    # 1. Standard files
    create_dummy_file(root / "standard_1.csv", "id;name\n1;A")
    create_dummy_file(root / "standard_2.json", '{"key": "value"}')
    create_dummy_file(root / "standard_3.txt", "Plain text")
    create_dummy_file(root / "standard_4.xlsx", "Fake xlsx content")

    # 2. Files with suffixes after extension
    create_dummy_file(root / "suffix_1.csv_PRO_20250101", "id;name\n2;B")
    create_dummy_file(root / "suffix_2.json.BAK", '{"key": "backup"}')
    create_dummy_file(root / "suffix_3.txt_old", "Old text")
    create_dummy_file(root / "suffix_4.csv_v2", "id;name\n3;C")

    # 3. Files in subdirectories
    sub1 = root / "subdir_A"
    create_dummy_file(sub1 / "nested_1.csv", "id;name\n4;D")
    create_dummy_file(sub1 / "nested_2.xml", "<root></root>")
    
    sub2 = root / "subdir_B" / "deep"
    create_dummy_file(sub2 / "deep_1.csv_ARCHIVE", "id;name\n5;E")
    create_dummy_file(sub2 / "deep_2.log", "Log entry")

    # 4. Files matching partial extension logic overlap
    create_dummy_file(root / "image.png", "fake image")
    create_dummy_file(root / "data.csv.tmp", "temp csv")

    print("\nTest data generation complete.")
    print(f"Directory: {root}")

if __name__ == "__main__":
    generate_test_data("tests/mover_test_data/input")

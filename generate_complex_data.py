import os
import csv
import random
import shutil

# Configuration
BASE_DIR = "tests/batch_data"
DIR_A = os.path.join(BASE_DIR, "server_a")
DIR_B = os.path.join(BASE_DIR, "server_b")
NUM_FILES = 20 # 20 Composite files

def generate_composite_csv(filepath, rows=50, duplicate_keys=False):
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['portfolio', 'instrument', 'date', 'market_value', 'currency'])
        
        data = []
        for i in range(1, rows + 1):
            row = [
                f"PF_{random.choice(['A', 'B', 'C'])}",       # Key Part 1
                f"INST_{random.randint(1, 100):03d}",          # Key Part 2
                f"2023-01-{random.randint(1, 5):02d}",         # Key Part 3
                f"{random.uniform(1000, 50000):.2f}",
                random.choice(['USD', 'EUR', 'GBP'])
            ]
            data.append(row)
            
        if duplicate_keys:
            # Duplicate the first row 3 times
            data.append(data[0]) 
            data.append(data[0])
            
        writer.writerows(data)

def modify_csv(source_path, target_path, mode='identical'):
    with open(source_path, 'r') as f:
        rows = list(csv.reader(f))
    
    header = rows[0]
    data = rows[1:] # type: list
    
    if mode == 'diff':
        if len(data) > 5:
            # Change Market Value (Col 3)
            data[2][3] = "999999.99"
            
    with open(target_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

def main():
    # Assume directories exist (created by generate_batch_data.py)
    os.makedirs(DIR_A, exist_ok=True)
    os.makedirs(DIR_B, exist_ok=True)
    
    print(f"Generating {NUM_FILES} composite key files...")
    
    for i in range(1, NUM_FILES + 1):
        filename = f"composite_report_{i:03d}.csv"
        path_a = os.path.join(DIR_A, filename)
        path_b = os.path.join(DIR_B, filename)
        
        # Scenario Logic
        # 1-5: Identical
        # 6-10: Diff
        # 11-15: Missing/Extra
        # 16: Duplicate Keys (Edge Case)
        
        if i <= 5:
            generate_composite_csv(path_a)
            shutil.copy(path_a, path_b)
        elif i <= 10:
            generate_composite_csv(path_a)
            modify_csv(path_a, path_b, mode='diff')
        elif i <= 13:
            generate_composite_csv(path_a) # Missing in B
        elif i <= 15:
            generate_composite_csv(path_b) # Extra in B
            # Ensure A exists? No, missing in A logic requires it absent.
        elif i == 16:
            # Duplicate Keys Case
            filename = f"composite_dup_{i:03d}.csv"
            path_a = os.path.join(DIR_A, filename)
            path_b = os.path.join(DIR_B, filename)
            generate_composite_csv(path_a, duplicate_keys=True) # Dupes in A
            generate_composite_csv(path_b, duplicate_keys=False) # Clean in B
            
    print("Complex data generation complete.")

if __name__ == "__main__":
    main()

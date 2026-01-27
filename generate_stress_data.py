import os
import csv
import random
import shutil
import string

# Configuration
BASE_DIR = "tests/stress_data"
DIR_A = os.path.join(BASE_DIR, "server_a")
DIR_B = os.path.join(BASE_DIR, "server_b")
NUM_FILES = 100
SEPARATOR = ';'

def setup_directories():
    if os.path.exists(BASE_DIR):
        shutil.rmtree(BASE_DIR)
    os.makedirs(DIR_A)
    os.makedirs(DIR_B)
    print(f"Created directories: {DIR_A}, {DIR_B}")

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_csv(filepath, rows=50, separator=SEPARATOR, include_id_duplicates=False, missing_keys=False, extra_columns=False, bad_headers=False):
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=separator)
        
        headers = ['id', 'date', 'amount', 'currency', 'status', 'description']
        if extra_columns:
            headers.append('extra_col_1')
        if bad_headers:
            headers = ['ID ', 'Date', 'Amount', 'Currency', 'Status', 'Desc'] # Mismatched names
        if missing_keys:
             headers = ['date', 'amount', 'currency', 'status'] # No ID column

        writer.writerow(headers)
        
        generated_ids = []
        
        for i in range(1, rows + 1):
            row_id = i
            if include_id_duplicates and i > rows - 5: # Make last 5 duplicates of first 5
                row_id = i - (rows - 5)
            
            row = [
                row_id,
                f"2023-01-{random.randint(1, 28):02d}",
                f"{random.randint(100, 10000)}",
                random.choice(['USD', 'EUR', 'GBP', 'JPY']),
                random.choice(['PENDING', 'CLEARED', 'FAILED', 'CANCELLED']),
                generate_random_string(15)
            ]
            
            if extra_columns:
                row.append("extra_data")
                
            if missing_keys:
                 row.pop(0) # Remove ID from data too
            
            writer.writerow(row)

def modify_csv_content(source_path, target_path, separator=SEPARATOR, modification_type='random'):
    with open(source_path, 'r') as f:
        reader = csv.reader(f, delimiter=separator)
        rows = list(reader)
    
    header = rows[0]
    data = rows[1:]
    
    if modification_type == 'content_diff':
        # Modify 5 random rows
        for _ in range(5):
            if not data: break
            row_idx = random.randint(0, len(data)-1)
            col_idx = random.randint(1, len(header)-1) # Skip ID
            if col_idx < len(data[row_idx]):
                 data[row_idx][col_idx] = "MODIFIED_VALUE"
                 
    elif modification_type == 'header_mismatch':
        # Change header names in target only
        header = [h + "_X" for h in header]

    elif modification_type == 'row_count_diff':
        # Remove last 10 rows
        data = data[:-10]
        
    with open(target_path, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=separator)
        writer.writerow(header)
        writer.writerows(data)

def main():
    setup_directories()
    
    print(f"Generating {NUM_FILES} files for stress testing (Separator: '{SEPARATOR}')...")
    
    scenarios = [
        'perfect_match', 
        'content_diff', 
        'missing_in_b', 
        'missing_in_a', 
        'duplicate_keys_a', 
        'duplicate_keys_b',
        'key_not_found',
        'header_mismatch',
        'empty_file', # Pending implementation if complex
        'extra_cols_b'
    ]
    
    for i in range(1, NUM_FILES + 1):
        filename = f"stress_test_{i:03d}.csv"
        path_a = os.path.join(DIR_A, filename)
        path_b = os.path.join(DIR_B, filename)
        
        # Pick scenario
        scenario = scenarios[i % len(scenarios)]
        
        if scenario == 'perfect_match':
            generate_csv(path_a, separator=SEPARATOR)
            shutil.copy(path_a, path_b)
            
        elif scenario == 'content_diff':
            generate_csv(path_a, separator=SEPARATOR)
            modify_csv_content(path_a, path_b, separator=SEPARATOR, modification_type='content_diff')
            
        elif scenario == 'missing_in_b':
            generate_csv(path_a, separator=SEPARATOR)
            # No B file
            
        elif scenario == 'missing_in_a':
            generate_csv(path_b, separator=SEPARATOR)
            # No A file
            
        elif scenario == 'duplicate_keys_a':
            generate_csv(path_a, separator=SEPARATOR, include_id_duplicates=True)
            shutil.copy(path_a, path_b) # B also has dupes? Or just A? Let's make B clean to see only A error.
            # Actually, if A has dupes, we error out before comparing B usually.
            
        elif scenario == 'duplicate_keys_b':
            generate_csv(path_a, separator=SEPARATOR)
            generate_csv(path_b, separator=SEPARATOR, include_id_duplicates=True)
            
        elif scenario == 'key_not_found':
            generate_csv(path_a, separator=SEPARATOR, missing_keys=True)
            shutil.copy(path_a, path_b)
            
        elif scenario == 'header_mismatch':
            generate_csv(path_a, separator=SEPARATOR)
            modify_csv_content(path_a, path_b, separator=SEPARATOR, modification_type='header_mismatch')
            
        elif scenario == 'empty_file':
            # Create empty files
            open(path_a, 'w').close()
            open(path_b, 'w').close()
            
        elif scenario == 'extra_cols_b':
            generate_csv(path_a, separator=SEPARATOR)
            generate_csv(path_b, separator=SEPARATOR, extra_columns=True)

    print("Stress data generation complete.")

if __name__ == "__main__":
    main()

import os
import csv
import random
import shutil

# Configuration
BASE_DIR = "tests/batch_data"
DIR_A = os.path.join(BASE_DIR, "server_a")
DIR_B = os.path.join(BASE_DIR, "server_b")
NUM_FILES = 100

def setup_directories():
    if os.path.exists(BASE_DIR):
        shutil.rmtree(BASE_DIR)
    os.makedirs(DIR_A)
    os.makedirs(DIR_B)
    print(f"Created directories: {DIR_A}, {DIR_B}")

def generate_csv(filepath, rows=50):
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'date', 'amount', 'currency', 'status'])
        for i in range(1, rows + 1):
            writer.writerow([
                i,
                f"2023-01-{random.randint(1, 31):02d}",
                f"{random.randint(100, 10000)}", # Integers for strict testing potential
                random.choice(['USD', 'EUR', 'GBP']),
                random.choice(['PENDING', 'CLEARED', 'FAILED'])
            ])

def generate_special_csv(filepath, rows=50):
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['deal_id', 'execution_date', 'notional', 'counterparty'])
        for i in range(1, rows + 1):
            writer.writerow([
                f"DL-{i:04d}",
                f"2023-01-{random.randint(1, 31):02d}",
                f"{random.uniform(5000, 50000):.2f}",
                f"CPTY_{random.randint(1, 5)}"
            ])

def modify_csv(source_path, target_path, mode='identical'):
    with open(source_path, 'r') as f:
        rows = list(csv.reader(f))
    
    header = rows[0]
    data = rows[1:]
    
    if mode == 'diff':
        # Modify a few rows values
        if len(data) > 5:
            # Safe modification
            if len(data[2]) > 2:
                data[2][2] = "99999.99" # Value Change
            if len(data[5]) > 4:
                data[5][4] = "CANCELLED" # Status Change (if exists)
            elif len(data[5]) > 1: # Fallback for special report
                 data[5][1] = "2099-01-01" # Date change
            
    elif mode == 'strict':
        # Strict Format Test: Change "100" to "100.0"
        # Find a suitable integer column (index 2 'amount' in standard)
        if 'amount' in header:
            idx = header.index('amount')
            for i in range(len(data)):
                val = data[i][idx]
                if val.isdigit(): # If it's pure int string
                    data[i][idx] = f"{val}.0" # Make it float string
                    # Change only a few to simulate mixed bag, or all? Let's change 5.
                    if i > 5: break
    
    with open(target_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data)

def main():
    setup_directories()
    
    print(f"Generating {NUM_FILES} files for batch testing...")
    
    for i in range(1, NUM_FILES + 1):
        # Determine Type: Standard vs Special (Last 10)
        is_special = i > 90
        
        if is_special:
            filename = f"special_report_{i:03d}.csv"
            gen_func = generate_special_csv
            # For special, let's keep them mostly identical to prove key config works
            scenario = random.choice(['identical', 'diff']) 
        else:
            filename = f"trade_report_{i:03d}.csv"
            gen_func = generate_csv
            # Random scenario for standard files
            # 0.0-0.6: Identical
            # 0.6-0.7: Missing in B
            # 0.7-0.8: Extra in B (Missing in A)
            # 0.8-0.9: Content Diff
            # 0.9-1.0: Strict Format Diff
            rand = random.random()
            if rand < 0.6: scenario = 'identical'
            elif rand < 0.7: scenario = 'missing'
            elif rand < 0.8: scenario = 'extra'
            elif rand < 0.9: scenario = 'diff'
            else: scenario = 'strict'

        path_a = os.path.join(DIR_A, filename)
        path_b = os.path.join(DIR_B, filename)
        
        # Execute Scenario
        if scenario == 'identical':
            gen_func(path_a)
            shutil.copy(path_a, path_b)
            
        elif scenario == 'diff':
            gen_func(path_a)
            modify_csv(path_a, path_b, mode='diff')
            
        elif scenario == 'strict':
            gen_func(path_a)
            if is_special: # Special doesn't support strict (floats already)
                shutil.copy(path_a, path_b)
            else:
                modify_csv(path_a, path_b, mode='strict')
                
        elif scenario == 'missing':
            gen_func(path_a)
            # Do not create B
            
        elif scenario == 'extra':
            gen_func(path_b)
            # Do not create A

    print("Batch data generation complete.")

if __name__ == "__main__":
    main()

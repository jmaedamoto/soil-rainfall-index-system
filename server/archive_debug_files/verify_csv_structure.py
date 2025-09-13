#!/usr/bin/env python3
"""
CSVファイルの構造を詳細確認
"""

import sys
import os
sys.path.append('.')

import pandas as pd

def verify_csv_structure():
    """CSV構造の詳細確認"""
    print("=== CSV Structure Verification ===")
    
    # CSV読み込み
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    print(f"CSV data: {len(df)} rows, {len(df.columns)} columns")
    
    # 最初の行を詳細分析
    first_row = df.iloc[0]
    print(f"\\nFirst row analysis:")
    print(f"  Column 0 (Area): {first_row[0]}")
    print(f"  Column 1 (X): {first_row[1]}")
    print(f"  Column 2 (Y): {first_row[2]}")
    print(f"  Column 3 (Advisory): {first_row[3]}")
    print(f"  Column 4 (Warning): {first_row[4]}")
    print(f"  Column 5 (Dosyakei): {first_row[5]}")
    print(f"  Column 6: {first_row[6]} <- What is this?")
    
    print(f"\\nTime series data (7th column onwards):")
    for i in range(7, min(12, len(first_row))):
        print(f"  Column {i}: {first_row[i]}")
    
    # 仮説：6列目が初期SWI、7列目以降が時系列
    print(f"\\n=== Hypothesis Testing ===")
    print(f"If Column 6 is initial SWI: {first_row[6]}")
    print(f"Time series FT0 (Column 7): {first_row[7]}")
    print(f"Time series FT3 (Column 8): {first_row[8]}")
    print(f"Time series FT6 (Column 9): {first_row[9]}")
    
    # VBA的には：
    # swi_time_series(1).ft = 0, swi_time_series(1).value = swi (初期値)
    # swi_time_series(2).ft = 3, swi_time_series(2).value = 計算結果
    
    # もし7列目がFT=0の初期値だとすると、これとGRIB2から読み取った初期SWI値が一致すべき
    
    return first_row

if __name__ == "__main__":
    verify_csv_structure()
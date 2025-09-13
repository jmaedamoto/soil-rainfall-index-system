#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSVファイルのエンコーディングテスト
"""

def test_encoding(filename, encoding):
    print(f"\\n=== {filename} with {encoding} ===")
    try:
        with open(filename, 'r', encoding=encoding) as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines[:3]):
            parts = line.strip().split(',')
            print(f"Line {i+1}: {parts[:6]}")
            if len(parts) >= 3:
                try:
                    print(f"  Parsed: area={parts[0]}, x={parts[1]}, y={parts[2]}")
                except:
                    print(f"  Parse failed")
    except Exception as e:
        print(f"Error: {e}")

def main():
    encodings = ['utf-8', 'shift_jis', 'iso-8859-1', 'cp932']
    
    for encoding in encodings:
        test_encoding('data/shiga_rain.csv', encoding)
        test_encoding('data/shiga_swi.csv', encoding)

if __name__ == "__main__":
    main()
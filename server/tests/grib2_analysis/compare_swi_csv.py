#!/usr/bin/env python3
"""
Compare server GRIB2 SWI processing with correct CSV values.
This script validates that the server's soil water index calculations 
match the expected values from the CSV files.
"""

import pandas as pd
import numpy as np
from services.main_service import MainService
from datetime import datetime
import sys
import os

def load_swi_csv(prefecture_code):
    """Load SWI CSV file for a prefecture"""
    csv_path = f"data/{prefecture_code}_swi.csv"
    try:
        # Try different encodings
        for encoding in ['shift-jis', 'cp932', 'iso-8859-1', 'utf-8']:
            try:
                # Skip first row (meaningless data) and load from row 2
                df = pd.read_csv(csv_path, header=None, skiprows=1, encoding=encoding)
                print(f"Loaded {len(df)} records from {csv_path} (encoding: {encoding})")
                return df
            except UnicodeDecodeError:
                continue
        print(f"Could not decode {csv_path} with any encoding")
        return None
    except Exception as e:
        print(f"Error loading {csv_path}: {e}")
        return None

def load_rain_csv(prefecture_code):
    """Load rain CSV file for a prefecture"""
    csv_path = f"data/{prefecture_code}_rain.csv"
    try:
        # Try different encodings
        for encoding in ['shift-jis', 'cp932', 'iso-8859-1', 'utf-8']:
            try:
                df = pd.read_csv(csv_path, header=None, encoding=encoding)
                print(f"Loaded {len(df)} records from {csv_path} (encoding: {encoding})")
                return df
            except UnicodeDecodeError:
                continue
        print(f"Could not decode {csv_path} with any encoding")
        return None
    except Exception as e:
        print(f"Error loading {csv_path}: {e}")
        return None

def compare_single_prefecture(prefecture_code, limit_meshes=10):
    """Compare server results with CSV data for one prefecture"""
    print(f"\n=== Comparing {prefecture_code.upper()} Prefecture ===")
    
    # Load CSV data
    swi_df = load_swi_csv(prefecture_code)
    rain_df = load_rain_csv(prefecture_code)
    
    if swi_df is None or rain_df is None:
        print(f"Failed to load CSV data for {prefecture_code}")
        return False
    
    # Get server results using local test files
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    try:
        main_service = MainService()
        result = main_service.main_process_from_files(swi_file, guidance_file)
        print("Server processing completed successfully")
    except Exception as e:
        print(f"Server processing failed: {e}")
        return False
    
    # Find prefecture in server results
    prefecture_data = None
    for pref_code, pref_data in result.get('prefectures', {}).items():
        if pref_code == prefecture_code:
            prefecture_data = pref_data
            break
    
    if not prefecture_data:
        print(f"No data found for {prefecture_code} in server results")
        return False
    
    # Compare results
    mismatches = 0
    total_comparisons = 0
    mesh_count = 0
    
    for area in prefecture_data.get('areas', []):
        for mesh in area.get('meshes', []):
            if mesh_count >= limit_meshes:
                break
                
            mesh_code = mesh['code']
            server_swi = mesh.get('swi_timeline', [])
            server_rain = mesh.get('rain_timeline', [])
            
            # Find corresponding row in CSV
            csv_row = None
            for idx, row in swi_df.iterrows():
                if str(int(row[1])) == str(mesh['x']) and str(int(row[2])) == str(mesh['y']):
                    csv_row = row
                    break
            
            if csv_row is None:
                print(f"Mesh {mesh_code} not found in CSV")
                continue
            
            # Compare SWI values
            csv_swi_values = []
            for col_idx in range(7, min(len(csv_row), 7 + len(server_swi))):
                if pd.notna(csv_row[col_idx]):
                    csv_swi_values.append(float(csv_row[col_idx]))
            
            print(f"\nMesh {mesh_code} (x={mesh['x']}, y={mesh['y']}):")
            print(f"  Boundaries: advisory={mesh['advisary_bound']}, warning={mesh['warning_bound']}, disaster={mesh['dosyakei_bound']}")
            
            for i, server_point in enumerate(server_swi):
                if i < len(csv_swi_values):
                    csv_value = csv_swi_values[i]
                    server_value = server_point['value']
                    ft = server_point['ft']
                    
                    diff = abs(csv_value - server_value)
                    if diff > 0.01:  # Allow small floating point differences
                        print(f"  FT {ft:2d}: CSV={csv_value:8.2f}, Server={server_value:8.2f}, Diff={diff:8.2f} MISMATCH")
                        mismatches += 1
                    else:
                        print(f"  FT {ft:2d}: CSV={csv_value:8.2f}, Server={server_value:8.2f}, Diff={diff:8.2f} OK")
                    
                    total_comparisons += 1
            
            mesh_count += 1
        
        if mesh_count >= limit_meshes:
            break
    
    print(f"\n=== Summary for {prefecture_code.upper()} ===")
    print(f"Total comparisons: {total_comparisons}")
    print(f"Mismatches: {mismatches}")
    print(f"Match rate: {((total_comparisons - mismatches) / total_comparisons * 100):.1f}%" if total_comparisons > 0 else "N/A")
    
    return mismatches == 0

def main():
    """Main comparison function"""
    print("=== SWI CSV vs Server GRIB2 Processing Comparison ===")
    
    # Test with Shiga prefecture (smallest dataset)
    prefecture = "shiga"
    limit_meshes = 20  # Limit for debugging
    
    success = compare_single_prefecture(prefecture, limit_meshes)
    
    if success:
        print(f"\nSUCCESS: All SWI values match for {prefecture} prefecture!")
    else:
        print(f"\nFAILURE: Found discrepancies in {prefecture} prefecture SWI calculations")
        print("Check the GRIB2 processing logic against Module.bas VBA code")

if __name__ == "__main__":
    main()
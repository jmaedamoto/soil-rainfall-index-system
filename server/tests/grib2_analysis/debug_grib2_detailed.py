#!/usr/bin/env python3
"""
Detailed GRIB2 processing debug script to identify discrepancies with VBA code.
Focus on run-length decompression and compare with expected CSV values.
"""

import sys
import os
# Add parent directories to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from services.grib2_service import Grib2Service
import pandas as pd

def debug_grib2_processing():
    """Debug GRIB2 processing in detail"""
    print("=== Detailed GRIB2 Processing Debug ===")
    
    # Initialize service
    grib2_service = Grib2Service()
    
    # Test with SWI file
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    try:
        print(f"\n=== SWI File Analysis: {swi_file} ===")
        base_info, swi_grib2 = grib2_service.unpack_swi_grib2_from_file(swi_file)
        
        print(f"Base Info:")
        print(f"  Initial Date: {base_info.initial_date}")
        print(f"  Grid Num: {base_info.grid_num}")
        print(f"  X Num: {base_info.x_num}, Y Num: {base_info.y_num}")
        print(f"  Lat Range: {base_info.s_lat/1000000:.6f} to {base_info.e_lat/1000000:.6f}")
        print(f"  Lon Range: {base_info.s_lon/1000000:.6f} to {base_info.e_lon/1000000:.6f}")
        
        print(f"\nSWI Data:")
        print(f"  SWI Values: {len(swi_grib2.get('swi', []))} points")
        print(f"  First Tank: {len(swi_grib2.get('first_tunk', []))} points")
        print(f"  Second Tank: {len(swi_grib2.get('second_tunk', []))} points")
        
        # Sample SWI values
        swi_data = swi_grib2.get('swi', [])
        if swi_data:
            print(f"  Sample SWI values (first 10): {swi_data[:10]}")
        
        print(f"\n=== Guidance File Analysis: {guidance_file} ===")
        guidance_base, guidance_grib2 = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
        
        guidance_data = guidance_grib2.get('data', [])
        print(f"Guidance Data: {len(guidance_data)} time steps")
        
        for i, step in enumerate(guidance_data[:5]):  # First 5 steps
            print(f"  Step {i}: FT={step.get('ft', 'N/A')}, Values={len(step.get('value', []))}")
            if step.get('value'):
                print(f"    Sample values (first 5): {step['value'][:5]}")
        
        # Test coordinate conversion for a specific mesh
        print(f"\n=== Coordinate Testing ===")
        test_meshcode = "53394627"  # From CSV data
        
        # Import coordinate functions
        from services.calculation_service import CalculationService
        calc_service = CalculationService()
        
        lat, lon = calc_service.meshcode_to_coordinate(test_meshcode)
        print(f"Meshcode {test_meshcode} -> Lat: {lat:.6f}, Lon: {lon:.6f}")
        
        x, y = calc_service.meshcode_to_index(test_meshcode)
        print(f"Meshcode {test_meshcode} -> Index X: {x}, Y: {y}")
        
        data_num = calc_service.get_data_num(lat, lon, base_info)
        print(f"Data number for ({lat:.6f}, {lon:.6f}): {data_num}")
        
        # Get SWI value at this point
        if data_num > 0 and data_num <= len(swi_data):
            swi_value = swi_data[data_num - 1]  # 0-based indexing
            print(f"SWI value at data_num {data_num}: {swi_value}")
            print(f"Converted SWI value (÷10): {swi_value / 10}")
        
        # Load corresponding CSV to compare
        print(f"\n=== CSV Comparison ===")
        try:
            csv_df = pd.read_csv("data/shiga_swi.csv", header=None, skiprows=1, encoding='shift-jis')
            print(f"CSV loaded: {len(csv_df)} records")
            
            # Find matching row
            for idx, row in csv_df.iterrows():
                if row[1] == x and row[2] == y:
                    print(f"Found matching CSV row:")
                    print(f"  Area: {row[0]}")
                    print(f"  X,Y: {row[1]}, {row[2]}")
                    print(f"  Boundaries: {row[3]}, {row[4]}, {row[5]}")
                    print(f"  Initial SWI (CSV col 7): {row[6]}")
                    print(f"  Expected vs Actual: {row[6]} vs {swi_value/10:.2f}")
                    break
            else:
                print(f"No matching CSV row found for X={x}, Y={y}")
                
        except Exception as e:
            print(f"CSV loading error: {e}")
            
    except Exception as e:
        print(f"GRIB2 processing error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_grib2_processing()
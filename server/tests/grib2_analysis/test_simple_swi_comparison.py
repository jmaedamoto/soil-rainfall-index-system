#!/usr/bin/env python3
"""
Simple SWI comparison script to test if our GRIB2 processing matches CSV values.
"""

import pandas as pd
from services.main_service import MainService

def test_swi_comparison():
    """Test SWI processing against CSV data"""
    print("=== Simple SWI Comparison Test ===")
    
    # Load CSV data
    print("Loading Shiga SWI CSV...")
    try:
        csv_df = pd.read_csv("data/shiga_swi.csv", header=None, skiprows=1, encoding='shift-jis')
        print(f"CSV loaded: {len(csv_df)} records")
        
        # Show first few rows of CSV
        print("\nFirst 3 CSV records:")
        for i in range(min(3, len(csv_df))):
            row = csv_df.iloc[i]
            print(f"  Row {i+2}: Area={row[0]}, X={row[1]}, Y={row[2]}, Boundaries={row[3]},{row[4]},{row[5]}, Initial SWI={row[6]}")
    except Exception as e:
        print(f"CSV loading error: {e}")
        return
    
    # Process server data
    print("\nProcessing server GRIB2 data...")
    try:
        main_service = MainService()
        result = main_service.main_process_from_files(
            "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin",
            "data/guid_msm_grib2_20230602000000_rmax00.bin"
        )
        print("Server processing completed")
        
        # Find Shiga prefecture
        shiga_data = result.get('prefectures', {}).get('shiga')
        if not shiga_data:
            print("No Shiga data in server results")
            return
        
        print(f"Server data: {len(shiga_data.get('areas', []))} areas")
        
        # Compare first few meshes
        comparison_count = 0
        matches = 0
        mismatches = 0
        
        for area in shiga_data.get('areas', []):
            area_name = area.get('name', '')
            for mesh in area.get('meshes', []):
                if comparison_count >= 10:  # Limit for testing
                    break
                    
                mesh_code = mesh.get('code', '')
                server_swi_timeline = mesh.get('swi_timeline', [])
                
                if not server_swi_timeline:
                    continue
                    
                # Get initial SWI value (FT=0)
                initial_swi = None
                for swi_point in server_swi_timeline:
                    if swi_point.get('ft') == 0:
                        initial_swi = swi_point.get('value')
                        break
                
                if initial_swi is None:
                    continue
                
                # Find matching CSV row by mesh code
                csv_match = None
                for idx, csv_row in csv_df.iterrows():
                    if str(csv_row[0]).strip() == area_name.strip():
                        # For now, just match by area name as mesh codes might differ
                        csv_match = csv_row
                        break
                
                if csv_match is not None:
                    csv_initial_swi = float(csv_match[6])  # Column 7 (0-based index 6)
                    
                    print(f"\nComparison {comparison_count + 1}:")
                    print(f"  Mesh Code: {mesh_code}")
                    print(f"  Area: {area_name}")
                    print(f"  CSV Initial SWI: {csv_initial_swi}")
                    print(f"  Server Initial SWI: {initial_swi}")
                    print(f"  Difference: {abs(csv_initial_swi - initial_swi)}")
                    
                    if abs(csv_initial_swi - initial_swi) < 0.1:
                        matches += 1
                        print("  Status: MATCH ✓")
                    else:
                        mismatches += 1
                        print("  Status: MISMATCH ✗")
                    
                    comparison_count += 1
            
            if comparison_count >= 10:
                break
        
        print(f"\n=== Summary ===")
        print(f"Total comparisons: {comparison_count}")
        print(f"Matches: {matches}")
        print(f"Mismatches: {mismatches}")
        if comparison_count > 0:
            print(f"Match rate: {matches/comparison_count*100:.1f}%")
            
    except Exception as e:
        print(f"Server processing error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_swi_comparison()
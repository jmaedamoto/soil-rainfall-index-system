#!/usr/bin/env python3
"""
ガイダンスデータ構造の詳細デバッグ
"""

import sys
import os
sys.path.append('.')

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from models import Mesh
import logging

logging.basicConfig(level=logging.ERROR)

def debug_guidance_structure():
    """ガイダンスデータ構造のデバッグ"""
    print("=== Guidance Structure Debug ===")
    
    # GRIB2データ読み込み
    grib2_service = Grib2Service()
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    print(f"Guidance data structure:")
    print(f"  Type: {type(guidance_data)}")
    print(f"  Keys: {list(guidance_data.keys()) if isinstance(guidance_data, dict) else 'Not a dict'}")
    
    if isinstance(guidance_data, dict):
        if 'data' in guidance_data:
            print(f"  Data length: {len(guidance_data['data'])}")
            for i, data_set in enumerate(guidance_data['data'][:5]):
                print(f"    Dataset {i}:")
                print(f"      Type: {type(data_set)}")
                print(f"      Keys: {list(data_set.keys()) if isinstance(data_set, dict) else 'Not a dict'}")
                if isinstance(data_set, dict):
                    print(f"      FT: {data_set.get('ft', 'N/A')}")
                    values = data_set.get('value', [])
                    print(f"      Values length: {len(values)}")
                    if len(values) > 133917:
                        print(f"      Sample value at index 133917: {values[133917]}")
    
    # テスト座標
    csv_x, csv_y = 2869, 4187
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
    calc_service = CalculationService()
    guidance_index = calc_service.get_data_num(lat, lon, guidance_base_info)
    
    print(f"\nTest coordinate mapping:")
    print(f"  lat={lat}, lon={lon}")
    print(f"  guidance_index={guidance_index}")
    
    # calc_swi_timelapseのガイダンス処理をテスト
    if isinstance(guidance_data, dict) and 'data' in guidance_data:
        print(f"\nGuidance processing simulation:")
        for i, data_set in enumerate(guidance_data['data'][:3]):
            if isinstance(data_set, dict):
                values = data_set.get('value', [])
                ft = data_set.get('ft', (i + 1) * 3)
                
                if guidance_index < len(values):
                    rain = values[guidance_index]
                    print(f"  FT{ft}: rain={rain}")
                else:
                    print(f"  FT{ft}: index out of range")

if __name__ == "__main__":
    debug_guidance_structure()
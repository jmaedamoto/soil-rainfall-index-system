#!/usr/bin/env python3
"""
VBAとPythonの座標変換を詳細比較
"""

import sys
import os
sys.path.append('.')

from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
import logging

logging.basicConfig(level=logging.ERROR)

def debug_coordinate_exact():
    """座標変換の詳細比較"""
    print("=== Coordinate Conversion Exact Debug ===")
    
    # テスト座標
    csv_x, csv_y = 2869, 4187
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
    print(f"Input coordinates: X={csv_x}, Y={csv_y}")
    print(f"Converted lat/lon: lat={lat:.15f}, lon={lon:.15f}")
    
    # GRIB2データ読み込み
    grib2_service = Grib2Service()
    calc_service = CalculationService()
    
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    print(f"\\nSWI base_info:")
    print(f"  s_lat = {base_info.s_lat} / 1000000 = {base_info.s_lat / 1000000}")
    print(f"  s_lon = {base_info.s_lon} / 1000000 = {base_info.s_lon / 1000000}")
    print(f"  d_lat = {base_info.d_lat} / 1000000 = {base_info.d_lat / 1000000}")
    print(f"  d_lon = {base_info.d_lon} / 1000000 = {base_info.d_lon / 1000000}")
    print(f"  x_num = {base_info.x_num}")
    print(f"  y_num = {base_info.y_num}")
    
    # VBAロジックの詳細実装
    print(f"\\nVBA logic step by step (SWI):")
    y_calc = (base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)
    x_calc = (lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)
    
    print(f"  y_calc = ({base_info.s_lat / 1000000} - {lat}) / {base_info.d_lat / 1000000} = {y_calc}")
    print(f"  x_calc = ({lon} - {base_info.s_lon / 1000000}) / {base_info.d_lon / 1000000} = {x_calc}")
    
    y = int(y_calc) + 1
    x = int(x_calc) + 1
    
    print(f"  y = int({y_calc}) + 1 = {y}")
    print(f"  x = int({x_calc}) + 1 = {x}")
    
    vba_data_num = (y - 1) * base_info.x_num + x
    python_index = vba_data_num - 1  # 0ベース変換
    
    print(f"  vba_data_num = ({y} - 1) * {base_info.x_num} + {x} = {vba_data_num}")
    print(f"  python_index = {vba_data_num} - 1 = {python_index}")
    
    # Pythonのget_data_numと比較
    calculated_index = calc_service.get_data_num(lat, lon, base_info)
    print(f"  calc_service.get_data_num() = {calculated_index}")
    
    print(f"\\nComparison: manual={python_index}, service={calculated_index}, match={python_index == calculated_index}")
    
    # Guidance側でも同様
    print(f"\\nGuidance base_info:")
    print(f"  x_num = {guidance_base_info.x_num}")
    print(f"  y_num = {guidance_base_info.y_num}")
    
    guidance_index = calc_service.get_data_num(lat, lon, guidance_base_info)
    print(f"  guidance_index = {guidance_index}")

if __name__ == "__main__":
    debug_coordinate_exact()
#!/usr/bin/env python3
"""
VBAの1ベース配列インデックスを正確に模倣
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from models import Mesh
import logging

logging.basicConfig(level=logging.ERROR)

def debug_vba_index():
    """VBAインデックスの詳細デバッグ"""
    print("=== VBA Index Debug ===")
    
    # 座標
    csv_x, csv_y = 2869, 4187
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
    print(f"Coordinates: X={csv_x}, Y={csv_y}")
    print(f"Converted: lat={lat:.15f}, lon={lon:.15f}")
    
    # GRIB2データ読み込み
    grib2_service = Grib2Service()
    calc_service = CalculationService()
    
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    # VBAのget_data_num完全再実装
    def vba_get_data_num(lat, lon, base_info):
        """VBAのget_data_num完全再現"""
        # VBA: y = Int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        y_calc = (base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)
        x_calc = (lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)
        
        # VBAのInt()は切り捨て（Pythonと同じ）
        y = int(y_calc) + 1  # VBAの1ベース
        x = int(x_calc) + 1  # VBAの1ベース
        
        # VBA: get_data_num = (y - 1) * base_info.x_num + x
        vba_data_num = (y - 1) * base_info.x_num + x
        
        return vba_data_num, y, x, y_calc, x_calc
    
    # SWI インデックス
    vba_swi_data_num, swi_y, swi_x, swi_y_calc, swi_x_calc = vba_get_data_num(lat, lon, base_info)
    python_swi_index = vba_swi_data_num - 1  # 0ベース変換
    
    print(f"\\nSWI index calculation:")
    print(f"  y_calc = {swi_y_calc:.10f} -> y = {swi_y}")
    print(f"  x_calc = {swi_x_calc:.10f} -> x = {swi_x}")
    print(f"  vba_data_num = {vba_swi_data_num}")
    print(f"  python_index = {python_swi_index}")
    
    # 既存サービスとの比較
    service_index = calc_service.get_data_num(lat, lon, base_info)
    print(f"  service_index = {service_index}")
    print(f"  Match: {python_swi_index == service_index}")
    
    # ガイダンス インデックス
    vba_guid_data_num, guid_y, guid_x, guid_y_calc, guid_x_calc = vba_get_data_num(lat, lon, guidance_base_info)
    python_guid_index = vba_guid_data_num - 1  # 0ベース変換
    
    print(f"\\nGuidance index calculation:")
    print(f"  y_calc = {guid_y_calc:.10f} -> y = {guid_y}")
    print(f"  x_calc = {guid_x_calc:.10f} -> x = {guid_x}")
    print(f"  vba_data_num = {vba_guid_data_num}")
    print(f"  python_index = {python_guid_index}")
    
    # 既存サービスとの比較
    service_guid_index = calc_service.get_data_num(lat, lon, guidance_base_info)
    print(f"  service_index = {service_guid_index}")
    print(f"  Match: {python_guid_index == service_guid_index}")
    
    # データ値確認
    print(f"\\nData values at calculated index:")
    if python_swi_index < len(swi_data['swi']):
        swi_raw = swi_data['swi'][python_swi_index]
        first_raw = swi_data['first_tunk'][python_swi_index]
        second_raw = swi_data['second_tunk'][python_swi_index]
        
        print(f"  SWI: {swi_raw} -> {swi_raw/10}")
        print(f"  First: {first_raw} -> {first_raw/10}")
        print(f"  Second: {second_raw} -> {second_raw/10}")
        print(f"  Third: {(swi_raw - first_raw - second_raw)/10}")
    
    # 近隣インデックスの確認（±1）
    print(f"\\nNeighboring index values:")
    for offset in [-1, 0, 1]:
        test_index = python_swi_index + offset
        if 0 <= test_index < len(swi_data['swi']):
            swi_val = swi_data['swi'][test_index] / 10
            print(f"  Index {test_index}: SWI={swi_val}")

if __name__ == "__main__":
    debug_vba_index()
#!/usr/bin/env python3
"""
calc_swi_timelapse関数の詳細デバッグ
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
from models import Mesh, BaseInfo
import logging

logging.basicConfig(level=logging.ERROR)

def debug_calculation_detailed():
    """計算処理の詳細デバッグ"""
    print("=== Calculation Debug ===")
    
    # テストデータ
    csv_x, csv_y = 2869, 4187
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
    # GRIB2データ読み込み
    grib2_service = Grib2Service()
    calc_service = CalculationService()
    
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    print(f"Base info comparison:")
    print(f"  SWI: {base_info.x_num}x{base_info.y_num} = {base_info.grid_num}")
    print(f"  Guidance: {guidance_base_info.x_num}x{guidance_base_info.y_num} = {guidance_base_info.grid_num}")
    
    # 座標変換デバッグ
    swi_index = calc_service.get_data_num(lat, lon, base_info)
    guidance_index = calc_service.get_data_num(lat, lon, guidance_base_info)
    
    print(f"\\nCoordinate mapping:")
    print(f"  Test coordinates: lat={lat}, lon={lon}")
    print(f"  SWI index: {swi_index} (max: {base_info.grid_num-1})")
    print(f"  Guidance index: {guidance_index} (max: {guidance_base_info.grid_num-1})")
    
    # ガイダンスデータの詳細
    print(f"\\nGuidance data details:")
    print(f"  Number of time series: {len(guidance_data['data'])}")
    
    for i, data_set in enumerate(guidance_data['data'][:5]):
        ft = data_set.get('ft', 'N/A')
        values = data_set.get('value', [])
        print(f"    {i}: FT={ft}, values length={len(values)}")
        if guidance_index >= 0 and guidance_index < len(values):
            print(f"        value at index {guidance_index}: {values[guidance_index]}")
        else:
            print(f"        index {guidance_index} out of range (max: {len(values)-1})")
    
    # Meshオブジェクト作成
    mesh = Mesh(
        area_name="test",
        code="",
        lat=lat,
        lon=lon,
        x=csv_x,
        y=csv_y,
        advisary_bound=100,
        warning_bound=150,
        dosyakei_bound=200,
        swi=[],
        rain=[]
    )
    
    print(f"\\n=== Manual calculation step-by-step ===")
    
    # 手動でcalc_swi_timelapse相当を実行
    try:
        swi_index = calc_service.get_data_num(mesh.lat, mesh.lon, swi_data['base_info'])
        
        if swi_index >= 0 and swi_index < len(swi_data['swi']):
            # 初期値取得（生の値）
            initial_swi_raw = swi_data['swi'][swi_index]
            first_tunk_raw = swi_data['first_tunk'][swi_index]
            second_tunk_raw = swi_data['second_tunk'][swi_index]
            
            print(f"Raw initial values:")
            print(f"  SWI: {initial_swi_raw}")
            print(f"  First tank: {first_tunk_raw}")
            print(f"  Second tank: {second_tunk_raw}")
            
            # VBAと同じく10で割る
            initial_swi = initial_swi_raw / 10
            first_tunk = first_tunk_raw / 10
            second_tunk = second_tunk_raw / 10
            third_tunk = initial_swi - first_tunk - second_tunk
            
            print(f"\\nProcessed initial values:")
            print(f"  SWI: {initial_swi}")
            print(f"  First tank: {first_tunk}")
            print(f"  Second tank: {second_tunk}")
            print(f"  Third tank: {third_tunk}")
            
            # ガイダンス処理
            guidance_index = calc_service.get_data_num(mesh.lat, mesh.lon, guidance_data['base_info'])
            print(f"\\nGuidance processing:")
            print(f"  Guidance index: {guidance_index}")
            
            s1, s2, s3 = first_tunk, second_tunk, third_tunk
            timeline = [{'ft': 0, 'value': initial_swi}]
            
            if guidance_index >= 0:
                for i, data_set in enumerate(guidance_data['data']):
                    values = data_set.get('value', [])
                    ft = data_set.get('ft', (i + 1) * 3)
                    
                    if guidance_index < len(values):
                        rain = values[guidance_index]
                        print(f"    FT{ft}: rain={rain}")
                        
                        # タンクモデル計算
                        s1, s2, s3 = calc_service.calc_tunk_model(s1, s2, s3, 3.0, rain)
                        swi_value = s1 + s2 + s3
                        
                        timeline.append({'ft': ft, 'value': swi_value})
                        print(f"      After tank model: SWI={swi_value}")
                    else:
                        print(f"    FT{ft}: index out of range")
                        break
                        
                    if len(timeline) >= 5:  # 最初の5ポイント
                        break
            
            print(f"\\nCalculated timeline:")
            for t in timeline:
                print(f"  FT{t['ft']}: {t['value']:.2f}")
                
            # CSV比較
            csv_file = "data/shiga_swi.csv"
            df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
            first_row = df.iloc[0]
            
            print(f"\\nCSV comparison:")
            for i in range(min(len(timeline), 5)):
                if 7 + i < len(first_row):
                    csv_val = first_row[7 + i]
                    python_val = timeline[i]['value']
                    print(f"  FT{timeline[i]['ft']}: CSV={csv_val}, Python={python_val:.2f}, Diff={abs(csv_val-python_val):.2f}")
        else:
            print(f"SWI index {swi_index} out of range")
            
    except Exception as e:
        print(f"Error in manual calculation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_calculation_detailed()
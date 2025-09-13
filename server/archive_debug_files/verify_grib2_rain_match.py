#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIB2から読み出された雨量データとRAIN.CSVの完全一致検証
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service
from services.data_service import DataService

def parse_rain_csv():
    """Rain CSVから期待値を読み込み"""
    rain_expected = {}
    with open('data/shiga_rain.csv', 'r', encoding='shift_jis') as f:
        lines = f.readlines()
    
    for line in lines:
        parts = line.strip().split(',')
        if len(parts) >= 9 and parts[1] and parts[2]:
            try:
                x = int(parts[1])
                y = int(parts[2])
                # Rain CSVフォーマット: 地域名, x, y, FT3, FT6, FT9, FT12, FT15, FT18
                rain_values = [float(parts[i]) for i in range(3, 9) if parts[i]]
                rain_expected[(x, y)] = rain_values
            except:
                continue
    
    return rain_expected

def main():
    print("=== GRIB2雨量データとRAIN.CSV完全一致検証 ===")
    
    # GRIB2ガイダンスデータ読み込み
    grib2_service = Grib2Service()
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    guidance_base_info, guidance_result = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    # CSVデータ読み込み
    rain_expected = parse_rain_csv()
    print(f"CSV期待値数: {len(rain_expected)}件")
    
    # データサービスでメッシュ情報取得
    data_service = DataService()
    prefectures = data_service.prepare_areas()
    shiga = next((p for p in prefectures if p.code == "shiga"), None)
    
    if not shiga:
        print("滋賀県データが見つかりません")
        return
    
    print(f"\\n=== GRIB2データ直接検証 (最初の10メッシュ) ===")
    
    matches = 0
    total_values = 0
    
    for area in shiga.areas:
        for mesh in area.meshes[:10]:  # 最初の10メッシュのみ
            mesh_key = (mesh.x, mesh.y)
            expected_rain = rain_expected.get(mesh_key)
            
            if expected_rain:
                print(f"\\nメッシュ {mesh.code} ({mesh.x}, {mesh.y}):")
                
                # VBAのget_data_num計算（デバッグ済み）
                base_info = guidance_result['base_info']
                y = int((base_info.s_lat / 1000000 - mesh.lat) / (base_info.d_lat / 1000000)) + 1
                x = int((mesh.lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
                guidance_index = (y - 1) * base_info.x_num + x
                python_index = guidance_index - 1
                
                print(f"  get_data_num結果: guidance_index={guidance_index}, python_index={python_index}")
                
                # GRIB2データから直接値を取得
                grib2_values = []
                for i, guidance_item in enumerate(guidance_result['data'][:6]):  # FT=3,6,9,12,15,18
                    if python_index < len(guidance_item['value']):
                        value = guidance_item['value'][python_index]
                        grib2_values.append(value)
                        ft = guidance_item['ft']
                        expected_ft_value = expected_rain[i] if i < len(expected_rain) else 0
                        
                        match = "OK" if abs(value - expected_ft_value) < 0.1 else "NG"
                        print(f"    FT={ft}: GRIB2={value}, CSV期待値={expected_ft_value} {match}")
                        
                        if abs(value - expected_ft_value) < 0.1:
                            matches += 1
                        total_values += 1
                
                grib2_str = " ".join([f"{v:4.0f}" for v in grib2_values])
                expected_str = " ".join([f"{v:4.0f}" for v in expected_rain])
                print(f"  GRIB2: [{grib2_str}]")
                print(f"  CSV:   [{expected_str}]")
                
    accuracy = matches / total_values * 100 if total_values > 0 else 0
    print(f"\\n=== 検証結果 ===")
    print(f"一致数: {matches}/{total_values} ({accuracy:.1f}%)")
    
    if accuracy >= 99:
        print("✅ GRIB2データとCSVが完全一致しています")
    elif accuracy >= 90:
        print("⚠️ GRIB2データとCSVがほぼ一致しています") 
    else:
        print("❌ GRIB2データとCSVに大きな差異があります")
        print("GRIB2デコード処理の完全やり直しが必要です")

if __name__ == "__main__":
    main()
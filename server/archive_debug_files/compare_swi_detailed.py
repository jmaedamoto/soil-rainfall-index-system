#!/usr/bin/env python3
"""
VBAのCSV結果とPython処理結果の詳細比較
差異を特定して修正ポイントを明確化
"""

import sys
import os
sys.path.append('.')

import pandas as pd
from services.grib2_service import Grib2Service
from services.calculation_service import CalculationService
import logging

# ログレベルを設定
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

def compare_swi_with_csv():
    """CSVファイルとPython処理結果の詳細比較"""
    print("=== VBA CSV vs Python処理 詳細比較 ===")
    
    # CSV読み込み
    csv_file = "data/shiga_swi.csv"
    df = pd.read_csv(csv_file, encoding='shift-jis', header=None, skiprows=1)
    print(f"CSVデータ: {len(df)}メッシュ")
    
    # GRIB2サービス初期化
    grib2_service = Grib2Service()
    calc_service = CalculationService()
    
    # GRIB2ファイル読み込み
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
    
    print("GRIB2ファイル解析中...")
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    guidance_base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    
    print(f"SWI GRIB2: {len(swi_data['swi'])} values")
    print(f"Guidance GRIB2: {len(guidance_data)} time steps")
    
    # 最初の5メッシュで詳細比較
    print("\\n=== 詳細比較（最初の5メッシュ） ===")
    
    mismatches = 0
    for i in range(min(5, len(df))):
        row = df.iloc[i]
        area_name = row[0]
        csv_x, csv_y = int(row[1]), int(row[2])
        
        # 座標変換（VBAと同じ）
        lat = (csv_y + 0.5) * 30 / 3600
        lon = (csv_x + 0.5) * 45 / 3600 + 100
        
        print(f"\\nメッシュ{i+1}: {area_name} (X={csv_x}, Y={csv_y})")
        print(f"  緯度: {lat:.6f}, 経度: {lon:.6f}")
        
        # Python処理で土壌雨量指数計算
        try:
            from models import Mesh
            mesh = Mesh(
                area_name=str(area_name),
                code="",
                lat=lat,
                lon=lon,
                x=csv_x,
                y=csv_y,
                advisary_bound=int(row[3]) if pd.notna(row[3]) else 0,
                warning_bound=int(row[4]) if pd.notna(row[4]) else 0,
                dosyakei_bound=int(row[5]) if pd.notna(row[5]) else 0
            )
            
            # Python計算
            swi_timeline = calc_service.calc_swi_timelapse(mesh, swi_data, guidance_data)
            
            if swi_timeline:
                python_initial = swi_timeline[0].value
                csv_initial = row[6]
                
                print(f"  初期SWI: CSV={csv_initial:.2f}, Python={python_initial:.2f}")
                if abs(python_initial - csv_initial) > 0.01:
                    print(f"  ❌ 初期値不一致: 差={python_initial - csv_initial:.2f}")
                    mismatches += 1
                else:
                    print(f"  ✅ 初期値一致")
                
                # 時系列の最初の3値を比較
                print(f"  時系列比較:")
                for j in range(min(3, len(swi_timeline)-1)):
                    if 7+j < len(row):
                        csv_val = row[7+j]
                        python_val = swi_timeline[j+1].value
                        ft = swi_timeline[j+1].ft
                        print(f"    FT{ft}: CSV={csv_val:.2f}, Python={python_val:.2f}, 差={python_val-csv_val:.2f}")
                        if abs(python_val - csv_val) > 0.01:
                            mismatches += 1
            else:
                print(f"  ❌ Python処理でSWI時系列が取得できませんでした")
                mismatches += 1
                
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            mismatches += 1
    
    print(f"\\n=== 比較結果 ===")
    print(f"不一致数: {mismatches}")
    if mismatches == 0:
        print("✅ 完全一致!")
    else:
        print("❌ 修正が必要です")
    
    return mismatches == 0

if __name__ == "__main__":
    compare_swi_with_csv()
#!/usr/bin/env python3
"""
現在のgrib2_service.pyの実装がデバッグ結果と一致するかテスト
"""

import pandas as pd
from services.grib2_service import Grib2Service

def debug_service_test():
    """grib2_service.pyの実装をテスト"""
    
    grib2_service = Grib2Service()
    
    # GRIB2データ解析（現在のサービス実装）
    base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file('data/guid_msm_grib2_20230602000000_rmax00.bin')
    
    print(f"サービス実装結果:")
    print(f"データセット数: {len(guidance_data['data'])}")
    
    # CSV比較データ読み込み
    try:
        df = pd.read_csv('data/shiga_rain.csv', encoding='shift_jis', header=None)
        
        # テスト座標 (前回確認した座標)
        test_row = 1
        mesh_x = df.iloc[test_row, 1]
        mesh_y = df.iloc[test_row, 2]
        csv_rain_series = df.iloc[test_row, 3:].values
        
        # 座標変換（VBAの関数と同じ）
        lat = (mesh_y + 0.5) * 30 / 3600
        lon = (mesh_x + 0.5) * 45 / 3600 + 100
        y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        grid_index = (y - 1) * base_info.x_num + x
        
        print(f"\\nテスト座標: ({mesh_x}, {mesh_y})")
        print(f"GRIB2インデックス: {grid_index}")
        print(f"CSV雨量時系列: {csv_rain_series}")
        
        if 1 <= grid_index <= len(guidance_data['data'][0]):
            print(f"\\n=== サービス実装とCSVの比較 ===")
            
            # 各データセットと完全一致を探す
            perfect_matches = []
            for dataset_idx in range(len(guidance_data['data'])):
                dataset = guidance_data['data'][dataset_idx]
                grib2_value = dataset[grid_index - 1]
                
                # CSV時系列の中で完全一致を探す
                for csv_idx, csv_val in enumerate(csv_rain_series):
                    diff = abs(grib2_value - csv_val)
                    if diff < 0.01:
                        time_hours = csv_idx * 3
                        perfect_matches.append((dataset_idx, grib2_value, csv_idx, csv_val, time_hours))
                        print(f"Dataset{dataset_idx:2d}: GRIB2={grib2_value} = CSV t={time_hours}h(列{csv_idx+3}, 値{csv_val}) ★完全一致")
            
            print(f"\\n完全一致数: {len(perfect_matches)}")
            
            # デバッグ結果との比較
            debug_matches = [
                (0, 3.0, 5, 3, 15),    # Dataset1: ft=3 → CSV t=15h
                (5, 8.0, 4, 8, 12),    # Dataset6: ft=18 → CSV t=12h
                (17, 3.0, 5, 3, 15),   # Dataset18: ft=54 → CSV t=15h
                (21, 3.0, 5, 3, 15),   # Dataset22: ft=66 → CSV t=15h
            ]
            
            print(f"\\n=== デバッグ結果との対照 ===")
            for debug_idx, (expected_dataset, expected_grib2, expected_csv_idx, expected_csv_val, expected_time) in enumerate(debug_matches):
                found = False
                for match in perfect_matches:
                    dataset_idx, grib2_value, csv_idx, csv_val, time_hours = match
                    if (dataset_idx == expected_dataset and 
                        abs(grib2_value - expected_grib2) < 0.01 and
                        csv_idx == expected_csv_idx):
                        print(f"✓ Debug{debug_idx+1}: Dataset{dataset_idx} GRIB2={grib2_value} CSV t={time_hours}h 一致")
                        found = True
                        break
                
                if not found:
                    print(f"✗ Debug{debug_idx+1}: Dataset{expected_dataset} 期待値={expected_grib2} 一致せず")
            
        else:
            print(f"GRIB2インデックス範囲外エラー")
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("grib2_service.py実装のテスト開始")
    debug_service_test()
#!/usr/bin/env python3
"""
単一座標の極詳細解析
CSV参照データと GRIB2 の完全一致検証
"""

import pandas as pd
from services.grib2_service import Grib2Service

def meshcode_to_coordinate(x, y):
    """メッシュコード座標 → 緯度経度変換"""
    lat = (y + 0.5) * 30 / 3600
    lon = (x + 0.5) * 45 / 3600 + 100
    return lat, lon

def get_data_num(lat, lon, base_info):
    """緯度経度 → GRIB2グリッドインデックス変換"""
    y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
    x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
    grid_index = (y - 1) * base_info.x_num + x
    return grid_index, x, y

def debug_single_point():
    """単一座標の極詳細解析"""
    
    grib2_service = Grib2Service()
    
    # GRIB2データ解析
    base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file('data/guid_msm_grib2_20230602000000_rmax00.bin')
    
    # CSV比較データ読み込み
    try:
        df = pd.read_csv('data/shiga_rain.csv', encoding='shift_jis', header=None)
        
        # 特定の1点を詳細解析 (CSV 2行目, index=1)
        test_row = 1
        area_name = df.iloc[test_row, 0]
        mesh_x = df.iloc[test_row, 1]
        mesh_y = df.iloc[test_row, 2]
        csv_rain_series = df.iloc[test_row, 3:].values
        
        print(f"=== 単一座標の極詳細解析 ===")
        print(f"CSV行: {test_row}")
        print(f"エリア名: {area_name}")
        print(f"メッシュコード座標: X={mesh_x}, Y={mesh_y}")
        print(f"CSV雨量時系列 (全26値): {csv_rain_series}")
        print(f"CSV時系列長: {len(csv_rain_series)}")
        
        # 座標変換
        lat, lon = meshcode_to_coordinate(mesh_x, mesh_y)
        grid_index, grib_x, grib_y = get_data_num(lat, lon, base_info)
        
        print(f"\\n=== 座標変換結果 ===")
        print(f"緯度経度: lat={lat:.8f}, lon={lon:.8f}")
        print(f"GRIB2グリッド座標: x={grib_x}, y={grib_y}")
        print(f"GRIB2インデックス: {grid_index}")
        print(f"インデックス有効性: {1 <= grid_index <= len(guidance_data['data'][0])}")
        
        if 1 <= grid_index <= len(guidance_data['data'][0]):
            print(f"\\n=== 全データセットとの詳細比較 ===")
            
            # 各GRIB2データセットと全CSV時刻の比較
            for dataset_idx in range(min(26, len(guidance_data['data']))):
                dataset = guidance_data['data'][dataset_idx]
                grib2_value = dataset[grid_index - 1]
                
                print(f"\\nデータセット{dataset_idx:2d}: GRIB2値 = {grib2_value}")
                
                # 全CSV時刻と比較
                exact_matches = []
                close_matches = []  # 差0.5未満
                
                for csv_idx, csv_val in enumerate(csv_rain_series):
                    diff = abs(grib2_value - csv_val)
                    time_hours = csv_idx * 3  # 3時間間隔
                    
                    if diff < 0.01:
                        exact_matches.append((csv_idx, csv_val, time_hours, diff))
                    elif diff < 0.5:
                        close_matches.append((csv_idx, csv_val, time_hours, diff))
                
                if exact_matches:
                    print(f"  完全一致: ", end="")
                    for csv_idx, csv_val, time_h, diff in exact_matches:
                        print(f"t={time_h}h(列{csv_idx + 3}, 値{csv_val}, 差{diff:.6f})", end=" ")
                    print()
                elif close_matches:
                    print(f"  近似一致: ", end="")
                    for csv_idx, csv_val, time_h, diff in close_matches[:3]:  # 最初の3個
                        print(f"t={time_h}h(列{csv_idx + 3}, 値{csv_val}, 差{diff:.3f})", end=" ")
                    print()
                else:
                    print(f"  一致なし (最小差: {min(abs(grib2_value - val) for val in csv_rain_series):.3f})")
            
            # 逆方向: 各CSV時刻に最適なデータセットを探索
            print(f"\\n=== CSV時刻から最適データセット探索 ===")
            for csv_idx, csv_val in enumerate(csv_rain_series):
                time_hours = csv_idx * 3
                
                best_dataset = None
                best_diff = float('inf')
                
                for dataset_idx in range(min(26, len(guidance_data['data']))):
                    dataset = guidance_data['data'][dataset_idx]
                    grib2_value = dataset[grid_index - 1]
                    diff = abs(grib2_value - csv_val)
                    
                    if diff < best_diff:
                        best_diff = diff
                        best_dataset = dataset_idx
                
                if best_diff < 0.01:
                    print(f"  t={time_hours:2d}h (CSV列{csv_idx + 3}, 値{csv_val:3.0f}) -> Dataset{best_dataset:2d} (差{best_diff:.6f}) ★完全一致")
                elif best_diff < 0.5:
                    print(f"  t={time_hours:2d}h (CSV列{csv_idx + 3}, 値{csv_val:3.0f}) -> Dataset{best_dataset:2d} (差{best_diff:.3f}) ○近似")
                else:
                    print(f"  t={time_hours:2d}h (CSV列{csv_idx + 3}, 値{csv_val:3.0f}) -> Dataset{best_dataset:2d} (差{best_diff:.3f})")
            
            # データセットの統計
            print(f"\\n=== GRIB2データセット統計 ===")
            for dataset_idx in range(min(10, len(guidance_data['data']))):  # 最初の10個
                dataset = guidance_data['data'][dataset_idx]
                grib2_value = dataset[grid_index - 1]
                
                # このデータセットの全般的な値の統計
                unique_values = {}
                for val in dataset:
                    rounded_val = round(val, 1)
                    unique_values[rounded_val] = unique_values.get(rounded_val, 0) + 1
                
                sorted_values = sorted(unique_values.items(), key=lambda x: x[1], reverse=True)[:5]
                print(f"  Dataset{dataset_idx:2d}: この座標={grib2_value}, 全体上位値={sorted_values}")
            
        else:
            print(f"GRIB2インデックス範囲外エラー")
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("単一座標の極詳細解析開始")
    debug_single_point()
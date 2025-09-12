#!/usr/bin/env python3
"""
GRIB2とCSVの完全一致検証
座標マッピングとデータ値の詳細比較
"""

import pandas as pd
from services.grib2_service import Grib2Service

def debug_exact_matching():
    """GRIB2データとCSVデータの完全一致検証"""
    
    # GRIB2データ解析
    grib2_service = Grib2Service()
    
    print("=== GRIB2 guidance データ解析 ===")
    base_info, guidance_data = grib2_service.unpack_guidance_grib2_from_file('data/guid_msm_grib2_20230602000000_rmax00.bin')
    
    print(f"base_info.s_lat: {base_info.s_lat}")
    print(f"base_info.s_lon: {base_info.s_lon}")
    print(f"base_info.d_lat: {base_info.d_lat}")
    print(f"base_info.d_lon: {base_info.d_lon}")
    print(f"base_info.x_num: {base_info.x_num}")
    print(f"base_info.y_num: {base_info.y_num}")
    print(f"base_info.grid_num: {base_info.grid_num}")
    
    if len(guidance_data['data']) > 0:
        first_dataset = guidance_data['data'][0]  # ft=3のデータ
        print(f"第1データセット要素数: {len(first_dataset)}")
        print(f"最初の10要素: {first_dataset[:10]}")
    
    # CSV比較データ読み込み
    print("\n=== CSV参照データ読み込み ===")
    try:
        df = pd.read_csv('data/shiga_rain.csv', encoding='shift_jis', header=None)
        print(f"CSV形状: {df.shape}")
        
        # 最初の5行のデータを詳細確認
        print(f"\nCSV最初の5行:")
        for i in range(min(5, df.shape[0])):
            if i == 0:
                print(f"  行{i+1} (ヘッダー): スキップ")
                continue
            
            area_name = df.iloc[i, 0]
            x_coord = df.iloc[i, 1]
            y_coord = df.iloc[i, 2]
            rain_values = df.iloc[i, 3:8].values
            
            # 座標からlat/lonを逆算（VBAロジック使用）
            lat = base_info.s_lat / 1000000 - (y_coord - 1) * (base_info.d_lat / 1000000)
            lon = base_info.s_lon / 1000000 + (x_coord - 1) * (base_info.d_lon / 1000000)
            
            # get_data_numでグリッドインデックス計算
            y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
            x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
            grid_index = (y - 1) * base_info.x_num + x
            
            print(f"  行{i+1}: X={x_coord}, Y={y_coord}")
            print(f"    -> lat={lat:.6f}, lon={lon:.6f}")
            print(f"    -> 逆算X={x}, Y={y}, grid_index={grid_index}")
            print(f"    CSV雨量[3:8]: {rain_values}")
            
            # GRIB2データから対応する値を取得
            if 0 <= grid_index - 1 < len(first_dataset):  # 0ベースインデックス
                grib2_value = first_dataset[grid_index - 1]
                csv_first_rain = rain_values[0] if len(rain_values) > 0 else 0
                print(f"    GRIB2値(ft=3): {grib2_value}")
                print(f"    CSV値(4列目): {csv_first_rain}")
                print(f"    一致: {'○' if abs(grib2_value - csv_first_rain) < 0.01 else '×'}")
            else:
                print(f"    GRIB2値: 範囲外 (grid_index={grid_index})")
            print()
        
        # 特定座標での詳細検証
        print(f"\n=== 特定座標での詳細検証 ===")
        test_coords = [
            (2869, 4187),  # CSV 2行目
            (2869, 4188),  # CSV 3行目
            (2871, 4185),  # CSV 4行目
        ]
        
        for x_coord, y_coord in test_coords:
            # CSVから該当行を検索
            csv_rows = df[(df.iloc[:, 1] == x_coord) & (df.iloc[:, 2] == y_coord)]
            if len(csv_rows) > 0:
                csv_row = csv_rows.iloc[0]
                csv_rain_series = csv_row.iloc[3:].values
                
                # 座標変換
                lat = base_info.s_lat / 1000000 - (y_coord - 1) * (base_info.d_lat / 1000000)
                lon = base_info.s_lon / 1000000 + (x_coord - 1) * (base_info.d_lon / 1000000)
                
                # グリッドインデックス計算
                y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
                x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
                grid_index = (y - 1) * base_info.x_num + x
                
                print(f"座標({x_coord}, {y_coord}):")
                print(f"  lat={lat:.6f}, lon={lon:.6f}")
                print(f"  grid_index={grid_index}")
                
                if 0 <= grid_index - 1 < len(first_dataset):
                    grib2_value = first_dataset[grid_index - 1]
                    print(f"  GRIB2値: {grib2_value}")
                    print(f"  CSV雨量系列: {csv_rain_series[:5]}")  # 最初の5個
                    print(f"  完全一致: {'○' if abs(grib2_value - csv_rain_series[0]) < 0.01 else '×'}")
                else:
                    print(f"  GRIB2値: 範囲外")
                print()
                
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("GRIB2とCSVの完全一致検証開始")
    debug_exact_matching()
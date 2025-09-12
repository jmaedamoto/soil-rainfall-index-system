#!/usr/bin/env python3
"""
座標変換のテストとデバッグ
"""

import pandas as pd
from services.grib2_service import Grib2Service

def test_coordinate_conversion():
    """座標変換のテスト"""
    print("=== 座標変換テスト ===")
    
    # CSVデータを読み込み
    csv_df = pd.read_csv("data/shiga_swi.csv", header=None, skiprows=1, encoding='shift-jis')
    
    # GRIB2基本情報を取得
    grib2_service = Grib2Service()
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(
        "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    )
    
    print("GRIB2基本情報:")
    print(f"  グリッド数: {base_info.grid_num}")
    print(f"  X軸数: {base_info.x_num}, Y軸数: {base_info.y_num}")
    print(f"  緯度範囲: {base_info.s_lat/1000000} - {base_info.e_lat/1000000}")
    print(f"  経度範囲: {base_info.s_lon/1000000} - {base_info.e_lon/1000000}")
    print(f"  緯度間隔: {base_info.d_lat/1000000}")
    print(f"  経度間隔: {base_info.d_lon/1000000}")
    
    swi_values = swi_data.get('swi', [])
    
    # CSVの最初の数行でテスト
    print("\n座標変換テスト:")
    for i in range(5):
        row = csv_df.iloc[i]
        area = row[0]
        csv_x, csv_y = int(row[1]), int(row[2])
        expected_swi = row[6]
        
        # VBAのmeshcode_to_coordinate関数を再現
        # まずメッシュコードが必要だが、CSVにはX,Y座標しかない
        # 座標からメッシュコードを逆算する必要がある
        
        # VBA式: x = Val(Mid(code, 3, 2)) * 80 + Val(Mid(code, 6, 1)) * 10 + Val(Mid(code, 8, 1))
        # 逆算: code = ?
        # 単純化のため、座標から緯度経度を直接計算
        
        # VBA式を再現: lat = (y + 0.5) * 30 / 3600, lon = (x + 0.5) * 45 / 3600 + 100
        lat = (csv_y + 0.5) * 30 / 3600
        lon = (csv_x + 0.5) * 45 / 3600 + 100
        
        # VBAのget_data_num関数を再現
        # y = Int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        # x = Int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        y_grid = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        x_grid = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        
        # data_num = (y - 1) * base_info.x_num + x
        data_num = (y_grid - 1) * base_info.x_num + x_grid
        
        print(f"\n行{i+2}: {area}")
        print(f"  CSV座標: X={csv_x}, Y={csv_y}")
        print(f"  計算された緯度経度: lat={lat:.6f}, lon={lon:.6f}")
        print(f"  GRIB2グリッド座標: X={x_grid}, Y={y_grid}")
        print(f"  データ番号: {data_num}")
        print(f"  データ番号範囲チェック: {0 <= data_num < len(swi_values)}")
        
        if 0 <= data_num < len(swi_values):
            grib2_swi_raw = swi_values[data_num]
            grib2_swi_divided = grib2_swi_raw / 10  # VBAでは÷10する
            print(f"  GRIB2 SWI値: {grib2_swi_raw} (÷10 = {grib2_swi_divided})")
            print(f"  CSV期待値: {expected_swi}")
            print(f"  差: {abs(grib2_swi_divided - expected_swi):.2f}")
            
            if abs(grib2_swi_divided - expected_swi) < 1.0:
                print(f"  OK 一致（差 < 1.0）")
            else:
                print(f"  NG 不一致")
        else:
            print(f"  NG データ番号が範囲外")

if __name__ == "__main__":
    test_coordinate_conversion()
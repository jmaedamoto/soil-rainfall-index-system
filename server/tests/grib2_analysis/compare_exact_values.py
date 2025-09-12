#!/usr/bin/env python3
"""
CSVの正確な値と現在の処理結果を比較
"""

import pandas as pd
import logging
from services.grib2_service import Grib2Service

# ログレベルを設定してエラーを確認
logging.basicConfig(level=logging.ERROR)

def compare_exact_swi_values():
    """CSVとの正確な比較"""
    print("=== CSVとの正確な値比較 ===")
    
    # CSVデータを読み込み
    try:
        csv_df = pd.read_csv("data/shiga_swi.csv", header=None, skiprows=1, encoding='shift-jis')
        print(f"CSVデータ: {len(csv_df)}件")
        
        # 最初の5行のデータを表示
        print("\nCSV最初の5行の初期SWI値:")
        for i in range(5):
            row = csv_df.iloc[i]
            area = row[0]
            x, y = row[1], row[2]
            initial_swi = row[6]  # 7列目が初期SWI値
            print(f"  行{i+2}: エリア={area}, X={x}, Y={y}, 初期SWI={initial_swi}")
            
        # GRIB2からの抽出値も表示
        grib2_service = Grib2Service()
        
        print("\nGRIB2処理結果:")
        base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(
            "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        )
        
        swi_values = swi_data.get('swi', [])
        print(f"SWI値の数: {len(swi_values)}")
        print(f"最初の10個のSWI値: {swi_values[:10]}")
        print(f"SWI値の範囲: {min(swi_values)} - {max(swi_values)}")
        print(f"ユニークな値の数: {len(set(swi_values))}")
        
        # ÷10した値（VBAで行う処理）
        swi_divided = [val / 10 for val in swi_values[:10]]
        print(f"÷10後の最初の10個: {swi_divided}")
        
        # 0以外の値を探す
        non_zero_values = [val for val in swi_values if val != 0]
        print(f"非ゼロ値の数: {len(non_zero_values)}")
        if non_zero_values:
            print(f"非ゼロ値の例 (最初の10個): {non_zero_values[:10]}")
        
        # 座標変換テスト
        from services.calculation_service import CalculationService
        calc_service = CalculationService()
        
        print("\n座標変換テスト:")
        # CSVの最初の行の座標を使用
        first_row = csv_df.iloc[0]
        csv_x, csv_y = int(first_row[1]), int(first_row[2])
        print(f"CSV座標: X={csv_x}, Y={csv_y}")
        
        # CSVのX,Y座標から緯度経度を計算（VBAのmeshcode_to_coordinate相当）
        lat = (csv_y + 0.5) * 30 / 3600
        lon = (csv_x + 0.5) * 45 / 3600 + 100
        print(f"計算された緯度経度: lat={lat:.6f}, lon={lon:.6f}")
        
        # VBAのget_data_num関数を再現
        y_grid = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        x_grid = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        # VBA: get_data_num = (y - 1) * base_info.x_num + x 
        # VBAは1ベース配列だが、Pythonは0ベース配列なので-1が必要
        data_num_vba = (y_grid - 1) * base_info.x_num + x_grid  # VBA結果
        data_num = data_num_vba - 1  # Python 0ベースアクセス用
        
        print(f"GRIB2グリッド座標: x={x_grid}, y={y_grid}")
        print(f"計算されたデータ番号: {data_num}")
        print(f"データ番号範囲チェック: {0 <= data_num < len(swi_values)}")
        
        if 0 <= data_num < len(swi_values):
            grib2_swi = swi_values[data_num]
            csv_swi = first_row[6]
            print(f"GRIB2 SWI値: {grib2_swi} (÷10 = {grib2_swi/10})")
            print(f"CSV SWI値: {csv_swi}")
            print(f"差: {abs(grib2_swi/10 - csv_swi)}")
        else:
            print(f"データ番号が範囲外: {data_num}")
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    compare_exact_swi_values()
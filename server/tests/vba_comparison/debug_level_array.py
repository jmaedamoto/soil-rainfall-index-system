#!/usr/bin/env python3
"""
level配列の詳細確認とgrib2_serviceでの値抽出の検証
"""

from services.grib2_service import Grib2Service
import pandas as pd

def debug_level_array_and_extraction():
    """level配列とgrib2_serviceでの値抽出の詳細デバッグ"""
    print("=== level配列とgrib2_service詳細デバッグ ===")
    
    # CSVの最初の行の座標を取得
    csv_df = pd.read_csv("data/shiga_swi.csv", header=None, skiprows=1, encoding='shift-jis')
    first_row = csv_df.iloc[0]
    csv_x, csv_y = int(first_row[1]), int(first_row[2])
    expected_swi = first_row[6]
    print(f"テスト座標: X={csv_x}, Y={csv_y}, 期待値={expected_swi}")
    
    grib2_service = Grib2Service()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    # 座標変換
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    
    # GRIB2ファイルから基本情報を取得
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    swi_values = swi_data.get('swi', [])
    
    # data_num計算（VBA完全対応）
    y_grid = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
    x_grid = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
    data_num_vba = (y_grid - 1) * base_info.x_num + x_grid  # VBA結果
    data_num = data_num_vba - 1  # Python 0ベースアクセス用
    
    print(f"座標変換: data_num={data_num}")
    print(f"grib2_service結果: swi_values[{data_num}] = {swi_values[data_num]} (÷10 = {swi_values[data_num]/10})")
    
    # ここからlevel配列の詳細解析を開始
    with open(swi_file, 'rb') as f:
        data = f.read()
    
    print(f"\n=== level配列の詳細構築プロセス ===")
    
    # セクション5,6,7の位置を計算
    position = 16  # セクション1開始
    section_size = grib2_service.get_dat(data, position, 4)
    position += section_size  # セクション3へ
    
    section_size = grib2_service.get_dat(data, position, 4)  # セクション3
    position += section_size  # セクション4へ
    
    section_size = grib2_service.get_dat(data, position, 4)  # セクション4
    data_type = grib2_service.get_dat(data, position + 22, 1)
    position += section_size  # セクション5へ
    
    print(f"データタイプ: {data_type}")
    if data_type != 200:
        print("ERROR: データタイプが200ではありません")
        return
    
    # セクション5: レベル配列読み取り
    section_size = grib2_service.get_dat(data, position, 4)
    bit_num = grib2_service.get_dat(data, position + 11, 1)
    level_max = grib2_service.get_dat(data, position + 12, 2)
    level_num = grib2_service.get_dat(data, position + 14, 2)
    
    print(f"セクション5パラメータ: bit_num={bit_num}, level_max={level_max}, level_num={level_num}")
    
    # 手動でlevel配列を構築（grib2_serviceのロジック再現）
    manual_level = []
    print(f"level配列構築開始:")
    for i in range(1, level_max + 1):
        val = grib2_service.get_dat(data, position + 15 + 2 * i, 2)
        if val >= 32768:
            val = val - 65536
        manual_level.append(val)
        if i <= 20:  # 最初の20個を表示
            print(f"  level[{i}] = {val}")
    
    print(f"level配列完成: 長さ={len(manual_level)}")
    print(f"期待される level[14] = {manual_level[13] if len(manual_level) > 13 else 'N/A'} (1ベース→0ベース変換)")
    
    # 実際のd=14での値抽出確認
    print(f"\n=== 実際のd=14での値抽出確認 ===")
    d = 14
    if 1 <= d <= len(manual_level):
        level_value = manual_level[d - 1]  # 1ベース→0ベース
        print(f"d={d} → level[{d}-1] = level[{d-1}] = {level_value}")
        print(f"期待値: 70.0, 実際: {level_value/10}, 差: {abs(70.0 - level_value/10)}")
    else:
        print(f"d={d} が範囲外: len(level)={len(manual_level)}")

if __name__ == "__main__":
    debug_level_array_and_extraction()

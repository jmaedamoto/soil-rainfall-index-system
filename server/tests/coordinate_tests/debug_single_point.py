#!/usr/bin/env python3
"""
特定の座標でのランレングス展開の詳細デバッグ
"""

from services.grib2_service import Grib2Service
import pandas as pd

def debug_single_point_extraction():
    """特定座標での詳細デバッグ"""
    print("=== 特定座標でのランレングス展開詳細デバッグ ===")
    
    # CSVの最初の行（期待値70）
    csv_df = pd.read_csv("data/shiga_swi.csv", header=None, skiprows=1, encoding='shift-jis')
    first_row = csv_df.iloc[0]
    csv_x, csv_y = int(first_row[1]), int(first_row[2])
    expected_swi = first_row[6]
    
    print(f"テスト座標: X={csv_x}, Y={csv_y}")
    print(f"CSV期待値: {expected_swi}")
    
    # 座標からdata_numを計算
    grib2_service = Grib2Service()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
    
    lat = (csv_y + 0.5) * 30 / 3600
    lon = (csv_x + 0.5) * 45 / 3600 + 100
    y_grid = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
    x_grid = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
    data_num = (y_grid - 1) * base_info.x_num + x_grid
    
    print(f"計算されたdata_num: {data_num}")
    
    # このdata_numでのランレングス展開を詳細トレース
    # GRIB2ファイルを再度解析してランレングス部分のd値をトレース
    with open(swi_file, 'rb') as f:
        data = f.read()
    
    # セクション7のランレングス展開部分に移動
    position = 16  # セクション1開始
    section_size = grib2_service.get_dat(data, position, 4)
    position += section_size  # セクション2はスキップ
    
    section_size = grib2_service.get_dat(data, position, 4)  # セクション3
    position += section_size
    
    section_size = grib2_service.get_dat(data, position, 4)  # セクション4
    position += section_size
    
    # セクション5詳細
    section_size = grib2_service.get_dat(data, position, 4)
    bit_num = grib2_service.get_dat(data, position + 11, 1)
    level_max = grib2_service.get_dat(data, position + 12, 2)
    level_num = grib2_service.get_dat(data, position + 14, 2)
    
    # レベル配列取得
    level = []
    for i in range(1, level_max + 1):
        if position + 15 + 2 * i < len(data):
            val = grib2_service.get_dat(data, position + 15 + 2 * i, 2)
            if val >= 65536 // 2:
                val = int(val - 65536 // 2)
            level.append(val)
    
    position += section_size
    
    # セクション6（ビットマップ）をスキップ
    section_size = grib2_service.get_dat(data, position, 4)
    position += section_size
    
    # セクション7でdata_num位置のd値をトレース
    section_size = grib2_service.get_dat(data, position, 4)
    byte_size = bit_num // 8
    s_position = position + 5
    e_position = position + section_size
    
    print(f"ランレングス展開パラメータ:")
    print(f"  bit_num: {bit_num}, byte_size: {byte_size}")
    print(f"  level_max: {level_max}, level_num: {level_num}")
    print(f"  s_position: {s_position}, e_position: {e_position}")
    
    # data_num位置までのランレングス展開をトレース
    d_index = 0
    p = s_position
    found_target = False
    
    print(f"\ndata_num={data_num}に到達するまでのd値トレース:")
    
    while p < e_position and d_index < data_num + 10:  # target周辺も含めて調査
        d = grib2_service.get_dat(data, p, byte_size)
        p += byte_size
        
        if d > level_num:
            print(f"  エラー: d({d}) > level_num({level_num})で停止")
            break
            
        dd = grib2_service.get_dat(data, p, byte_size)
        
        # data_num周辺のd値を記録
        if data_num - 5 <= d_index <= data_num + 5:
            level_val = level[d - 1] if 1 <= d <= len(level) else 0
            print(f"  d_index={d_index}: d={d}, dd={dd}, level[{d}]={level_val} (÷10={level_val/10})")
            if d_index == data_num:
                found_target = True
                print(f"    ★ TARGET位置: 期待値{expected_swi}に対してd={d}→level[{d}]={level_val}(÷10={level_val/10})")
        
        if dd <= level_max:
            d_index += 1
        else:
            # ランレングス圧縮処理
            lngu = 2 ** bit_num - 1 - level_max
            nlength = 0
            p2 = 1
            
            while p <= e_position and dd > level_max:
                nlength = nlength + ((lngu ** (p2 - 1)) * (dd - level_max - 1))
                p += byte_size
                if p + byte_size > len(data):
                    break
                dd = grib2_service.get_dat(data, p, byte_size)
                p2 += 1
            
            if data_num - 5 <= d_index <= data_num + nlength + 5:
                print(f"    ランレングス: {nlength + 1}個のlevel[{d}]を展開")
            
            d_index += nlength + 1
    
    if not found_target:
        print(f"警告: data_num={data_num}位置に到達できませんでした")

if __name__ == "__main__":
    debug_single_point_extraction()

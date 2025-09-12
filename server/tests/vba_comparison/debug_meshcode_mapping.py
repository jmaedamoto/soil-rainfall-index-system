#!/usr/bin/env python3
"""
バイナリ読み取り位置の完全検証
debug_single_point.pyとgrib2_service.pyの処理を並列実行して差異を特定
"""

from services.grib2_service import Grib2Service
import pandas as pd

def debug_binary_position_mapping():
    """バイナリ読み取り位置の完全検証"""
    print("=== バイナリ読み取り位置完全検証 ===")
    
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
    
    # VBAのget_data_numは1ベースだが、Pythonでは0ベースアクセスなので-1が必要
    data_num_vba = (y_grid - 1) * base_info.x_num + x_grid  # VBA結果
    data_num = data_num_vba - 1  # Python 0ベースアクセス用
    
    print(f"座標変換: y_grid={y_grid}, x_grid={x_grid}")
    print(f"VBAのget_data_num結果: {data_num_vba}")
    print(f"Python配列アクセス用: {data_num}")
    
    print(f"計算結果: data_num={data_num}")
    print(f"grib2_service結果: swi_values[{data_num}] = {swi_values[data_num]} (÷10 = {swi_values[data_num]/10})")
    
    # debug_single_point.py相当の処理（直接実装）
    with open(swi_file, 'rb') as f:
        data = f.read()
    
    print(f"\n=== debug_single_point.py相当の直接処理 ===")
    
    # セクション5,6,7の位置を計算（grib2_service.pyと同じ順序で）
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
    
    level = []
    for i in range(1, level_max + 1):
        val = grib2_service.get_dat(data, position + 15 + 2 * i, 2)
        if val >= 32768:
            val = val - 65536
        level.append(val)
    
    print(f"レベル配列確認: level[14]={level[13]} (期待値700)")
    position += section_size  # セクション6へ
    
    # セクション6スキップ
    section_size = grib2_service.get_dat(data, position, 4)
    position += section_size  # セクション7へ
    
    # セクション7: データセクション
    section_size = grib2_service.get_dat(data, position, 4)
    s_position = position + 5
    e_position = position + section_size
    byte_size = bit_num // 8
    
    print(f"ランレングス開始位置: {s_position}")
    print(f"TARGET位置 {data_num} までのd値を手動トレース:")
    
    # 手動ランレングス展開（debug_single_point.py相当）
    d_index = 0
    p = s_position
    target_found = False
    
    iteration = 0
    while p < e_position and d_index <= data_num + 5:
        if p + 2 * byte_size > len(data):
            break
            
        d = grib2_service.get_dat(data, p, byte_size)
        p += byte_size
        
        if d > level_num:
            print(f"  エラー: d({d}) > level_num({level_num})で停止")
            break
            
        dd = grib2_service.get_dat(data, p, byte_size)
        
        # TARGET位置近くのログ
        if data_num - 2 <= d_index <= data_num + 2:
            level_val = level[d - 1] if 1 <= d <= len(level) else 0
            print(f"  d_index={d_index}: d={d}, dd={dd}, level[{d}]={level_val} (÷10={level_val/10})")
            
            if d_index == data_num:
                target_found = True
                print(f"    ★ TARGET位置発見: d={d} → level[{d}]={level_val} → ÷10={level_val/10}")
        
        if dd <= level_max:
            d_index += 1
        else:
            # ランレングス圧縮
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
            
            if data_num - 2 <= d_index <= data_num + nlength + 2:
                level_val = level[d - 1] if 1 <= d <= len(level) else 0
                print(f"  ランレングス: d_index={d_index}-{d_index+nlength}, d={d}, level[{d}]={level_val}")
                
            d_index += nlength + 1
            
        iteration += 1
        if iteration > 1000 and d_index < data_num - 10:
            continue
        if d_index > data_num + 10:
            break
    
    if target_found:
        print(f"\n手動トレース成功")
    else:
        print(f"\n手動トレースでTARGET位置に到達できませんでした")
    
    # 比較結果
    if target_found and swi_values[data_num] != 0:
        print(f"\n=== 比較結果 ===")
        print(f"期待値: {expected_swi}")
        print(f"grib2_service結果: {swi_values[data_num]/10}")
        print(f"手動トレース結果: {level[d-1]/10 if 1 <= d <= len(level) else 0}")

if __name__ == "__main__":
    debug_binary_position_mapping()

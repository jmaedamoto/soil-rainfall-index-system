#!/usr/bin/env python3
"""
ランレングス展開の各ステップでのd値抽出を詳細トレース
grib2_serviceと手動トレースの差異を特定
"""

from services.grib2_service import Grib2Service
import pandas as pd
import logging

# ログレベルを設定してエラーを確認
logging.basicConfig(level=logging.ERROR)

def debug_runlength_step_by_step():
    """ランレングス展開の各ステップでのd値抽出を詳細トレース"""
    print("=== ランレングス展開ステップバイステップデバッグ ===")
    
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
    
    # 手動でランレングス展開を実行し、TARGET位置での詳細を確認
    with open(swi_file, 'rb') as f:
        data = f.read()
    
    print(f"\n=== 手動ランレングス展開でのTARGET位置詳細トレース ===")
    
    # セクション5,6,7の位置を計算
    position = 16  # セクション1開始
    section_size = grib2_service.get_dat(data, position, 4)
    position += section_size  # セクション3へ
    
    section_size = grib2_service.get_dat(data, position, 4)  # セクション3
    position += section_size  # セクション4へ
    
    section_size = grib2_service.get_dat(data, position, 4)  # セクション4
    position += section_size  # セクション5へ
    
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
    
    position += section_size  # セクション6へ
    
    # セクション6スキップ
    section_size = grib2_service.get_dat(data, position, 4)
    position += section_size  # セクション7へ
    
    # セクション7: データセクション
    section_size = grib2_service.get_dat(data, position, 4)
    s_position = position + 5
    e_position = position + section_size
    byte_size = bit_num // 8
    
    print(f"TARGET位置 {data_num} でのd値を手動トレース:")
    print(f"level[13]={level[12]}, level[14]={level[13]} (期待されるd=14の場合)")
    
    # 手動ランレングス展開（TARGET位置のみフォーカス）
    d_index = 0
    p = s_position
    target_found = False
    
    while p < e_position and d_index <= data_num + 5:
        if p + 2 * byte_size > len(data):
            break
            
        d = grib2_service.get_dat(data, p, byte_size)
        p += byte_size
        
        if d > level_num:
            print(f"  エラー: d({d}) > level_num({level_num})で停止")
            break
            
        dd = grib2_service.get_dat(data, p, byte_size)
        
        # TARGET位置での詳細ログ
        if d_index == data_num:
            target_found = True
            level_val = level[d - 1] if 1 <= d <= len(level) else 0
            print(f"  ★ TARGET位置発見:")
            print(f"    d_index={d_index}")
            print(f"    d={d} (取得されたインデックス)")
            print(f"    dd={dd}")
            print(f"    level[{d}] = level[{d-1}] = {level_val} (期待値700)")
            print(f"    ÷10結果: {level_val/10} (期待値70)")
            print(f"    grib2_service結果との比較:")
            print(f"      手動トレース: {level_val/10}")
            print(f"      grib2_service: {swi_values[data_num]/10}")
            print(f"      差: {abs(level_val/10 - swi_values[data_num]/10)}")
        
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
                
            d_index += nlength + 1
        
        if target_found:
            break
    
    if not target_found:
        print(f"警告: TARGET位置 {data_num} に到達できませんでした")

if __name__ == "__main__":
    debug_runlength_step_by_step()
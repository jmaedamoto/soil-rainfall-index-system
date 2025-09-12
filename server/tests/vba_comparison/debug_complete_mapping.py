#!/usr/bin/env python3
"""
VBAとPythonの完全なバイト単位での比較
"""

from services.grib2_service import Grib2Service

def debug_complete_vba_mapping():
    """VBAとの完全なバイト単位比較"""
    print("=== VBA完全バイト単位比較デバッグ ===")
    
    grib2_service = Grib2Service()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    with open(swi_file, 'rb') as f:
        data = f.read()
    
    # VBAの処理順序を完全再現
    position = 0
    
    # セクション0
    position = 16
    
    # セクション1
    section_size = grib2_service.get_dat(data, position, 4)
    print(f"セクション1サイズ: {section_size}")
    position += section_size
    
    # セクション3
    section_size = grib2_service.get_dat(data, position, 4)
    print(f"セクション3サイズ: {section_size}")
    grid_num = grib2_service.get_dat(data, position + 6, 4)
    x_num = grib2_service.get_dat(data, position + 30, 4)
    y_num = grib2_service.get_dat(data, position + 34, 4)
    s_lat = grib2_service.get_dat(data, position + 46, 4)
    s_lon = grib2_service.get_dat(data, position + 50, 4)
    d_lat = grib2_service.get_dat(data, position + 67, 4)
    d_lon = grib2_service.get_dat(data, position + 63, 4)
    print(f"グリッド: {grid_num}, X={x_num}, Y={y_num}")
    position += section_size
    
    # セクション4
    section_size = grib2_service.get_dat(data, position, 4)
    data_type = grib2_service.get_dat(data, position + 22, 1)
    print(f"セクション4サイズ: {section_size}, データタイプ: {data_type}")
    position += section_size
    
    if data_type != 200:
        print("ERROR: data_type != 200")
        return
    
    # セクション5: データ表現セクション（VBA完全対応）
    section_size = grib2_service.get_dat(data, position, 4)
    print(f"セクション5サイズ: {section_size}")
    
    bit_num = grib2_service.get_dat(data, position + 11, 1)
    level_max = grib2_service.get_dat(data, position + 12, 2)
    level_num = grib2_service.get_dat(data, position + 14, 2)
    
    print(f"bit_num: {bit_num}, level_max: {level_max}, level_num: {level_num}")
    
    # VBAのレベル配列読み取り（完全再現）
    level = []
    print("レベル配列構築:")
    for i in range(1, level_max + 1):
        val = grib2_service.get_dat(data, position + 15 + 2 * i, 2)
        if val >= 32768:  # signed 16-bit
            val = val - 65536
        level.append(val)
        if i <= 15 or i == level_max:
            print(f"  level[{i}] = {val}")
    
    position += section_size
    
    # セクション6: ビットマップセクション
    section_size = grib2_service.get_dat(data, position, 4)
    print(f"セクション6サイズ: {section_size}")
    position += section_size
    
    # セクション7: データセクション
    section_size = grib2_service.get_dat(data, position, 4)
    print(f"セクション7サイズ: {section_size}")
    
    # VBAのunpack_runlengthパラメータ
    s_position = position + 5
    e_position = position + section_size
    byte_size = bit_num // 8
    lngu = 2 ** bit_num - 1 - level_max
    
    print(f"ランレングスパラメータ:")
    print(f"  s_position: {s_position}")
    print(f"  e_position: {e_position}")
    print(f"  byte_size: {byte_size}")
    print(f"  lngu: {lngu}")
    
    # VBAのランレングス展開を完全に再現
    print(f"\nVBAランレングス展開（完全再現）:")
    
    result = [0.0] * grid_num
    d_index = 0  # Python 0ベース（VBAの1ベースに対応）
    p = s_position
    
    # TARGET位置までの処理をトレース
    target_d_index = 4025749  # Python 0ベース
    trace_start = target_d_index - 5
    trace_end = target_d_index + 5
    
    iteration = 0
    while p < e_position and d_index < grid_num:
        if p + 2 * byte_size > len(data):
            break
        
        # VBA: d = get_dat(buf, p, bit_num / 8)
        d = grib2_service.get_dat(data, p, byte_size)
        p += byte_size
        
        # VBA: dd = get_dat(buf, p, bit_num / 8)
        dd = grib2_service.get_dat(data, p, byte_size)
        p += byte_size
        
        # VBA: If d > level_num Then MsgBox ... Stop
        if d > level_num:
            print(f"VBA ERROR: d({d}) > level_num({level_num}) at d_index={d_index}")
            # VBAではStopするが、実際のCSVデータが存在するため何らかの処理継続
            # 範囲外の場合は0を使用
            d = min(d, len(level))
        
        # TARGET位置周辺の詳細ログ
        if trace_start <= d_index <= trace_end:
            print(f"  d_index={d_index}: d={d}, dd={dd}, level[{d}]={level[d-1] if 1<=d<=len(level) else 'N/A'}")
        
        # VBA: If dd <= level_max Then
        if dd <= level_max:
            # VBA: data(d_index) = level(d)
            if 1 <= d <= len(level):
                result[d_index] = float(level[d - 1])
            else:
                result[d_index] = 0.0
            d_index += 1
        else:
            # ランレングス圧縮処理
            nlength = 0
            p2 = 1
            
            # VBA: Do While p <= e_position And dd > level_max
            while p <= e_position and dd > level_max:
                # VBA: nlength = nlength + ((lngu ^ (p2 - 1)) * (dd - level_max - 1))
                nlength = nlength + ((lngu ** (p2 - 1)) * (dd - level_max - 1))
                p += byte_size
                if p + byte_size > len(data):
                    break
                dd = grib2_service.get_dat(data, p, byte_size)
                p2 += 1
            
            if trace_start <= d_index <= trace_end + nlength + 1:
                print(f"  ランレングス: d_index={d_index}-{d_index+nlength}, d={d}, nlength={nlength}")
            
            # VBA: For i = 1 To nlength + 1
            for i in range(nlength + 1):
                if d_index >= grid_num:
                    break
                
                if 1 <= d <= len(level):
                    result[d_index] = float(level[d - 1])
                else:
                    result[d_index] = 0.0
                    
                if d_index == target_d_index:
                    print(f"  ★TARGET FOUND: d_index={d_index}, d={d}, level[{d}]={level[d-1] if 1<=d<=len(level) else 0}, result={result[d_index]}")
                
                d_index += 1
        
        iteration += 1
        if iteration > 1000 and d_index < trace_start:  # 効率化
            continue
        if d_index > trace_end + 100:  # TARGET通過後は終了
            break
    
    print(f"\n結果:")
    print(f"TARGET位置 {target_d_index} の値: {result[target_d_index]}")
    print(f"期待値: 70.0")
    print(f"一致: {'YES' if abs(result[target_d_index] - 70.0) < 0.01 else 'NO'}")

if __name__ == "__main__":
    debug_complete_vba_mapping()

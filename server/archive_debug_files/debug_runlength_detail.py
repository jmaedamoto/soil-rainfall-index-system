#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ランレングス処理の詳細デバッグ - 特定位置での処理をトレース
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.grib2_service import Grib2Service

class DebugGrib2Service(Grib2Service):
    """デバッグ用のGrib2Service - ランレングス処理に詳細ログ追加"""
    
    def unpack_runlength(self, data, bit_num, level_num, level_max, grid_num, level, s_position, e_position):
        """ランレングス展開（詳細デバッグ版）"""
        print(f"\n=== ランレングス展開開始 ===")
        print(f"bit_num: {bit_num}, level_num: {level_num}, level_max: {level_max}")
        print(f"grid_num: {grid_num}, s_position: {s_position}, e_position: {e_position}")
        
        target_d_index = 3992468  # 追跡したい位置
        
        try:
            lngu = 2 ** bit_num - 1 - level_max
            data_result = [0.0] * (grid_num + 1)
            d_index = 1
            p = s_position
            byte_size = bit_num // 8
            
            print(f"lngu: {lngu}, byte_size: {byte_size}")
            print(f"level配列例: {level[1:6] if len(level) > 5 else level}")
            
            loop_count = 0
            
            while p < e_position and d_index <= grid_num:
                loop_count += 1
                
                if loop_count <= 10 or (target_d_index - 5 <= d_index <= target_d_index + 5):
                    print(f"\nLoop {loop_count}: d_index={d_index}, p={p}")
                
                if p + 2 * byte_size > len(data):
                    print(f"データ終端到達: p={p}, len(data)={len(data)}")
                    break
                
                d = self.get_dat(data, p, byte_size)
                p += byte_size
                
                if d > level_num:
                    print(f"VBA停止条件: d({d}) > level_num({level_num})")
                    break
                
                dd = self.get_dat(data, p, byte_size)
                
                # ターゲット位置周辺での詳細ログ
                if target_d_index - 5 <= d_index <= target_d_index + 5:
                    print(f"★ TARGET近傍: d_index={d_index}, d={d}, dd={dd}")
                    if 1 <= d < len(level):
                        print(f"  level[{d}] = {level[d]}")
                    else:
                        print(f"  level[{d}] = 0 (範囲外)")
                
                if dd <= level_max:
                    if d_index == target_d_index:
                        print(f"★★ TARGET設定: d_index={d_index}, d={d}, level[d]={level[d] if 1 <= d < len(level) else 0}")
                    
                    if 1 <= d < len(level):
                        data_result[d_index] = float(level[d])
                    else:
                        data_result[d_index] = 0.0
                    d_index += 1
                else:
                    # ランレングス処理
                    nlength = 0
                    p2 = 1
                    
                    while p <= e_position and dd > level_max:
                        nlength = nlength + ((lngu ** (p2 - 1)) * (dd - level_max - 1))
                        p += byte_size
                        if p < len(data) and p + byte_size <= len(data):
                            dd = self.get_dat(data, p, byte_size)
                        else:
                            break
                        p2 += 1
                    
                    if target_d_index - 5 <= d_index <= target_d_index + nlength + 5:
                        print(f"  ランレングス: nlength={nlength}, 範囲 {d_index}~{d_index + nlength}")
                    
                    # nlength + 1個の値を設定
                    for i in range(1, nlength + 2):
                        if d_index == target_d_index:
                            print(f"★★ TARGET設定(RL): d_index={d_index}, d={d}, level[d]={level[d] if 1 <= d < len(level) else 0}")
                        
                        if d_index < len(data_result):
                            if 1 <= d < len(level):
                                data_result[d_index] = float(level[d])
                            else:
                                data_result[d_index] = 0.0
                        d_index += 1
                        if d_index > grid_num:
                            break
                
                if d_index > grid_num:
                    break
                    
                if loop_count % 1000000 == 0:
                    print(f"進捗: {loop_count}ループ, d_index={d_index}")

            print(f"\n=== ランレングス展開完了 ===")
            print(f"総ループ数: {loop_count}")
            print(f"最終d_index: {d_index}")
            
            # ターゲット位置の値確認
            if target_d_index < len(data_result):
                target_value = data_result[target_d_index]
                print(f"ターゲット位置{target_d_index}の値: {target_value}")
            
            return data_result[1:grid_num + 1]
            
        except Exception as e:
            print(f"ランレングス展開エラー: {e}")
            return [0.0] * grid_num

def main():
    print("=== ランレングス詳細デバッグ ===")
    
    debug_service = DebugGrib2Service()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    print("SWIファイル解析（詳細デバッグ版）...")
    base_info, swi_result = debug_service.unpack_swi_grib2_from_file(swi_file)
    
    print(f"\n結果: SWI配列長={len(swi_result['swi'])}")
    if len(swi_result['swi']) > 3992468:
        target_value = swi_result['swi'][3992468]
        print(f"ターゲット位置の最終値: {target_value}")
        print(f"期待値: 930.0, 差異: {abs(target_value - 930.0)}")
    
if __name__ == "__main__":
    main()
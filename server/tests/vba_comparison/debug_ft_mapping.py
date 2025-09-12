#!/usr/bin/env python3
"""
ランレングス展開の実行トレース
"""

from services.grib2_service import Grib2Service
import logging

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

def debug_runlength_execution():
    """ランレングス展開の実行をトレース"""
    print("=== ランレングス展開実行トレース ===")
    
    grib2_service = Grib2Service()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    
    try:
        print("unpack_swi_grib2_from_file実行中...")
        base_info, swi_data = grib2_service.unpack_swi_grib2_from_file(swi_file)
        
        swi_values = swi_data.get('swi', [])
        print(f"返された配列サイズ: {len(swi_values)}")
        print(f"期待サイズ: {base_info.grid_num}")
        
        if len(swi_values) == base_info.grid_num:
            print("OK: 配列サイズは正常")
            
            # 特定位置の値を確認
            test_positions = [4025749, 4023189, 4030871]
            for pos in test_positions:
                if pos < len(swi_values):
                    val = swi_values[pos]
                    print(f"位置 {pos}: 値 = {val} (÷10 = {val/10})")
                else:
                    print(f"位置 {pos}: 範囲外")
            
            # 非ゼロ値の分布を調査
            non_zero_count = sum(1 for v in swi_values if v != 0.0)
            unique_values = set(swi_values)
            
            print(f"非ゼロ値数: {non_zero_count} / {len(swi_values)} ({non_zero_count/len(swi_values)*100:.1f}%)")
            print(f"ユニーク値数: {len(unique_values)}")
            print(f"値の範囲: {min(swi_values)} - {max(swi_values)}")
            
            # 最初の100個の値をチェック
            print("\n最初の100個の値:")
            for i in range(0, min(100, len(swi_values)), 10):
                values = [swi_values[j] for j in range(i, min(i+10, len(swi_values)))]
                print(f"  {i:5d}-{i+9:5d}: {values}")
                
        else:
            print("NG: 配列サイズが異常")
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_runlength_execution()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick VBA validation test - focuses on first few meshes only
For rapid verification of VBA complete rewrite functionality
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.main_service import MainService

def parse_expected_values():
    """参照CSVから期待値を抽出（前回と同じ）"""
    # Rain期待値
    rain_expected = {}
    with open('data/shiga_rain.csv', 'r', encoding='shift_jis') as f:
        lines = f.readlines()
    
    for line in lines:
        parts = line.strip().split(',')
        if len(parts) >= 9 and parts[1] and parts[2]:
            try:
                x = int(parts[1])
                y = int(parts[2])
                # Rain CSVフォーマット: 地域名, x, y, FT3, FT6, FT9, FT12, FT15, FT18, ...
                rain_values = [float(parts[i]) for i in range(3, 9) if parts[i]]  # FT3からFT18まで
                rain_expected[(x, y)] = rain_values
            except:
                continue
    
    # SWI期待値
    swi_expected = {}
    with open('data/shiga_swi.csv', 'r', encoding='shift_jis') as f:
        lines = f.readlines()
    
    for line in lines:
        parts = line.strip().split(',')
        if len(parts) >= 7 and parts[1] and parts[2] and parts[6]:
            try:
                x = int(parts[1])
                y = int(parts[2])
                swi_value = float(parts[6])  # 6列目がSWI初期値（FT=0）
                swi_expected[(x, y)] = swi_value
            except:
                continue
    
    return rain_expected, swi_expected

def main():
    print("=== VBA完全再現 クイックテスト ===")
    
    try:
        # 期待値読み込み
        rain_expected, swi_expected = parse_expected_values()
        print(f"Rain期待値: {len(rain_expected)}件")
        print(f"SWI期待値: {len(swi_expected)}件")
        
        # MainServiceでテスト
        main_service = MainService()
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
        
        print("\\nメイン処理実行中...")
        result = main_service.main_process_from_files(swi_file, guidance_file)
        
        print(f"処理結果ステータス: {result.get('status', 'unknown')}")
        
        # 滋賀県データ抽出
        if 'prefectures' in result:
            shiga_data = result['prefectures'].get('shiga')
            if shiga_data and 'areas' in shiga_data:
                first_area = shiga_data['areas'][0]
                test_meshes = first_area['meshes'][:5]  # 最初の5メッシュのみテスト
                
                print(f"\\n=== Rain完全一致検証 ({len(test_meshes)}メッシュ) ===")
                print("No. Mesh Code    FT=3  FT=6  FT=9  FT=12 FT=15 FT=18 一致数")
                print("-" * 60)
                
                total_rain_matches = 0
                total_rain_values = 0
                
                for i, mesh in enumerate(test_meshes):
                    mesh_key = (mesh.get('x'), mesh.get('y'))
                    expected_rain = rain_expected.get(mesh_key, [])
                    
                    if expected_rain:
                        rain_timeline = mesh.get('rain_timeline', [])
                        
                        # PythonのFT=3,6,9,12,15,18 vs CSVのFT=3,6,9,12,15,18 を直接比較
                        actual_rain = [item['value'] for item in rain_timeline[:6]]
                        
                        matches = 0
                        for j, (actual, expected) in enumerate(zip(actual_rain, expected_rain)):
                            if abs(actual - expected) < 0.1:
                                matches += 1
                            total_rain_values += 1
                        total_rain_matches += matches
                        
                        actual_str = " ".join([f"{v:4.0f}" for v in actual_rain[:6]])
                        expected_str = " ".join([f"{v:4.0f}" for v in expected_rain[:6]])
                        
                        print(f"{i+1:2d}. {mesh['code']} {actual_str} | {expected_str} {matches}/6")
                
                rain_accuracy = total_rain_matches / total_rain_values * 100 if total_rain_values > 0 else 0
                print(f"\\nRain全体精度: {total_rain_matches}/{total_rain_values} ({rain_accuracy:.1f}%)")
                
                print(f"\\n=== SWI完全一致検証 ({len(test_meshes)}メッシュ) ===")
                print("No. Mesh Code    Python  期待値  差異")
                print("-" * 40)
                
                total_swi_matches = 0
                total_swi_count = 0
                
                for i, mesh in enumerate(test_meshes):
                    mesh_key = (mesh.get('x'), mesh.get('y'))
                    expected_swi = swi_expected.get(mesh_key)
                    
                    if expected_swi is not None:
                        swi_timeline = mesh.get('swi_timeline', [])
                        ft0_swi = None
                        
                        for item in swi_timeline:
                            if item['ft'] == 0:
                                ft0_swi = item['value']
                                break
                        
                        if ft0_swi is not None:
                            diff = abs(ft0_swi - expected_swi)
                            is_match = diff < 0.1
                            
                            if is_match:
                                total_swi_matches += 1
                            total_swi_count += 1
                            
                            match_symbol = "OK" if is_match else "NG"
                            print(f"{i+1:2d}. {mesh['code']} {ft0_swi:7.1f} {expected_swi:7.1f} {diff:5.1f} {match_symbol}")
                
                swi_accuracy = total_swi_matches / total_swi_count * 100 if total_swi_count > 0 else 0
                print(f"\\nSWI全体精度: {total_swi_matches}/{total_swi_count} ({swi_accuracy:.1f}%)")
                
                print(f"\\n=== 総合結果 ===")
                print(f"Rain精度: {rain_accuracy:.1f}%")
                print(f"SWI精度: {swi_accuracy:.1f}%")
                
                if rain_accuracy >= 95 and swi_accuracy >= 95:
                    print("[OK] VBAとの完全一致を実現しました！")
                elif rain_accuracy >= 90 and swi_accuracy >= 90:
                    print("[WARN] VBAとほぼ完全に一致しています（90%以上）")
                else:
                    print("[ERROR] VBAとの一致度が低く、さらなる修正が必要です")
            else:
                print("ERROR: 滋賀県データが見つかりません")
        else:
            print("ERROR: メイン処理でprefecturesが返されませんでした")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
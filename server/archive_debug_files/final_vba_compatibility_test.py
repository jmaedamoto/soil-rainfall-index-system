#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最終VBA互換性テスト - SWI修正後の完全検証
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.main_service import MainService
from services.data_service import DataService
from datetime import datetime

def parse_reference_csvs():
    """参照CSVファイルから期待値を抽出"""
    # Rain CSV
    rain_expectations = {}
    with open('data/shiga_rain.csv', 'r', encoding='iso-8859-1') as f:
        lines = f.readlines()
    
    for line in lines:
        parts = line.strip().split(',')
        if len(parts) >= 9 and parts[1] and parts[2]:  # 十分な列数があり、座標が存在
            try:
                x = int(parts[1])
                y = int(parts[2])
                # FT=3,6,9,12,15,18の雨量データ
                rain_values = []
                for i in range(3, 9):  # 3-8列目（FT=3,6,9,12,15,18）
                    if parts[i]:
                        rain_values.append(float(parts[i]))
                if rain_values:
                    rain_expectations[(x, y)] = rain_values
            except:
                continue
    
    # SWI CSV
    swi_expectations = {}
    with open('data/shiga_swi.csv', 'r', encoding='iso-8859-1') as f:
        lines = f.readlines()
    
    for line in lines:
        parts = line.strip().split(',')
        if len(parts) >= 4 and parts[1] and parts[2] and parts[3]:
            try:
                x = int(parts[1])
                y = int(parts[2])
                swi_value = float(parts[3])  # FT=0のSWI値
                swi_expectations[(x, y)] = swi_value
            except:
                continue
    
    return rain_expectations, swi_expectations

def main():
    print("=== 最終VBA互換性テスト ===")
    
    try:
        # 期待値読み込み
        rain_expectations, swi_expectations = parse_reference_csvs()
        print(f"Rain期待値: {len(rain_expectations)}件")
        print(f"SWI期待値: {len(swi_expectations)}件")
        
        # MainServiceでAPIテスト
        main_service = MainService()
        
        print("\n1. メイン処理実行中...")
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
        result = main_service.main_process_from_files(swi_file, guidance_file)
        
        if not result or result.get('status') != 'success':
            print("メイン処理が失敗しました")
            return
        
        # 滋賀県データ抽出
        shiga_data = result['prefectures'].get('shiga')
        if not shiga_data:
            print("滋賀県データが見つかりません")
            return
        
        # 最初のエリアの最初の20メッシュをテスト
        first_area = shiga_data['areas'][0]
        test_meshes = first_area['meshes'][:20]
        
        print(f"\n2. Rain互換性検証（{len(test_meshes)}メッシュ）:")
        print("No. X     Y     FT=3  FT=6  FT=9  FT=12 FT=15 FT=18 期待値一致")
        print("-" * 70)
        
        rain_total_matches = 0
        rain_total_values = 0
        
        for i, mesh in enumerate(test_meshes):
            mesh_key = (mesh['x'], mesh['y'])
            expected_rain = rain_expectations.get(mesh_key)
            
            if expected_rain:
                # Python計算結果
                rain_timeline = mesh.get('rain_timeline', [])
                actual_rain = [item['value'] for item in rain_timeline[:6]]  # FT=3-18
                
                # 一致確認
                matches = 0
                if len(actual_rain) == len(expected_rain):
                    for j, (actual, expected) in enumerate(zip(actual_rain, expected_rain)):
                        if abs(actual - expected) < 0.1:
                            matches += 1
                        rain_total_values += 1
                    rain_total_matches += matches
                
                match_rate = f"{matches}/{len(expected_rain)}" if expected_rain else "N/A"
                actual_str = ",".join([f"{v:4.0f}" for v in actual_rain[:6]])
                expected_str = ",".join([f"{v:4.0f}" for v in expected_rain[:6]])
                
                print(f"{i+1:2d}. {mesh['x']:4d} {mesh['y']:4d} {actual_str} | {expected_str} {match_rate}")
            else:
                print(f"{i+1:2d}. {mesh['x']:4d} {mesh['y']:4d} (期待値なし)")
        
        rain_accuracy = rain_total_matches / rain_total_values * 100 if rain_total_values > 0 else 0
        print(f"Rain全体精度: {rain_total_matches}/{rain_total_values} ({rain_accuracy:.1f}%)")
        
        print(f"\n3. SWI互換性検証（{len(test_meshes)}メッシュ）:")
        print("No. X     Y     Python  期待値  一致")
        print("-" * 35)
        
        swi_matches = 0
        swi_total = 0
        
        for i, mesh in enumerate(test_meshes):
            mesh_key = (mesh['x'], mesh['y'])
            expected_swi = swi_expectations.get(mesh_key)
            
            # Python計算結果（FT=0）
            swi_timeline = mesh.get('swi_timeline', [])
            ft0_swi = None
            for item in swi_timeline:
                if item['ft'] == 0:
                    ft0_swi = item['value']
                    break
            
            if expected_swi and ft0_swi is not None:
                match = abs(ft0_swi - expected_swi) < 0.1
                if match:
                    swi_matches += 1
                swi_total += 1
                
                match_symbol = "✓" if match else "✗"
                print(f"{i+1:2d}. {mesh['x']:4d} {mesh['y']:4d} {ft0_swi:7.1f} {expected_swi:7.1f} {match_symbol}")
            else:
                expected_str = f"{expected_swi:.1f}" if expected_swi else "N/A"
                ft0_str = f"{ft0_swi:.1f}" if ft0_swi is not None else "N/A"
                print(f"{i+1:2d}. {mesh['x']:4d} {mesh['y']:4d} {ft0_str:>7} {expected_str:>7} -")
        
        swi_accuracy = swi_matches / swi_total * 100 if swi_total > 0 else 0
        print(f"SWI全体精度: {swi_matches}/{swi_total} ({swi_accuracy:.1f}%)")
        
        print(f"\n4. 総合結果:")
        print(f"Rain精度: {rain_accuracy:.1f}%")
        print(f"SWI精度: {swi_accuracy:.1f}%")
        
        if rain_accuracy > 90 and swi_accuracy > 90:
            print("✅ VBAとの完全一致を実現しました！")
        elif rain_accuracy > 80 and swi_accuracy > 80:
            print("⚠️ VBAとほぼ一致していますが、さらなる改善が可能です")
        else:
            print("❌ VBAとの一致度が低く、追加修正が必要です")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
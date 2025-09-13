#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBA完全再現版の最終検証テスト
完全一致の確認
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.main_service import MainService
from services.data_service import DataService

def parse_expected_values():
    """参照CSVから期待値を抽出"""
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
        if len(parts) >= 4 and parts[1] and parts[2] and parts[3]:
            try:
                x = int(parts[1])
                y = int(parts[2])
                swi_value = float(parts[3])
                swi_expected[(x, y)] = swi_value
            except:
                continue
    
    return rain_expected, swi_expected

def main():
    print("=== VBA完全再現版 最終検証テスト ===")
    
    try:
        # 期待値読み込み
        rain_expected, swi_expected = parse_expected_values()
        print(f"Rain期待値: {len(rain_expected)}件")
        print(f"SWI期待値: {len(swi_expected)}件")
        
        # MainServiceでテスト
        main_service = MainService()
        swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
        guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"
        
        print("\nメイン処理実行中...")
        result = main_service.main_process_from_files(swi_file, guidance_file)
        
        if not result or result.get('status') != 'success':
            print("メイン処理が失敗しました")
            return
        
        # 滋賀県データ抽出
        shiga_data = result['prefectures'].get('shiga')
        if not shiga_data:
            print("滋賀県データが見つかりません")
            return
        
        # 最初のエリアのメッシュをテスト
        first_area = shiga_data['areas'][0]
        test_meshes = first_area['meshes'][:10]  # 最初の10メッシュ
        
        print(f"\n=== Rain完全一致検証 ({len(test_meshes)}メッシュ) ===")
        print("No. Mesh Code    FT=3  FT=6  FT=9  FT=12 FT=15 FT=18 一致数")
        print("-" * 60)
        
        total_rain_matches = 0
        total_rain_values = 0
        
        for i, mesh in enumerate(test_meshes):
            mesh_key = (mesh['x'], mesh['y'])
            expected_rain = rain_expected.get(mesh_key, [])
            
            if expected_rain:
                rain_timeline = mesh.get('rain_timeline', [])
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
        print(f"\nRain全体精度: {total_rain_matches}/{total_rain_values} ({rain_accuracy:.1f}%)")
        
        print(f"\n=== SWI完全一致検証 ({len(test_meshes)}メッシュ) ===")
        print("No. Mesh Code    Python  期待値  差異")
        print("-" * 40)
        
        total_swi_matches = 0
        total_swi_count = 0
        
        for i, mesh in enumerate(test_meshes):
            mesh_key = (mesh['x'], mesh['y'])
            expected_swi = swi_expected.get(mesh_key)
            
            if expected_swi:
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
                    
                    match_symbol = "✓" if is_match else "✗"
                    print(f"{i+1:2d}. {mesh['code']} {ft0_swi:7.1f} {expected_swi:7.1f} {diff:5.1f} {match_symbol}")
        
        swi_accuracy = total_swi_matches / total_swi_count * 100 if total_swi_count > 0 else 0
        print(f"\nSWI全体精度: {total_swi_matches}/{total_swi_count} ({swi_accuracy:.1f}%)")
        
        print(f"\n=== 総合結果 ===")
        print(f"Rain精度: {rain_accuracy:.1f}%")
        print(f"SWI精度: {swi_accuracy:.1f}%")
        
        if rain_accuracy >= 95 and swi_accuracy >= 95:
            print("✅ VBAとの完全一致を実現しました！")
        elif rain_accuracy >= 90 and swi_accuracy >= 90:
            print("⚠️ VBAとほぼ完全に一致しています（90%以上）")
        elif rain_accuracy >= 80 and swi_accuracy >= 80:
            print("⚠️ VBAと高い一致度です（80%以上）")
        else:
            print("❌ VBAとの一致度が低く、さらなる修正が必要です")
        
        # 詳細分析
        if swi_accuracy < 95:
            print(f"\nSWI改善のための詳細分析:")
            print("最初のメッシュでの詳細確認...")
            
            first_mesh = test_meshes[0]
            mesh_key = (first_mesh['x'], first_mesh['y'])
            expected_swi = swi_expected.get(mesh_key)
            
            if expected_swi:
                swi_timeline = first_mesh.get('swi_timeline', [])
                if swi_timeline:
                    ft0_swi = swi_timeline[0]['value']
                    print(f"メッシュ{first_mesh['code']}: Python={ft0_swi}, 期待値={expected_swi}, 差異={abs(ft0_swi - expected_swi)}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
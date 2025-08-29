#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time


def final_verification():
    print("最終検証を実行中...")
    
    try:
        # フルテストエンドポイントを使用
        start_time = time.time()
        response = requests.get('http://localhost:5000/api/test-full-soil-rainfall-index', timeout=180)
        end_time = time.time()
        
        if response.status_code != 200:
            print(f"APIエラー: {response.status_code}")
            print(f"レスポンス: {response.text[:500]}")
            return
            
        data = response.json()
        print(f"データ取得成功: {len(data.get('prefectures', {}))}府県")
        print(f"処理時間: {end_time - start_time:.1f}秒")
        
        # 境界値の全数調査
        total_meshes = 0
        boundary_stats = {
            'dosyakei_200': 0,
            'dosyakei_9999': 0,
            'dosyakei_other': 0,
            'advisary_9999': 0,
            'warning_9999': 0
        }
        
        # FT0でのリスクレベル
        risk_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        
        for pref_code, prefecture in data['prefectures'].items():
            for area in prefecture['areas']:
                for mesh in area['meshes']:
                    total_meshes += 1
                    
                    # 境界値統計
                    if mesh['dosyakei_bound'] == 200:
                        boundary_stats['dosyakei_200'] += 1
                    elif mesh['dosyakei_bound'] == 9999:
                        boundary_stats['dosyakei_9999'] += 1
                    else:
                        boundary_stats['dosyakei_other'] += 1
                    
                    if mesh['advisary_bound'] == 9999:
                        boundary_stats['advisary_9999'] += 1
                    if mesh['warning_bound'] == 9999:
                        boundary_stats['warning_9999'] += 1
                    
                    # FT0のリスクレベル
                    ft0_data = next((p for p in mesh['swi_timeline'] if p['ft'] == 0), None)
                    if ft0_data:
                        swi_value = ft0_data['value']
                        
                        risk_level = 0
                        if swi_value >= mesh['dosyakei_bound']:
                            risk_level = 3
                        elif swi_value >= mesh['warning_bound']:
                            risk_level = 2
                        elif swi_value >= mesh['advisary_bound']:
                            risk_level = 1
                        
                        risk_counts[risk_level] += 1
        
        print(f"\n=== 最終検証結果 ===")
        print(f"総メッシュ数: {total_meshes:,}個")
        
        print(f"\n土砂災害境界値の分布:")
        print(f"  200 (修正前): {boundary_stats['dosyakei_200']:,}個 ({boundary_stats['dosyakei_200']/total_meshes*100:.2f}%)")
        print(f"  9999 (修正後): {boundary_stats['dosyakei_9999']:,}個 ({boundary_stats['dosyakei_9999']/total_meshes*100:.2f}%)")
        print(f"  その他: {boundary_stats['dosyakei_other']:,}個 ({boundary_stats['dosyakei_other']/total_meshes*100:.2f}%)")
        
        print(f"\nその他の境界値:")
        print(f"  注意報基準9999: {boundary_stats['advisary_9999']:,}個")
        print(f"  警報基準9999: {boundary_stats['warning_9999']:,}個")
        
        print(f"\nFT0のリスクレベル分布:")
        for level in range(4):
            count = risk_counts[level]
            percentage = count / total_meshes * 100 if total_meshes > 0 else 0
            level_names = ['正常', '注意', '警報', '土砂災害']
            print(f"  レベル{level}({level_names[level]}): {count:,}個 ({percentage:.2f}%)")
        
        # 修正成功判定
        print(f"\n=== 修正効果の評価 ===")
        
        if boundary_stats['dosyakei_200'] == 0:
            print("✓ SUCCESS: すべての土砂災害基準200が9999に修正されました")
        else:
            print(f"⚠ PARTIAL: {boundary_stats['dosyakei_200']:,}個の200が残存しています")
        
        if boundary_stats['dosyakei_9999'] > 0:
            print(f"✓ SUCCESS: {boundary_stats['dosyakei_9999']:,}個で9999基準が適用されています")
        
        level_3_ratio = risk_counts[3] / total_meshes * 100 if total_meshes > 0 else 0
        if level_3_ratio < 10:  # 10%未満なら改善
            print(f"✓ SUCCESS: レベル3の割合が{level_3_ratio:.2f}%に改善されました")
        else:
            print(f"⚠ WARNING: レベル3の割合が{level_3_ratio:.2f}%でまだ高いです")
        
        # 時系列変化の確認
        available_fts = set()
        for pref_code, prefecture in data['prefectures'].items():
            for area in prefecture['areas']:
                for mesh in area['meshes'][:10]:  # 最初の10メッシュのみ
                    for point in mesh['swi_timeline']:
                        available_fts.add(point['ft'])
                    break
                break
            break
        
        print(f"\n利用可能時刻: {sorted(available_fts)[:10]}")  # 最初の10時刻
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    final_verification()
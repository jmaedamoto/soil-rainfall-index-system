#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json


def analyze_risk_levels():
    print("修正後のリスクレベル分析を開始...")
    
    try:
        response = requests.get('http://localhost:5000/api/test-full-soil-rainfall-index', timeout=120)
        if response.status_code != 200:
            print(f"APIエラー: {response.status_code}")
            return
            
        data = response.json()
        print(f"データ取得成功: {len(data.get('prefectures', {}))}府県")
        
        # 全メッシュ情報を収集
        all_meshes = []
        for pref_code, prefecture in data['prefectures'].items():
            for area in prefecture['areas']:
                for mesh in area['meshes']:
                    all_meshes.append({
                        'code': mesh['code'],
                        'advisary_bound': mesh['advisary_bound'],
                        'warning_bound': mesh['warning_bound'],
                        'dosyakei_bound': mesh['dosyakei_bound'],
                        'swi_timeline': mesh['swi_timeline']
                    })
        
        print(f"総メッシュ数: {len(all_meshes):,}個")
        
        # FT0でのリスクレベル分析
        risk_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        boundary_stats = {
            'advisary_9999': 0,
            'warning_9999': 0,
            'dosyakei_200': 0,
            'dosyakei_9999': 0
        }
        
        swi_values = []
        sample_details = []
        
        for mesh in all_meshes:
            # FT0のSWI値を取得
            ft0_data = next((p for p in mesh['swi_timeline'] if p['ft'] == 0), None)
            if not ft0_data:
                continue
                
            swi_value = ft0_data['value']
            swi_values.append(swi_value)
            
            # 境界値統計
            if mesh['advisary_bound'] == 9999:
                boundary_stats['advisary_9999'] += 1
            if mesh['warning_bound'] == 9999:
                boundary_stats['warning_9999'] += 1
            if mesh['dosyakei_bound'] == 200:
                boundary_stats['dosyakei_200'] += 1
            if mesh['dosyakei_bound'] == 9999:
                boundary_stats['dosyakei_9999'] += 1
            
            # リスクレベル判定
            risk_level = 0
            if swi_value >= mesh['dosyakei_bound']:
                risk_level = 3
            elif swi_value >= mesh['warning_bound']:
                risk_level = 2
            elif swi_value >= mesh['advisary_bound']:
                risk_level = 1
            
            risk_counts[risk_level] += 1
            
            # サンプル詳細を収集
            if len(sample_details) < 10:
                sample_details.append({
                    'code': mesh['code'],
                    'swi': swi_value,
                    'advisary': mesh['advisary_bound'],
                    'warning': mesh['warning_bound'],
                    'dosyakei': mesh['dosyakei_bound'],
                    'risk_level': risk_level
                })
        
        total_meshes = sum(risk_counts.values())
        
        print(f"\nFT0時間後のリスクレベル分析:")
        print(f"総メッシュ数: {total_meshes:,}個")
        print(f"レベル0（正常）: {risk_counts[0]:,}個 ({risk_counts[0]/total_meshes*100:.1f}%)")
        print(f"レベル1（注意）: {risk_counts[1]:,}個 ({risk_counts[1]/total_meshes*100:.1f}%)")
        print(f"レベル2（警報）: {risk_counts[2]:,}個 ({risk_counts[2]/total_meshes*100:.1f}%)")
        print(f"レベル3（土砂災害）: {risk_counts[3]:,}個 ({risk_counts[3]/total_meshes*100:.1f}%)")
        
        if swi_values:
            print(f"SWI値範囲: {min(swi_values):.1f} 〜 {max(swi_values):.1f}")
            print(f"SWI平均値: {sum(swi_values)/len(swi_values):.1f}")
        
        print(f"\n境界値異常チェック:")
        print(f"注意報基準9999の数: {boundary_stats['advisary_9999']}")
        print(f"警報基準9999の数: {boundary_stats['warning_9999']}")
        print(f"土砂災害基準200の数: {boundary_stats['dosyakei_200']}")
        print(f"土砂災害基準9999の数: {boundary_stats['dosyakei_9999']}")
        
        print(f"\nサンプル詳細（最初の5個）:")
        for detail in sample_details[:5]:
            print(f"  {detail['code']}: SWI={detail['swi']:.1f}, "
                  f"基準(注意:{detail['advisary']}/警報:{detail['warning']}/土砂:{detail['dosyakei']}) "
                  f"-> レベル{detail['risk_level']}")
        
        # 修正効果の評価
        print(f"\n修正効果の評価:")
        if boundary_stats['dosyakei_200'] > 0:
            print(f"WARNING: 土砂災害基準に200が残存: {boundary_stats['dosyakei_200']}個")
        else:
            print("SUCCESS: 土砂災害基準200は除去されました")
            
        if boundary_stats['dosyakei_9999'] > 0:
            print(f"SUCCESS: 土砂災害基準9999が適用: {boundary_stats['dosyakei_9999']}個")
        
        level_3_ratio = risk_counts.get(3, 0) / max(total_meshes, 1) * 100
        if level_3_ratio > 50:
            print(f"WARNING: レベル3が{level_3_ratio:.1f}%で依然として高い割合です")
        else:
            print(f"SUCCESS: レベル3の割合({level_3_ratio:.1f}%)が改善されました")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    analyze_risk_levels()
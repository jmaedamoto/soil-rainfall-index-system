#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBA期待値CSVファイルとサーバー処理結果の完全一致検証
"""
import pandas as pd
import json
import requests
from typing import Dict, List, Any, Tuple
import csv
import os

def read_vba_rain_csv(filename: str) -> Dict[str, List[float]]:
    """
    VBA RainCSVファイルを読み取り、メッシュコード別のrain_timelineデータに変換

    CSVフォーマット: area_name, x, y, rain_ft0, rain_ft3, rain_ft6, ...
    """
    result = {}

    try:
        with open(filename, 'r', encoding='shift_jis') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 6:  # 最低限のデータが必要
                    continue

                area_name = row[0]
                x = int(row[1])
                y = int(row[2])

                # メッシュコードを生成 (VBAロジックと同一方式)
                meshcode = str(x * 10000 + y)

                # rain_timelineデータを抽出 (ft=3から開始、3時間間隔)
                rain_timeline = []
                for i, val_str in enumerate(row[3:]):  # ft=0から開始するデータ
                    if val_str.strip() == '':
                        continue
                    try:
                        value = float(val_str)
                        rain_timeline.append({
                            "ft": i * 3,  # 3時間間隔
                            "value": value
                        })
                    except ValueError:
                        continue

                result[meshcode] = rain_timeline

    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return {}

    return result

def read_vba_swi_csv(filename: str) -> Dict[str, List[float]]:
    """
    VBA SWI CSVファイルを読み取り、メッシュコード別のswi_timelineデータに変換

    CSVフォーマット: area_name, x, y, advisary, warning, dosyakei, initial_swi, swi_ft0, swi_ft3, ...
    """
    result = {}

    try:
        with open(filename, 'r', encoding='shift_jis') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 8:  # 最低限のデータが必要
                    continue

                # 空行をスキップ
                if row[0].strip() == '' and row[1].strip() == '':
                    continue

                area_name = row[0]
                try:
                    x = int(row[1])
                    y = int(row[2])
                except ValueError:
                    continue

                # メッシュコードを生成
                meshcode = str(x * 10000 + y)

                # swi_timelineデータを抽出 (initial_swi + ft=0から開始、3時間間隔)
                swi_timeline = []
                for i, val_str in enumerate(row[6:]):  # initial_swiから開始
                    if val_str.strip() == '':
                        continue
                    try:
                        value = float(val_str)
                        swi_timeline.append({
                            "ft": i * 3,  # 3時間間隔
                            "value": value
                        })
                    except ValueError:
                        continue

                result[meshcode] = swi_timeline

    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return {}

    return result

def get_server_results() -> Dict[str, Any]:
    """
    サーバーから処理結果を取得
    """
    try:
        url = "http://localhost:5000/api/test-full-soil-rainfall-index"
        response = requests.get(url, timeout=120)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Server error: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error getting server results: {e}")
        return {}

def extract_server_data(server_results: Dict[str, Any]) -> Tuple[Dict[str, List], Dict[str, List]]:
    """
    サーバー結果からrain_timelineとswi_timelineを抽出
    """
    server_rain = {}
    server_swi = {}

    if 'prefectures' not in server_results:
        return server_rain, server_swi

    for pref_code, pref_data in server_results['prefectures'].items():
        if 'areas' not in pref_data:
            continue

        for area in pref_data['areas']:
            if 'meshes' not in area:
                continue

            for mesh in area['meshes']:
                meshcode = mesh.get('code', '')

                # rain_timelineを抽出
                if 'rain_timeline' in mesh:
                    server_rain[meshcode] = mesh['rain_timeline']

                # swi_timelineを抽出
                if 'swi_timeline' in mesh:
                    server_swi[meshcode] = mesh['swi_timeline']

    return server_rain, server_swi

def compare_timelines(vba_data: Dict[str, List], server_data: Dict[str, List],
                     data_type: str, tolerance: float = 0.01) -> Dict[str, Any]:
    """
    VBAとサーバーのタイムラインデータを比較
    """
    comparison_result = {
        'total_meshes_vba': len(vba_data),
        'total_meshes_server': len(server_data),
        'matching_meshes': 0,
        'mismatched_meshes': 0,
        'missing_in_server': [],
        'missing_in_vba': [],
        'value_mismatches': [],
        'perfect_matches': 0
    }

    # VBAにあってサーバーにないメッシュ
    for meshcode in vba_data:
        if meshcode not in server_data:
            comparison_result['missing_in_server'].append(meshcode)

    # サーバーにあってVBAにないメッシュ
    for meshcode in server_data:
        if meshcode not in vba_data:
            comparison_result['missing_in_vba'].append(meshcode)

    # 共通メッシュの値比較
    common_meshes = set(vba_data.keys()) & set(server_data.keys())

    for meshcode in common_meshes:
        vba_timeline = vba_data[meshcode]
        server_timeline = server_data[meshcode]

        # タイムライン長の比較
        if len(vba_timeline) != len(server_timeline):
            comparison_result['value_mismatches'].append({
                'meshcode': meshcode,
                'issue': 'timeline_length_mismatch',
                'vba_length': len(vba_timeline),
                'server_length': len(server_timeline)
            })
            comparison_result['mismatched_meshes'] += 1
            continue

        # 各時間点での値比較
        perfect_match = True
        for i in range(len(vba_timeline)):
            vba_point = vba_timeline[i]
            server_point = server_timeline[i]

            # FT時刻の比較
            if vba_point['ft'] != server_point['ft']:
                comparison_result['value_mismatches'].append({
                    'meshcode': meshcode,
                    'issue': 'ft_mismatch',
                    'index': i,
                    'vba_ft': vba_point['ft'],
                    'server_ft': server_point['ft']
                })
                perfect_match = False
                break

            # 値の比較（許容誤差内）
            vba_val = float(vba_point['value'])
            server_val = float(server_point['value'])

            if abs(vba_val - server_val) > tolerance:
                comparison_result['value_mismatches'].append({
                    'meshcode': meshcode,
                    'issue': 'value_mismatch',
                    'ft': vba_point['ft'],
                    'vba_value': vba_val,
                    'server_value': server_val,
                    'difference': abs(vba_val - server_val)
                })
                perfect_match = False

        if perfect_match:
            comparison_result['perfect_matches'] += 1
        else:
            comparison_result['mismatched_meshes'] += 1

    comparison_result['matching_meshes'] = len(common_meshes)

    return comparison_result

def main():
    """
    メイン検証処理
    """
    print("=== VBA結果とサーバー結果の完全一致検証 ===")
    print()

    # 1. サーバー結果取得
    print("1. サーバー結果を取得中...")
    server_results = get_server_results()
    if not server_results:
        print("ERROR: サーバー結果の取得に失敗しました")
        return

    server_rain, server_swi = extract_server_data(server_results)
    print(f"   サーバー rain_timeline: {len(server_rain)} meshes")
    print(f"   サーバー swi_timeline: {len(server_swi)} meshes")
    print()

    # 2. VBA期待値ファイル読み込み
    print("2. VBA期待値CSVファイルを読み込み中...")
    prefectures = ['shiga', 'kyoto', 'osaka', 'hyogo', 'nara', 'wakayama']

    vba_rain_all = {}
    vba_swi_all = {}

    for pref in prefectures:
        rain_file = f'data/{pref}_rain.csv'
        swi_file = f'data/{pref}_swi.csv'

        if os.path.exists(rain_file):
            vba_rain_pref = read_vba_rain_csv(rain_file)
            vba_rain_all.update(vba_rain_pref)
            print(f"   {pref}_rain.csv: {len(vba_rain_pref)} meshes")

        if os.path.exists(swi_file):
            vba_swi_pref = read_vba_swi_csv(swi_file)
            vba_swi_all.update(vba_swi_pref)
            print(f"   {pref}_swi.csv: {len(vba_swi_pref)} meshes")

    print(f"   VBA rain_timeline 総計: {len(vba_rain_all)} meshes")
    print(f"   VBA swi_timeline 総計: {len(vba_swi_all)} meshes")
    print()

    # 3. Rain Timeline比較
    print("3. Rain Timeline比較中...")
    rain_comparison = compare_timelines(vba_rain_all, server_rain, "rain", tolerance=0.01)

    print(f"   VBAメッシュ数: {rain_comparison['total_meshes_vba']}")
    print(f"   サーバーメッシュ数: {rain_comparison['total_meshes_server']}")
    print(f"   完全一致メッシュ: {rain_comparison['perfect_matches']}")
    print(f"   不一致メッシュ: {rain_comparison['mismatched_meshes']}")
    print(f"   サーバー未実装: {len(rain_comparison['missing_in_server'])}")
    print(f"   VBA未実装: {len(rain_comparison['missing_in_vba'])}")

    if rain_comparison['value_mismatches']:
        print(f"   値の相違例 (最初の5件):")
        for i, mismatch in enumerate(rain_comparison['value_mismatches'][:5]):
            print(f"     {i+1}. {mismatch}")
    print()

    # 4. SWI Timeline比較
    print("4. SWI Timeline比較中...")
    swi_comparison = compare_timelines(vba_swi_all, server_swi, "swi", tolerance=0.01)

    print(f"   VBAメッシュ数: {swi_comparison['total_meshes_vba']}")
    print(f"   サーバーメッシュ数: {swi_comparison['total_meshes_server']}")
    print(f"   完全一致メッシュ: {swi_comparison['perfect_matches']}")
    print(f"   不一致メッシュ: {swi_comparison['mismatched_meshes']}")
    print(f"   サーバー未実装: {len(swi_comparison['missing_in_server'])}")
    print(f"   VBA未実装: {len(swi_comparison['missing_in_vba'])}")

    if swi_comparison['value_mismatches']:
        print(f"   値の相違例 (最初の5件):")
        for i, mismatch in enumerate(swi_comparison['value_mismatches'][:5]):
            print(f"     {i+1}. {mismatch}")
    print()

    # 5. 総合結果
    print("5. 総合結果")
    rain_match_rate = rain_comparison['perfect_matches'] / max(rain_comparison['matching_meshes'], 1) * 100
    swi_match_rate = swi_comparison['perfect_matches'] / max(swi_comparison['matching_meshes'], 1) * 100

    print(f"   Rain Timeline一致率: {rain_match_rate:.2f}%")
    print(f"   SWI Timeline一致率: {swi_match_rate:.2f}%")

    if rain_match_rate == 100.0 and swi_match_rate == 100.0:
        print("   OK 完全一致: すべてのメッシュでVBAとサーバー結果が一致しました")
    else:
        print("   NG 不一致あり: 詳細な分析と修正が必要です")

    # 6. 詳細結果をファイルに保存
    detailed_results = {
        'rain_comparison': rain_comparison,
        'swi_comparison': swi_comparison,
        'summary': {
            'rain_match_rate': rain_match_rate,
            'swi_match_rate': swi_match_rate,
            'perfect_match': rain_match_rate == 100.0 and swi_match_rate == 100.0
        }
    }

    with open('vba_validation_results.json', 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, ensure_ascii=False, indent=2)

    print("   詳細結果を vba_validation_results.json に保存しました")

if __name__ == "__main__":
    main()
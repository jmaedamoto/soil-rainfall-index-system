#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2023年6月2日のGRIB2ファイルでサーバー処理を実行し、VBA CSV出力と完全一致検証
"""
import requests
import csv
import json

def test_server_with_vba_date():
    """
    2023年6月2日00時のデータでサーバー処理を実行
    """
    try:
        # VBA CSVデータの元となった正確な初期時刻
        initial_time = "2023-06-02T00:00:00Z"

        print(f"=== サーバー処理実行: {initial_time} ===")

        url = "http://localhost:5000/api/production-soil-rainfall-index"
        params = {"initial": initial_time}

        response = requests.get(url, params=params, timeout=600)

        if response.status_code != 200:
            print(f"サーバーエラー: {response.status_code}")
            print(f"Response: {response.text}")
            return None

        result = response.json()
        print(f"サーバー処理成功")
        print(f"使用URL: {result.get('used_urls', 'N/A')}")

        return result

    except Exception as e:
        print(f"エラー: {e}")
        return None

def load_vba_csv_data():
    """
    VBA CSV出力データを読み込み（正解データ）
    """
    vba_data = {}
    prefectures = ['shiga', 'kyoto', 'osaka', 'hyogo', 'nara', 'wakayama']

    for pref in prefectures:
        vba_data[pref] = {'rain': {}, 'swi': {}}

        # Rain CSV読み込み
        try:
            with open(f'data/{pref}_rain.csv', 'r', encoding='shift_jis') as f:
                reader = csv.reader(f)
                rows = list(reader)

                # 1行目は無意味なデータなので2行目以降を処理
                for row in rows[1:]:
                    if len(row) >= 6:  # Area, X, Y, + 雨量データ
                        try:
                            area_name = row[0].strip()
                            x = int(row[1])
                            y = int(row[2])

                            # FT=0から始まる雨量時系列
                            rain_timeline = []
                            for i, val_str in enumerate(row[3:]):
                                if val_str.strip() == '':
                                    break
                                try:
                                    value = float(val_str)
                                    rain_timeline.append({"ft": i * 3, "value": value})
                                except ValueError:
                                    break

                            key = f"{area_name}_{x}_{y}"
                            vba_data[pref]['rain'][key] = {
                                'area_name': area_name,
                                'x': x,
                                'y': y,
                                'timeline': rain_timeline
                            }

                        except ValueError:
                            continue

        except Exception as e:
            print(f"Error reading {pref}_rain.csv: {e}")

        # SWI CSV読み込み
        try:
            with open(f'data/{pref}_swi.csv', 'r', encoding='shift_jis') as f:
                reader = csv.reader(f)
                rows = list(reader)

                # 1行目は無意味なデータなので2行目以降を処理
                for row in rows[1:]:
                    if len(row) >= 10:  # Area, X, Y, 注意報, 警報, 土砂災害, + SWIデータ
                        try:
                            area_name = row[0].strip()
                            x = int(row[1])
                            y = int(row[2])

                            # 境界値
                            advisary_bound = int(row[3]) if row[3].strip() != '' else 0
                            warning_bound = int(row[4]) if row[4].strip() != '' else 0
                            dosyakei_bound = int(row[5]) if row[5].strip() != '' else 0

                            # FT=0から始まる土壌雨量指数時系列
                            swi_timeline = []
                            for i, val_str in enumerate(row[6:]):
                                if val_str.strip() == '':
                                    break
                                try:
                                    value = float(val_str)
                                    swi_timeline.append({"ft": i * 3, "value": value})
                                except ValueError:
                                    break

                            key = f"{area_name}_{x}_{y}"
                            vba_data[pref]['swi'][key] = {
                                'area_name': area_name,
                                'x': x,
                                'y': y,
                                'advisary_bound': advisary_bound,
                                'warning_bound': warning_bound,
                                'dosyakei_bound': dosyakei_bound,
                                'timeline': swi_timeline
                            }

                        except ValueError:
                            continue

        except Exception as e:
            print(f"Error reading {pref}_swi.csv: {e}")

    return vba_data

def compare_server_with_vba(server_result, vba_data):
    """
    サーバー結果とVBA CSV結果を詳細比較
    """
    print("\n=== サーバー結果 vs VBA CSV 詳細比較 ===")

    if not server_result or 'prefectures' not in server_result:
        print("サーバー結果が無効です")
        return

    comparison_results = {}

    for pref_code, pref_data in server_result['prefectures'].items():
        if pref_code not in vba_data:
            continue

        comparison_results[pref_code] = {
            'rain_matches': 0,
            'rain_mismatches': 0,
            'swi_matches': 0,
            'swi_mismatches': 0,
            'boundary_matches': 0,
            'boundary_mismatches': 0,
            'rain_mismatch_details': [],
            'swi_mismatch_details': [],
            'boundary_mismatch_details': []
        }

        print(f"\n{pref_code}県 比較:")

        for area in pref_data.get('areas', []):
            area_name = area.get('name', '')

            for mesh in area.get('meshes', []):
                # サーバーデータ
                server_rain = mesh.get('rain_timeline', [])
                server_swi = mesh.get('swi_timeline', [])
                server_advisary = mesh.get('advisary_bound', 0)
                server_warning = mesh.get('warning_bound', 0)
                server_dosyakei = mesh.get('dosyakei_bound', 0)

                # 対応するVBAデータを探索
                # 座標情報がないため、area_name と境界値で照合
                vba_rain_match = None
                vba_swi_match = None

                for vba_key, vba_rain_data in vba_data[pref_code]['rain'].items():
                    if vba_rain_data['area_name'] == area_name:
                        # 境界値でも照合確認
                        corresponding_swi_key = vba_key
                        if corresponding_swi_key in vba_data[pref_code]['swi']:
                            vba_swi_data = vba_data[pref_code]['swi'][corresponding_swi_key]

                            if (vba_swi_data['advisary_bound'] == server_advisary and
                                vba_swi_data['warning_bound'] == server_warning and
                                vba_swi_data['dosyakei_bound'] == server_dosyakei):
                                vba_rain_match = vba_rain_data
                                vba_swi_match = vba_swi_data
                                break

                if vba_rain_match and vba_swi_match:
                    # 境界値比較
                    boundary_match = (
                        server_advisary == vba_swi_match['advisary_bound'] and
                        server_warning == vba_swi_match['warning_bound'] and
                        server_dosyakei == vba_swi_match['dosyakei_bound']
                    )

                    if boundary_match:
                        comparison_results[pref_code]['boundary_matches'] += 1
                    else:
                        comparison_results[pref_code]['boundary_mismatches'] += 1
                        comparison_results[pref_code]['boundary_mismatch_details'].append({
                            'area': area_name,
                            'server': f"{server_advisary}/{server_warning}/{server_dosyakei}",
                            'vba': f"{vba_swi_match['advisary_bound']}/{vba_swi_match['warning_bound']}/{vba_swi_match['dosyakei_bound']}"
                        })

                    # Rain timeline比較
                    vba_rain_timeline = vba_rain_match['timeline']
                    rain_match = compare_timelines(server_rain, vba_rain_timeline, "rain")

                    if rain_match:
                        comparison_results[pref_code]['rain_matches'] += 1
                    else:
                        comparison_results[pref_code]['rain_mismatches'] += 1
                        if len(comparison_results[pref_code]['rain_mismatch_details']) < 3:  # 最初の3つだけ保存
                            comparison_results[pref_code]['rain_mismatch_details'].append({
                                'area': area_name,
                                'vba_coords': f"x={vba_rain_match['x']}, y={vba_rain_match['y']}",
                                'server_sample': server_rain[:3] if server_rain else [],
                                'vba_sample': vba_rain_timeline[:3] if vba_rain_timeline else []
                            })

                    # SWI timeline比較
                    vba_swi_timeline = vba_swi_match['timeline']
                    swi_match = compare_timelines(server_swi, vba_swi_timeline, "swi")

                    if swi_match:
                        comparison_results[pref_code]['swi_matches'] += 1
                    else:
                        comparison_results[pref_code]['swi_mismatches'] += 1
                        if len(comparison_results[pref_code]['swi_mismatch_details']) < 3:  # 最初の3つだけ保存
                            comparison_results[pref_code]['swi_mismatch_details'].append({
                                'area': area_name,
                                'vba_coords': f"x={vba_swi_match['x']}, y={vba_swi_match['y']}",
                                'server_sample': server_swi[:3] if server_swi else [],
                                'vba_sample': vba_swi_timeline[:3] if vba_swi_timeline else []
                            })

        # 都道府県別結果表示
        total_rain = comparison_results[pref_code]['rain_matches'] + comparison_results[pref_code]['rain_mismatches']
        total_swi = comparison_results[pref_code]['swi_matches'] + comparison_results[pref_code]['swi_mismatches']
        total_boundary = comparison_results[pref_code]['boundary_matches'] + comparison_results[pref_code]['boundary_mismatches']

        print(f"  境界値一致: {comparison_results[pref_code]['boundary_matches']}/{total_boundary}")
        print(f"  Rain一致: {comparison_results[pref_code]['rain_matches']}/{total_rain}")
        print(f"  SWI一致: {comparison_results[pref_code]['swi_matches']}/{total_swi}")

        # 不一致の詳細表示
        if comparison_results[pref_code]['rain_mismatch_details']:
            print(f"  Rain不一致例:")
            for detail in comparison_results[pref_code]['rain_mismatch_details'][:2]:
                print(f"    {detail['area']} ({detail['vba_coords']})")
                print(f"      Server: {detail['server_sample']}")
                print(f"      VBA: {detail['vba_sample']}")

        if comparison_results[pref_code]['swi_mismatch_details']:
            print(f"  SWI不一致例:")
            for detail in comparison_results[pref_code]['swi_mismatch_details'][:2]:
                print(f"    {detail['area']} ({detail['vba_coords']})")
                print(f"      Server: {detail['server_sample']}")
                print(f"      VBA: {detail['vba_sample']}")

def compare_timelines(server_timeline, vba_timeline, timeline_type):
    """
    タイムライン比較（許容誤差0.01）
    """
    if len(server_timeline) != len(vba_timeline):
        return False

    for i in range(len(server_timeline)):
        server_point = server_timeline[i]
        vba_point = vba_timeline[i]

        # FT時刻比較
        if timeline_type == "rain":
            # Rain: サーバーはft=3から、VBAはft=0から
            expected_server_ft = vba_point['ft'] + 3
        else:
            # SWI: 両方ft=0から
            expected_server_ft = vba_point['ft']

        if server_point['ft'] != expected_server_ft:
            return False

        # 値比較
        if abs(float(server_point['value']) - float(vba_point['value'])) > 0.01:
            return False

    return True

def main():
    """
    メイン処理
    """
    print("=== 2023年6月2日データでのサーバー vs VBA完全一致検証 ===")

    # 1. サーバー処理実行
    print("1. サーバー処理実行中...")
    server_result = test_server_with_vba_date()

    if not server_result:
        print("サーバー処理に失敗しました")
        return

    # 2. VBA CSVデータ読み込み
    print("\n2. VBA CSV正解データ読み込み中...")
    vba_data = load_vba_csv_data()

    vba_counts = {}
    for pref, data in vba_data.items():
        rain_count = len(data['rain'])
        swi_count = len(data['swi'])
        vba_counts[pref] = {'rain': rain_count, 'swi': swi_count}
        print(f"  {pref}: Rain={rain_count}, SWI={swi_count}")

    # 3. 詳細比較
    print("\n3. 詳細比較実行中...")
    compare_server_with_vba(server_result, vba_data)

if __name__ == "__main__":
    main()
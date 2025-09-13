#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBAとPythonサーバーの完全一致検証
全メッシュの詳細比較とレポート生成
"""
import sys
import os
import csv
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.main_service import MainService

def load_vba_reference_data():
    """
    VBA CSVファイルからすべての参照データを読み込み
    """
    print("=== VBA参照データ読み込み ===")

    prefectures = ['shiga', 'kyoto', 'osaka', 'hyogo', 'nara', 'wakayama']
    vba_data = {}

    for pref in prefectures:
        print(f"\n{pref}県データ読み込み中...")
        vba_data[pref] = {'rain': {}, 'swi': {}}

        # Rain CSV読み込み
        rain_file = f'data/{pref}_rain.csv'
        if os.path.exists(rain_file):
            try:
                with open(rain_file, 'r', encoding='shift_jis') as f:
                    reader = csv.reader(f)
                    rows = list(reader)

                    # 2行目以降を処理（1行目は無意味データ）
                    for row_idx, row in enumerate(rows[1:], start=2):
                        if len(row) >= 6:
                            try:
                                area_name = row[0].strip()
                                x = int(row[1])
                                y = int(row[2])

                                # Rain timeline (FT=0,3,6,9,12,15...)
                                rain_timeline = []
                                for i, val_str in enumerate(row[3:]):
                                    if val_str.strip() == '':
                                        break
                                    try:
                                        value = float(val_str)
                                        rain_timeline.append({
                                            "ft": i * 3,  # VBAはft=0から
                                            "value": value
                                        })
                                    except ValueError:
                                        break

                                key = f"{area_name}_{x}_{y}"
                                vba_data[pref]['rain'][key] = {
                                    'area_name': area_name,
                                    'x': x,
                                    'y': y,
                                    'timeline': rain_timeline,
                                    'csv_row': row_idx
                                }

                            except (ValueError, IndexError):
                                continue

                rain_count = len(vba_data[pref]['rain'])
                print(f"  Rain: {rain_count} メッシュ")

            except Exception as e:
                print(f"  Rain CSVエラー: {e}")

        # SWI CSV読み込み
        swi_file = f'data/{pref}_swi.csv'
        if os.path.exists(swi_file):
            try:
                with open(swi_file, 'r', encoding='shift_jis') as f:
                    reader = csv.reader(f)
                    rows = list(reader)

                    # 2行目以降を処理（1行目は無意味データ）
                    for row_idx, row in enumerate(rows[1:], start=2):
                        if len(row) >= 10:
                            try:
                                area_name = row[0].strip()
                                x = int(row[1])
                                y = int(row[2])

                                # 境界値
                                advisary_bound = int(row[3]) if row[3].strip() != '' else 9999
                                warning_bound = int(row[4]) if row[4].strip() != '' else 9999
                                dosyakei_bound = int(row[5]) if row[5].strip() != '' else 9999

                                # SWI timeline (FT=0,3,6,9,12,15...)
                                swi_timeline = []
                                for i, val_str in enumerate(row[6:]):
                                    if val_str.strip() == '':
                                        break
                                    try:
                                        value = float(val_str)
                                        swi_timeline.append({
                                            "ft": i * 3,  # VBAはft=0から
                                            "value": value
                                        })
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
                                    'timeline': swi_timeline,
                                    'csv_row': row_idx
                                }

                            except (ValueError, IndexError):
                                continue

                swi_count = len(vba_data[pref]['swi'])
                print(f"  SWI: {swi_count} メッシュ")

            except Exception as e:
                print(f"  SWI CSVエラー: {e}")

    total_rain = sum(len(data['rain']) for data in vba_data.values())
    total_swi = sum(len(data['swi']) for data in vba_data.values())
    print(f"\nVBA参照データ読み込み完了:")
    print(f"  Rain総数: {total_rain} メッシュ")
    print(f"  SWI総数: {total_swi} メッシュ")

    return vba_data

def run_server_processing():
    """
    サーバー処理を実行して結果を取得
    """
    print("\n=== サーバー処理実行 ===")

    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"

    # ファイル存在確認
    if not os.path.exists(swi_file):
        print(f"SWIファイル不足: {swi_file}")
        return None

    if not os.path.exists(guidance_file):
        print(f"ガイダンスファイル不足: {guidance_file}")
        return None

    try:
        main_service = MainService()
        result = main_service.main_process_from_files(swi_file, guidance_file)

        if result.get('status') == 'success':
            print("サーバー処理成功")
            return result
        else:
            print(f"サーバー処理エラー: {result.get('message', 'Unknown error')}")
            return None

    except Exception as e:
        print(f"サーバー処理例外: {e}")
        import traceback
        traceback.print_exc()
        return None

def comprehensive_comparison(server_result, vba_data):
    """
    サーバー結果とVBAデータの包括的比較
    """
    print("\n=== 包括的比較分析 ===")

    if not server_result or 'prefectures' not in server_result:
        print("サーバー結果が無効です")
        return None

    comparison_report = {
        'total_matches': {
            'boundary_exact': 0,
            'boundary_partial': 0,
            'boundary_mismatch': 0,
            'rain_exact': 0,
            'rain_close': 0,  # 許容誤差内
            'rain_mismatch': 0,
            'swi_exact': 0,
            'swi_close': 0,   # 許容誤差内
            'swi_mismatch': 0
        },
        'prefecture_details': {},
        'sample_mismatches': {
            'boundary': [],
            'rain': [],
            'swi': []
        },
        'summary': {}
    }

    # 許容誤差設定
    RAIN_TOLERANCE = 0.01  # 雨量許容誤差
    SWI_TOLERANCE = 0.01   # SWI許容誤差

    for pref_code, pref_data in server_result['prefectures'].items():
        if pref_code not in vba_data:
            continue

        print(f"\n{pref_code}県比較中...")

        pref_report = {
            'server_meshes': 0,
            'vba_rain_meshes': len(vba_data[pref_code]['rain']),
            'vba_swi_meshes': len(vba_data[pref_code]['swi']),
            'boundary_matches': 0,
            'rain_matches': 0,
            'swi_matches': 0,
            'unmatched_server': [],
            'unmatched_vba': []
        }

        # サーバーメッシュを処理
        for area in pref_data.get('areas', []):
            area_name = area.get('name', '')

            for mesh in area.get('meshes', []):
                pref_report['server_meshes'] += 1

                # 対応するVBAデータを検索
                vba_rain_match = None
                vba_swi_match = None

                # エリア名で検索（複数のVBAメッシュが存在する可能性）
                for vba_key, vba_rain_data in vba_data[pref_code]['rain'].items():
                    if vba_rain_data['area_name'] == area_name:
                        # 対応するSWIデータも確認
                        if vba_key in vba_data[pref_code]['swi']:
                            vba_swi_data = vba_data[pref_code]['swi'][vba_key]

                            # 境界値でマッチング確認
                            server_advisary = mesh.get('advisary_bound', 0)
                            server_warning = mesh.get('warning_bound', 0)
                            server_dosyakei = mesh.get('dosyakei_bound', 0)

                            if (server_advisary == vba_swi_data['advisary_bound'] and
                                server_warning == vba_swi_data['warning_bound'] and
                                server_dosyakei == vba_swi_data['dosyakei_bound']):
                                vba_rain_match = vba_rain_data
                                vba_swi_match = vba_swi_data
                                break

                if vba_rain_match and vba_swi_match:
                    # 境界値比較
                    boundary_match = compare_boundary_values(mesh, vba_swi_match)
                    if boundary_match['exact']:
                        comparison_report['total_matches']['boundary_exact'] += 1
                        pref_report['boundary_matches'] += 1
                    elif boundary_match['partial']:
                        comparison_report['total_matches']['boundary_partial'] += 1
                    else:
                        comparison_report['total_matches']['boundary_mismatch'] += 1
                        if len(comparison_report['sample_mismatches']['boundary']) < 5:
                            comparison_report['sample_mismatches']['boundary'].append({
                                'prefecture': pref_code,
                                'area': area_name,
                                'server': boundary_match['server'],
                                'vba': boundary_match['vba']
                            })

                    # Rain timeline比較
                    rain_match = compare_rain_timeline(mesh, vba_rain_match, RAIN_TOLERANCE)
                    if rain_match['exact']:
                        comparison_report['total_matches']['rain_exact'] += 1
                        pref_report['rain_matches'] += 1
                    elif rain_match['close']:
                        comparison_report['total_matches']['rain_close'] += 1
                        pref_report['rain_matches'] += 1
                    else:
                        comparison_report['total_matches']['rain_mismatch'] += 1
                        if len(comparison_report['sample_mismatches']['rain']) < 5:
                            comparison_report['sample_mismatches']['rain'].append({
                                'prefecture': pref_code,
                                'area': area_name,
                                'server_sample': rain_match['server_sample'],
                                'vba_sample': rain_match['vba_sample'],
                                'difference': rain_match['max_difference']
                            })

                    # SWI timeline比較
                    swi_match = compare_swi_timeline(mesh, vba_swi_match, SWI_TOLERANCE)
                    if swi_match['exact']:
                        comparison_report['total_matches']['swi_exact'] += 1
                        pref_report['swi_matches'] += 1
                    elif swi_match['close']:
                        comparison_report['total_matches']['swi_close'] += 1
                        pref_report['swi_matches'] += 1
                    else:
                        comparison_report['total_matches']['swi_mismatch'] += 1
                        if len(comparison_report['sample_mismatches']['swi']) < 5:
                            comparison_report['sample_mismatches']['swi'].append({
                                'prefecture': pref_code,
                                'area': area_name,
                                'server_sample': swi_match['server_sample'],
                                'vba_sample': swi_match['vba_sample'],
                                'difference': swi_match['max_difference']
                            })
                else:
                    # 対応するVBAデータが見つからない
                    pref_report['unmatched_server'].append({
                        'mesh_code': mesh.get('code', 'N/A'),
                        'area': area_name,
                        'boundary': f"{mesh.get('advisary_bound', 0)}/{mesh.get('warning_bound', 0)}/{mesh.get('dosyakei_bound', 0)}"
                    })

        comparison_report['prefecture_details'][pref_code] = pref_report

        print(f"  サーバーメッシュ: {pref_report['server_meshes']}")
        print(f"  VBA Rain: {pref_report['vba_rain_meshes']}")
        print(f"  VBA SWI: {pref_report['vba_swi_meshes']}")
        print(f"  境界値一致: {pref_report['boundary_matches']}")
        print(f"  Rain一致: {pref_report['rain_matches']}")
        print(f"  SWI一致: {pref_report['swi_matches']}")
        print(f"  未対応サーバー: {len(pref_report['unmatched_server'])}")

    # 総合サマリー
    total_server_meshes = sum(report['server_meshes'] for report in comparison_report['prefecture_details'].values())
    total_boundary_matches = sum(report['boundary_matches'] for report in comparison_report['prefecture_details'].values())
    total_rain_matches = sum(report['rain_matches'] for report in comparison_report['prefecture_details'].values())
    total_swi_matches = sum(report['swi_matches'] for report in comparison_report['prefecture_details'].values())

    comparison_report['summary'] = {
        'total_server_meshes': total_server_meshes,
        'boundary_match_rate': (total_boundary_matches / total_server_meshes * 100) if total_server_meshes > 0 else 0,
        'rain_match_rate': (total_rain_matches / total_server_meshes * 100) if total_server_meshes > 0 else 0,
        'swi_match_rate': (total_swi_matches / total_server_meshes * 100) if total_server_meshes > 0 else 0
    }

    print(f"\n=== 総合結果 ===")
    print(f"総サーバーメッシュ: {total_server_meshes}")
    print(f"境界値一致率: {comparison_report['summary']['boundary_match_rate']:.1f}%")
    print(f"Rain一致率: {comparison_report['summary']['rain_match_rate']:.1f}%")
    print(f"SWI一致率: {comparison_report['summary']['swi_match_rate']:.1f}%")

    return comparison_report

def compare_boundary_values(server_mesh, vba_swi_data):
    """境界値比較"""
    server_advisary = server_mesh.get('advisary_bound', 0)
    server_warning = server_mesh.get('warning_bound', 0)
    server_dosyakei = server_mesh.get('dosyakei_bound', 0)

    vba_advisary = vba_swi_data['advisary_bound']
    vba_warning = vba_swi_data['warning_bound']
    vba_dosyakei = vba_swi_data['dosyakei_bound']

    exact = (server_advisary == vba_advisary and
             server_warning == vba_warning and
             server_dosyakei == vba_dosyakei)

    partial = (server_advisary == vba_advisary)  # 注意報基準値のみ一致

    return {
        'exact': exact,
        'partial': partial,
        'server': f"{server_advisary}/{server_warning}/{server_dosyakei}",
        'vba': f"{vba_advisary}/{vba_warning}/{vba_dosyakei}"
    }

def compare_rain_timeline(server_mesh, vba_rain_data, tolerance):
    """Rain timeline比較"""
    server_timeline = server_mesh.get('rain_timeline', [])
    vba_timeline = vba_rain_data['timeline']

    # サーバーはft=3から、VBAはft=0から開始の調整
    server_adjusted = []
    for point in server_timeline:
        server_adjusted.append({
            'ft': point['ft'] - 3,  # サーバーft=3 → VBAft=0に調整
            'value': point['value']
        })

    exact_match = True
    close_match = True
    max_difference = 0

    min_length = min(len(server_adjusted), len(vba_timeline))

    for i in range(min_length):
        server_point = server_adjusted[i]
        vba_point = vba_timeline[i]

        # FT一致確認
        if server_point['ft'] != vba_point['ft']:
            exact_match = False
            close_match = False
            break

        # 値の差分計算
        value_diff = abs(float(server_point['value']) - float(vba_point['value']))
        max_difference = max(max_difference, value_diff)

        if value_diff > 0.001:  # 完全一致でない
            exact_match = False

        if value_diff > tolerance:  # 許容誤差を超える
            close_match = False

    return {
        'exact': exact_match,
        'close': close_match,
        'max_difference': max_difference,
        'server_sample': server_adjusted[:3],
        'vba_sample': vba_timeline[:3]
    }

def compare_swi_timeline(server_mesh, vba_swi_data, tolerance):
    """SWI timeline比較"""
    server_timeline = server_mesh.get('swi_timeline', [])
    vba_timeline = vba_swi_data['timeline']

    exact_match = True
    close_match = True
    max_difference = 0

    min_length = min(len(server_timeline), len(vba_timeline))

    for i in range(min_length):
        server_point = server_timeline[i]
        vba_point = vba_timeline[i]

        # FT一致確認 (SWIは両方ft=0から開始)
        if server_point['ft'] != vba_point['ft']:
            exact_match = False
            close_match = False
            break

        # 値の差分計算
        value_diff = abs(float(server_point['value']) - float(vba_point['value']))
        max_difference = max(max_difference, value_diff)

        if value_diff > 0.001:  # 完全一致でない
            exact_match = False

        if value_diff > tolerance:  # 許容誤差を超える
            close_match = False

    return {
        'exact': exact_match,
        'close': close_match,
        'max_difference': max_difference,
        'server_sample': server_timeline[:3],
        'vba_sample': vba_timeline[:3]
    }

def main():
    """
    メイン処理
    """
    print("=== VBA vs Python サーバー 包括的一致検証 ===")

    # 1. VBA参照データ読み込み
    vba_data = load_vba_reference_data()
    if not vba_data:
        print("VBA参照データの読み込みに失敗しました")
        return

    # 2. サーバー処理実行
    server_result = run_server_processing()
    if not server_result:
        print("サーバー処理に失敗しました")
        return

    # 3. 包括的比較
    comparison_report = comprehensive_comparison(server_result, vba_data)
    if not comparison_report:
        print("比較処理に失敗しました")
        return

    # 4. 結果保存
    with open('comprehensive_verification_report.json', 'w', encoding='utf-8') as f:
        json.dump(comparison_report, f, ensure_ascii=False, indent=2)

    print("\n包括的検証レポートを comprehensive_verification_report.json に保存しました")

    # 5. 重要な不一致サンプル表示
    if comparison_report['sample_mismatches']['boundary']:
        print("\n=== 境界値不一致サンプル ===")
        for mismatch in comparison_report['sample_mismatches']['boundary']:
            print(f"  {mismatch['prefecture']} {mismatch['area']}")
            print(f"    Server: {mismatch['server']}")
            print(f"    VBA: {mismatch['vba']}")

    if comparison_report['sample_mismatches']['rain']:
        print("\n=== Rain不一致サンプル ===")
        for mismatch in comparison_report['sample_mismatches']['rain']:
            print(f"  {mismatch['prefecture']} {mismatch['area']}")
            print(f"    最大差分: {mismatch['difference']:.4f}")
            print(f"    Server: {mismatch['server_sample']}")
            print(f"    VBA: {mismatch['vba_sample']}")

    if comparison_report['sample_mismatches']['swi']:
        print("\n=== SWI不一致サンプル ===")
        for mismatch in comparison_report['sample_mismatches']['swi']:
            print(f"  {mismatch['prefecture']} {mismatch['area']}")
            print(f"    最大差分: {mismatch['difference']:.4f}")
            print(f"    Server: {mismatch['server_sample']}")
            print(f"    VBA: {mismatch['vba_sample']}")

if __name__ == "__main__":
    main()
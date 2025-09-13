#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部分一致の詳細原因分析（FT時刻問題の特定）
"""
import requests
import csv

def get_sample_meshes():
    """
    分析用サンプルメッシュを取得
    """
    try:
        url = "http://localhost:5000/api/test-full-soil-rainfall-index"
        response = requests.get(url, timeout=120)
        if response.status_code != 200:
            return None, None

        data = response.json()

        # 滋賀県の最初のメッシュを取得
        for pref_code, pref_data in data['prefectures'].items():
            if pref_code == 'shiga':
                for area in pref_data.get('areas', [])[:1]:  # 最初のエリアのみ
                    for mesh in area.get('meshes', [])[:1]:  # 最初のメッシュのみ
                        server_mesh = {
                            'pref': pref_code,
                            'area': area.get('name', ''),
                            'meshcode': mesh.get('code', ''),
                            'lat': mesh.get('lat'),
                            'lon': mesh.get('lon'),
                            'advisary_bound': mesh.get('advisary_bound'),
                            'warning_bound': mesh.get('warning_bound'),
                            'dosyakei_bound': mesh.get('dosyakei_bound'),
                            'rain_timeline': mesh.get('rain_timeline', []),
                            'swi_timeline': mesh.get('swi_timeline', [])
                        }

                        # 対応するVBAメッシュを取得
                        area_name = area.get('name', '')
                        vba_mesh = get_vba_mesh_by_area(area_name)

                        return server_mesh, vba_mesh

        return None, None

    except Exception as e:
        print(f"エラー: {e}")
        return None, None

def get_vba_mesh_by_area(area_name):
    """
    指定されたAREA名の最初のVBAメッシュを取得
    """
    result = {}

    # Rain データ取得
    try:
        with open('data/shiga_rain.csv', 'r', encoding='shift_jis') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 6 and row[0].strip() == area_name:
                    x = int(row[1])
                    y = int(row[2])

                    rain_timeline = []
                    for i, val_str in enumerate(row[3:]):
                        if val_str.strip() == '':
                            break
                        try:
                            value = float(val_str)
                            rain_timeline.append({"ft": i * 3, "value": value})
                        except ValueError:
                            break

                    result.update({
                        'area_name': area_name,
                        'x': x,
                        'y': y,
                        'vba_meshcode': f"{x * 10000 + y}",
                        'rain_timeline': rain_timeline
                    })
                    break

    except Exception as e:
        print(f"Rain読み込みエラー: {e}")

    # SWI データ取得
    try:
        with open('data/shiga_swi.csv', 'r', encoding='shift_jis') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 7:
                    # 空行をスキップ
                    if row[0].strip() == '' and row[1].strip() == '':
                        continue
                    if row[0].strip() == area_name:
                        advisary_bound = int(row[3]) if row[3].strip() != '' else 0
                        warning_bound = int(row[4]) if row[4].strip() != '' else 0
                        dosyakei_bound = int(row[5]) if row[5].strip() != '' else 0

                        swi_timeline = []
                        for i, val_str in enumerate(row[6:]):
                            if val_str.strip() == '':
                                break
                            try:
                                value = float(val_str)
                                swi_timeline.append({"ft": i * 3, "value": value})
                            except ValueError:
                                break

                        result.update({
                            'advisary_bound': advisary_bound,
                            'warning_bound': warning_bound,
                            'dosyakei_bound': dosyakei_bound,
                            'swi_timeline': swi_timeline
                        })
                        break

    except Exception as e:
        print(f"SWI読み込みエラー: {e}")

    return result

def analyze_timeline_mismatch():
    """
    タイムライン不一致の詳細分析
    """
    print("=== タイムライン不一致詳細分析 ===")
    print()

    server_mesh, vba_mesh = get_sample_meshes()

    if not server_mesh or not vba_mesh:
        print("サンプルメッシュの取得に失敗しました")
        return

    print("1. サンプルメッシュ情報:")
    print(f"   サーバー: {server_mesh['meshcode']} ({server_mesh['area']})")
    print(f"   VBA: {vba_mesh['vba_meshcode']} ({vba_mesh['area_name']})")
    print()

    # 境界値比較
    print("2. 境界値比較:")
    print(f"   サーバー: {server_mesh['advisary_bound']}/{server_mesh['warning_bound']}/{server_mesh['dosyakei_bound']}")
    print(f"   VBA: {vba_mesh['advisary_bound']}/{vba_mesh['warning_bound']}/{vba_mesh['dosyakei_bound']}")
    boundary_match = (
        server_mesh['advisary_bound'] == vba_mesh['advisary_bound'] and
        server_mesh['warning_bound'] == vba_mesh['warning_bound'] and
        server_mesh['dosyakei_bound'] == vba_mesh['dosyakei_bound']
    )
    print(f"   境界値一致: {'OK' if boundary_match else 'NG'}")
    print()

    # Rain timeline詳細比較
    print("3. Rain Timeline詳細比較:")
    server_rain = server_mesh['rain_timeline']
    vba_rain = vba_mesh['rain_timeline']

    print(f"   サーバーRain ({len(server_rain)} points):")
    for i, point in enumerate(server_rain[:10]):  # 最初の10点
        print(f"     [{i}] ft={point['ft']:2d}, value={point['value']:6.1f}")

    print(f"   VBA Rain ({len(vba_rain)} points):")
    for i, point in enumerate(vba_rain[:10]):  # 最初の10点
        print(f"     [{i}] ft={point['ft']:2d}, value={point['value']:6.1f}")

    # 詳細比較分析
    if len(server_rain) == len(vba_rain):
        print(f"   長さ: 一致 ({len(server_rain)} points)")

        mismatches = []
        for i in range(len(server_rain)):
            server_point = server_rain[i]
            vba_point = vba_rain[i]

            ft_match = server_point['ft'] == vba_point['ft'] + 3 if i == 0 else server_point['ft'] == vba_point['ft']
            val_match = abs(server_point['value'] - vba_point['value']) <= 0.01

            if not ft_match or not val_match:
                mismatches.append({
                    'index': i,
                    'server_ft': server_point['ft'],
                    'vba_ft': vba_point['ft'],
                    'expected_server_ft': vba_point['ft'] + 3 if i == 0 else vba_point['ft'],
                    'server_val': server_point['value'],
                    'vba_val': vba_point['value'],
                    'val_diff': abs(server_point['value'] - vba_point['value']),
                    'ft_match': ft_match,
                    'val_match': val_match
                })

        if mismatches:
            print(f"   不一致点数: {len(mismatches)}")
            print(f"   不一致詳細:")
            for mm in mismatches[:5]:
                print(f"     [{mm['index']}] FT: server={mm['server_ft']} vs expected={mm['expected_server_ft']} ({'OK' if mm['ft_match'] else 'NG'})")
                print(f"           VAL: server={mm['server_val']:.3f} vs vba={mm['vba_val']:.3f} diff={mm['val_diff']:.6f} ({'OK' if mm['val_match'] else 'NG'})")
        else:
            print(f"   完全一致: OK")
    else:
        print(f"   長さ: 不一致 (server={len(server_rain)} vs vba={len(vba_rain)})")

    print()

    # SWI timeline詳細比較
    print("4. SWI Timeline詳細比較:")
    server_swi = server_mesh['swi_timeline']
    vba_swi = vba_mesh['swi_timeline']

    print(f"   サーバーSWI ({len(server_swi)} points):")
    for i, point in enumerate(server_swi[:10]):  # 最初の10点
        print(f"     [{i}] ft={point['ft']:2d}, value={point['value']:8.3f}")

    print(f"   VBA SWI ({len(vba_swi)} points):")
    for i, point in enumerate(vba_swi[:10]):  # 最初の10点
        print(f"     [{i}] ft={point['ft']:2d}, value={point['value']:8.3f}")

    # SWI詳細比較分析
    if len(server_swi) == len(vba_swi):
        print(f"   長さ: 一致 ({len(server_swi)} points)")

        swi_mismatches = []
        for i in range(len(server_swi)):
            server_point = server_swi[i]
            vba_point = vba_swi[i]

            ft_match = server_point['ft'] == vba_point['ft']  # SWIは両方ft=0から開始
            val_match = abs(server_point['value'] - vba_point['value']) <= 0.01

            if not ft_match or not val_match:
                swi_mismatches.append({
                    'index': i,
                    'server_ft': server_point['ft'],
                    'vba_ft': vba_point['ft'],
                    'server_val': server_point['value'],
                    'vba_val': vba_point['value'],
                    'val_diff': abs(server_point['value'] - vba_point['value']),
                    'ft_match': ft_match,
                    'val_match': val_match
                })

        if swi_mismatches:
            print(f"   不一致点数: {len(swi_mismatches)}")
            print(f"   不一致詳細:")
            for mm in swi_mismatches[:5]:
                print(f"     [{mm['index']}] FT: server={mm['server_ft']} vs vba={mm['vba_ft']} ({'OK' if mm['ft_match'] else 'NG'})")
                print(f"           VAL: server={mm['server_val']:.6f} vs vba={mm['vba_val']:.6f} diff={mm['val_diff']:.6f} ({'OK' if mm['val_match'] else 'NG'})")
        else:
            print(f"   完全一致: OK")
    else:
        print(f"   長さ: 不一致 (server={len(server_swi)} vs vba={len(vba_swi)})")

if __name__ == "__main__":
    analyze_timeline_mismatch()
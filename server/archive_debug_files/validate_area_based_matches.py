#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AREA（地域）ベースでのVBA期待値とサーバー結果の完全一致検証
1つのサーバーメッシュに複数のVBAメッシュが対応する正常パターンを考慮
"""
import requests
import csv
import json

def get_all_server_meshes():
    """
    全サーバーメッシュデータを取得（AREA情報付き）
    """
    try:
        url = "http://localhost:5000/api/test-full-soil-rainfall-index"
        response = requests.get(url, timeout=300)
        if response.status_code != 200:
            print(f"Server error: {response.status_code}")
            return {}

        data = response.json()
        server_meshes = {}

        for pref_code, pref_data in data['prefectures'].items():
            for area in pref_data.get('areas', []):
                area_name = area.get('name', '')
                for mesh in area.get('meshes', []):
                    meshcode = mesh.get('code', '')
                    # 複合キー: メッシュコード + AREA名
                    composite_key = f"{meshcode}_{area_name}"

                    server_meshes[composite_key] = {
                        'pref': pref_code,
                        'area': area_name,
                        'meshcode': meshcode,
                        'lat': mesh.get('lat'),
                        'lon': mesh.get('lon'),
                        'advisary_bound': mesh.get('advisary_bound'),
                        'warning_bound': mesh.get('warning_bound'),
                        'dosyakei_bound': mesh.get('dosyakei_bound'),
                        'rain_timeline': mesh.get('rain_timeline', []),
                        'swi_timeline': mesh.get('swi_timeline', [])
                    }

        return server_meshes

    except Exception as e:
        print(f"エラー: {e}")
        return {}

def get_all_vba_meshes():
    """
    全VBAメッシュデータを取得（AREA情報付き）
    """
    prefectures = ['shiga', 'kyoto', 'osaka', 'hyogo', 'nara', 'wakayama']
    vba_meshes = {}

    for pref in prefectures:
        # Rain データ取得
        try:
            with open(f'data/{pref}_rain.csv', 'r', encoding='shift_jis') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 6:
                        try:
                            area_name = row[0].strip()
                            x = int(row[1])
                            y = int(row[2])
                            vba_meshcode = f"{x * 10000 + y}"

                            # 複合キー: VBAメッシュコード + AREA名
                            composite_key = f"{vba_meshcode}_{area_name}"

                            if composite_key not in vba_meshes:
                                vba_meshes[composite_key] = {
                                    'pref': pref,
                                    'area_name': area_name,
                                    'x': x,
                                    'y': y,
                                    'vba_meshcode': vba_meshcode
                                }

                            # Rain timeline
                            rain_timeline = []
                            for i, val_str in enumerate(row[3:]):
                                if val_str.strip() == '':
                                    break
                                try:
                                    value = float(val_str)
                                    rain_timeline.append({"ft": i * 3, "value": value})
                                except ValueError:
                                    break

                            vba_meshes[composite_key]['rain_timeline'] = rain_timeline

                        except ValueError:
                            continue

        except Exception as e:
            print(f"Error reading {pref}_rain.csv: {e}")

        # SWI データ取得
        try:
            with open(f'data/{pref}_swi.csv', 'r', encoding='shift_jis') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 7:
                        # 空行をスキップ
                        if row[0].strip() == '' and row[1].strip() == '':
                            continue
                        try:
                            area_name = row[0].strip()
                            x = int(row[1])
                            y = int(row[2])
                            vba_meshcode = f"{x * 10000 + y}"

                            # 複合キー: VBAメッシュコード + AREA名
                            composite_key = f"{vba_meshcode}_{area_name}"

                            if composite_key not in vba_meshes:
                                vba_meshes[composite_key] = {
                                    'pref': pref,
                                    'area_name': area_name,
                                    'x': x,
                                    'y': y,
                                    'vba_meshcode': vba_meshcode
                                }

                            # 境界値
                            advisary_bound = int(row[3]) if row[3].strip() != '' else 0
                            warning_bound = int(row[4]) if row[4].strip() != '' else 0
                            dosyakei_bound = int(row[5]) if row[5].strip() != '' else 0

                            # SWI timeline
                            swi_timeline = []
                            for i, val_str in enumerate(row[6:]):
                                if val_str.strip() == '':
                                    break
                                try:
                                    value = float(val_str)
                                    swi_timeline.append({"ft": i * 3, "value": value})
                                except ValueError:
                                    break

                            vba_meshes[composite_key].update({
                                'advisary_bound': advisary_bound,
                                'warning_bound': warning_bound,
                                'dosyakei_bound': dosyakei_bound,
                                'swi_timeline': swi_timeline
                            })

                        except ValueError:
                            continue

        except Exception as e:
            print(f"Error reading {pref}_swi.csv: {e}")

    return vba_meshes

def compare_timelines(server_timeline, vba_timeline, tolerance=0.01):
    """
    2つのタイムラインを比較（FT時間差を考慮）
    """
    if len(server_timeline) != len(vba_timeline):
        return False, f"length_diff: server={len(server_timeline)} vs vba={len(vba_timeline)}"

    for i in range(len(server_timeline)):
        server_point = server_timeline[i]
        vba_point = vba_timeline[i]

        # FT時刻の比較（サーバーft=3から、VBAft=0から開始の差を考慮）
        expected_server_ft = vba_point['ft'] + 3 if i == 0 else vba_point['ft']

        if server_point['ft'] != expected_server_ft:
            return False, f"ft_mismatch: server_ft={server_point['ft']} vs expected={expected_server_ft}"

        # 値の比較
        server_val = float(server_point['value'])
        vba_val = float(vba_point['value'])
        diff = abs(server_val - vba_val)

        if diff > tolerance:
            return False, f"value_mismatch: server={server_val} vs vba={vba_val} diff={diff:.6f}"

    return True, "perfect_match"

def validate_area_based_matches():
    """
    AREA（地域）ベースでの完全一致検証
    """
    print("=== AREA（地域）ベース完全一致検証 ===")
    print()

    # 全データ取得
    print("1. 全データ取得中...")
    server_meshes = get_all_server_meshes()
    vba_meshes = get_all_vba_meshes()

    print(f"   サーバーメッシュ数: {len(server_meshes):,}")
    print(f"   VBAメッシュ数: {len(vba_meshes):,}")
    print()

    # AREA名ベース対応確認
    print("2. AREA名ベース対応確認...")

    # サーバーとVBAで共通のAREA名を抽出
    server_areas = set(mesh['area'] for mesh in server_meshes.values())
    vba_areas = set(mesh['area_name'] for mesh in vba_meshes.values())
    common_areas = server_areas & vba_areas

    print(f"   サーバーAREA数: {len(server_areas)}")
    print(f"   VBA AREA数: {len(vba_areas)}")
    print(f"   共通AREA数: {len(common_areas)}")

    if len(common_areas) == 0:
        print("   ❌ 共通のAREA名が見つかりませんでした")
        return

    print(f"   共通AREA例: {list(common_areas)[:5]}")
    print()

    # AREA名を使った直接マッチング
    print("3. AREA名ベース直接マッチング...")

    perfect_matches = []
    partial_matches = []

    for vba_key, vba_mesh in vba_meshes.items():
        area_name = vba_mesh['area_name']

        # 同じAREA名を持つサーバーメッシュを探索
        matching_server_meshes = []
        for server_key, server_mesh in server_meshes.items():
            if server_mesh['area'] == area_name and server_mesh['pref'] == vba_mesh['pref']:
                matching_server_meshes.append((server_key, server_mesh))

        if not matching_server_meshes:
            continue

        # 各サーバーメッシュとの詳細比較
        for server_key, server_mesh in matching_server_meshes:
            # 境界値一致確認
            boundary_match = (
                server_mesh['advisary_bound'] == vba_mesh.get('advisary_bound', -1) and
                server_mesh['warning_bound'] == vba_mesh.get('warning_bound', -1) and
                server_mesh['dosyakei_bound'] == vba_mesh.get('dosyakei_bound', -1)
            )

            if not boundary_match:
                continue

            # Rain timeline比較
            server_rain = server_mesh['rain_timeline']
            vba_rain = vba_mesh.get('rain_timeline', [])
            rain_match, rain_reason = compare_timelines(server_rain, vba_rain)

            # SWI timeline比較
            server_swi = server_mesh['swi_timeline']
            vba_swi = vba_mesh.get('swi_timeline', [])
            swi_match, swi_reason = compare_timelines(server_swi, vba_swi)

            match_result = {
                'server_key': server_key,
                'vba_key': vba_key,
                'pref': server_mesh['pref'],
                'area': area_name,
                'server_meshcode': server_mesh['meshcode'],
                'vba_meshcode': vba_mesh['vba_meshcode'],
                'vba_coords': f"x={vba_mesh['x']}, y={vba_mesh['y']}",
                'boundary_match': boundary_match,
                'rain_match': rain_match,
                'swi_match': swi_match,
                'rain_reason': rain_reason,
                'swi_reason': swi_reason,
                'boundary_values': f"{server_mesh['advisary_bound']}/{server_mesh['warning_bound']}/{server_mesh['dosyakei_bound']}"
            }

            if rain_match and swi_match:
                perfect_matches.append(match_result)
            else:
                partial_matches.append(match_result)

    print(f"   完全一致ペア: {len(perfect_matches):,}")
    print(f"   部分一致ペア: {len(partial_matches):,}")
    print()

    # 結果詳細表示
    print("4. 結果詳細:")

    if len(perfect_matches) > 0:
        print(f"   OK {len(perfect_matches):,} 個の完全一致ペアを発見")

        # 都道府県別集計
        pref_counts = {}
        for match in perfect_matches:
            pref = match['pref']
            pref_counts[pref] = pref_counts.get(pref, 0) + 1

        print(f"   都道府県別完全一致数:")
        for pref, count in sorted(pref_counts.items()):
            print(f"     {pref}: {count:,} ペア")

        # サンプル表示
        print(f"   完全一致サンプル (最初の5つ):")
        for match in perfect_matches[:5]:
            print(f"     {match['pref']}/{match['area']}: {match['server_meshcode']} ↔ {match['vba_meshcode']}")
            print(f"       境界値: {match['boundary_values']}, VBA座標: {match['vba_coords']}")

        # 全メッシュ数との比較
        total_server = len(server_meshes)
        total_vba = len(vba_meshes)
        match_rate_server = (len(perfect_matches) / total_server) * 100
        match_rate_vba = (len(perfect_matches) / total_vba) * 100

        print(f"\n5. 一致率:")
        print(f"   サーバーメッシュに対する一致率: {match_rate_server:.2f}% ({len(perfect_matches):,}/{total_server:,})")
        print(f"   VBAメッシュに対する一致率: {match_rate_vba:.2f}% ({len(perfect_matches):,}/{total_vba:,})")

        if match_rate_server == 100.0 and match_rate_vba == 100.0:
            print(f"\n OK 結論: 全メッシュで完全一致が確認されました！")
        else:
            print(f"\n NG 結論: 一部のメッシュで不一致があります。")

    else:
        print(f"   NG 完全一致するペアが見つかりませんでした")

        # 部分一致の分析
        if len(partial_matches) > 0:
            print(f"   部分一致の内訳:")
            rain_fails = [m for m in partial_matches if not m['rain_match']]
            swi_fails = [m for m in partial_matches if not m['swi_match']]

            print(f"     Rain不一致: {len(rain_fails)}")
            print(f"     SWI不一致: {len(swi_fails)}")

            # 不一致理由のサンプル
            if rain_fails:
                print(f"     Rain不一致例: {rain_fails[0]['rain_reason']}")
            if swi_fails:
                print(f"     SWI不一致例: {swi_fails[0]['swi_reason']}")

    # 結果保存
    result_summary = {
        'total_server_meshes': len(server_meshes),
        'total_vba_meshes': len(vba_meshes),
        'common_areas': len(common_areas),
        'perfect_matches': len(perfect_matches),
        'partial_matches': len(partial_matches),
        'prefecture_counts': pref_counts if 'pref_counts' in locals() else {},
        'perfect_match_details': perfect_matches[:10],  # 最初の10個のみ保存
        'partial_match_details': partial_matches[:10]   # 最初の10個のみ保存
    }

    with open('area_based_validation_results.json', 'w', encoding='utf-8') as f:
        json.dump(result_summary, f, ensure_ascii=False, indent=2)

    print(f"   詳細結果を area_based_validation_results.json に保存しました")

if __name__ == "__main__":
    validate_area_based_matches()
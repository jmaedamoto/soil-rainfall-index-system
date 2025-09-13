#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1:1完全一致メッシュを特定し、全メッシュでの完全検証を実行
"""
import requests
import csv
import json

def get_all_server_meshes():
    """
    全サーバーメッシュデータを取得
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
                for mesh in area.get('meshes', []):
                    meshcode = mesh.get('code', '')
                    server_meshes[meshcode] = {
                        'pref': pref_code,
                        'area': area.get('name', ''),
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
    全VBAメッシュデータを取得
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
                            area_name = row[0]
                            x = int(row[1])
                            y = int(row[2])
                            vba_meshcode = f"{x * 10000 + y}"

                            if vba_meshcode not in vba_meshes:
                                vba_meshes[vba_meshcode] = {
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

                            vba_meshes[vba_meshcode]['rain_timeline'] = rain_timeline

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
                            area_name = row[0]
                            x = int(row[1])
                            y = int(row[2])
                            vba_meshcode = f"{x * 10000 + y}"

                            if vba_meshcode not in vba_meshes:
                                vba_meshes[vba_meshcode] = {
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

                            vba_meshes[vba_meshcode].update({
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
    2つのタイムラインを比較（許容誤差付き）
    """
    if len(server_timeline) != len(vba_timeline):
        return False

    for i in range(len(server_timeline)):
        server_point = server_timeline[i]
        vba_point = vba_timeline[i]

        # FT時刻の比較（サーバーft=3から、VBAft=0から開始の差を考慮）
        expected_server_ft = vba_point['ft']
        if i == 0:
            expected_server_ft = vba_point['ft'] + 3  # 最初だけVBA ft=0 → server ft=3

        if server_point['ft'] != expected_server_ft:
            return False

        # 値の比較
        if abs(float(server_point['value']) - float(vba_point['value'])) > tolerance:
            return False

    return True

def find_perfect_matches():
    """
    1:1完全一致メッシュを特定
    """
    print("=== 1:1完全一致メッシュ特定・全メッシュ検証 ===")
    print()

    # 全データ取得
    print("1. 全サーバーメッシュ取得中...")
    server_meshes = get_all_server_meshes()
    print(f"   サーバーメッシュ数: {len(server_meshes)}")

    print("2. 全VBAメッシュ取得中...")
    vba_meshes = get_all_vba_meshes()
    print(f"   VBAメッシュ数: {len(vba_meshes)}")
    print()

    # 完全一致検証
    print("3. 完全一致検証実行中...")
    perfect_matches = []
    total_checks = 0
    boundary_matches = 0

    for server_meshcode, server_mesh in server_meshes.items():
        for vba_meshcode, vba_mesh in vba_meshes.items():
            total_checks += 1

            # 境界値一致確認
            if (server_mesh['advisary_bound'] == vba_mesh.get('advisary_bound', -1) and
                server_mesh['warning_bound'] == vba_mesh.get('warning_bound', -1) and
                server_mesh['dosyakei_bound'] == vba_mesh.get('dosyakei_bound', -1)):

                boundary_matches += 1

                # Rain timeline比較
                server_rain = server_mesh['rain_timeline']
                vba_rain = vba_mesh.get('rain_timeline', [])
                rain_match = compare_timelines(server_rain, vba_rain)

                # SWI timeline比較
                server_swi = server_mesh['swi_timeline']
                vba_swi = vba_mesh.get('swi_timeline', [])
                swi_match = compare_timelines(server_swi, vba_swi)

                if rain_match and swi_match:
                    perfect_matches.append({
                        'server_meshcode': server_meshcode,
                        'vba_meshcode': vba_meshcode,
                        'pref': server_mesh['pref'],
                        'server_coords': f"lat={server_mesh['lat']:.6f}, lon={server_mesh['lon']:.6f}",
                        'vba_coords': f"x={vba_mesh['x']}, y={vba_mesh['y']}",
                        'boundary': f"{server_mesh['advisary_bound']}/{server_mesh['warning_bound']}/{server_mesh['dosyakei_bound']}",
                        'rain_points': len(server_rain),
                        'swi_points': len(server_swi)
                    })

    print(f"   総比較回数: {total_checks:,}")
    print(f"   境界値一致: {boundary_matches:,}")
    print(f"   完全一致: {len(perfect_matches):,}")
    print()

    # 結果表示
    print("4. 完全一致結果:")
    if len(perfect_matches) == 0:
        print("   ❌ 完全一致するメッシュペアは見つかりませんでした")
        return

    print(f"   ✅ {len(perfect_matches):,} 個の完全一致メッシュペアを発見")

    # 都道府県別集計
    pref_counts = {}
    for match in perfect_matches:
        pref = match['pref']
        pref_counts[pref] = pref_counts.get(pref, 0) + 1

    print(f"\n   都道府県別一致数:")
    for pref, count in sorted(pref_counts.items()):
        print(f"     {pref}: {count:,} ペア")

    # サンプル表示（各府県から2つずつ）
    print(f"\n   完全一致サンプル:")
    shown_per_pref = {}
    for match in perfect_matches:
        pref = match['pref']
        if shown_per_pref.get(pref, 0) < 2:
            print(f"     {match['pref']}: {match['server_meshcode']} ↔ {match['vba_meshcode']}")
            print(f"       境界値: {match['boundary']}")
            print(f"       座標: Server({match['server_coords']}) ↔ VBA({match['vba_coords']})")
            shown_per_pref[pref] = shown_per_pref.get(pref, 0) + 1

    # 一致率計算
    server_mesh_count = len(server_meshes)
    vba_mesh_count = len(vba_meshes)
    match_rate_server = (len(perfect_matches) / server_mesh_count) * 100 if server_mesh_count > 0 else 0
    match_rate_vba = (len(perfect_matches) / vba_mesh_count) * 100 if vba_mesh_count > 0 else 0

    print(f"\n5. 一致率:")
    print(f"   サーバーメッシュに対する一致率: {match_rate_server:.2f}% ({len(perfect_matches):,}/{server_mesh_count:,})")
    print(f"   VBAメッシュに対する一致率: {match_rate_vba:.2f}% ({len(perfect_matches):,}/{vba_mesh_count:,})")

    # 結果保存
    result_summary = {
        'total_server_meshes': server_mesh_count,
        'total_vba_meshes': vba_mesh_count,
        'perfect_matches': len(perfect_matches),
        'match_rate_server': match_rate_server,
        'match_rate_vba': match_rate_vba,
        'prefecture_counts': pref_counts,
        'matches': perfect_matches
    }

    with open('complete_match_results.json', 'w', encoding='utf-8') as f:
        json.dump(result_summary, f, ensure_ascii=False, indent=2)

    print(f"   詳細結果を complete_match_results.json に保存しました")

    if match_rate_server == 100.0 and match_rate_vba == 100.0:
        print(f"\n🎉 結論: 全メッシュで完全一致が確認されました！")
    else:
        print(f"\n⚠️  結論: 一部のメッシュで不一致があります。詳細分析が必要です。")

if __name__ == "__main__":
    find_perfect_matches()
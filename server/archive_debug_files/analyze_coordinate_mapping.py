#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBAのx,y座標とサーバーの標準メッシュコードの対応関係を分析
"""
import requests
import csv
import math

def get_server_meshes():
    """
    サーバーから全メッシュデータを取得
    """
    try:
        url = "http://localhost:5000/api/test-full-soil-rainfall-index"
        response = requests.get(url, timeout=120)
        if response.status_code != 200:
            print(f"Server error: {response.status_code}")
            return []

        data = response.json()
        meshes = []

        for pref_code, pref_data in data['prefectures'].items():
            for area in pref_data.get('areas', []):
                for mesh in area.get('meshes', []):
                    meshes.append({
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
                    })

        return meshes

    except Exception as e:
        print(f"エラー: {e}")
        return []

def read_vba_coordinates(pref_name):
    """
    VBA CSVファイルからx,y座標を読み取り
    """
    vba_coords = []

    files_to_check = [
        f'data/{pref_name}_rain.csv',
        f'data/{pref_name}_swi.csv'
    ]

    for filename in files_to_check:
        try:
            with open(filename, 'r', encoding='shift_jis') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        # 空行をスキップ
                        if row[0].strip() == '' and row[1].strip() == '':
                            continue

                        try:
                            area_name = row[0]
                            x = int(row[1])
                            y = int(row[2])

                            # 重複チェック
                            coord_key = f"{x}_{y}"
                            if not any(c['coord_key'] == coord_key for c in vba_coords):
                                vba_coords.append({
                                    'area_name': area_name,
                                    'x': x,
                                    'y': y,
                                    'coord_key': coord_key,
                                    'vba_meshcode': str(x * 10000 + y),
                                    'source_file': filename
                                })

                        except ValueError:
                            continue

        except Exception as e:
            print(f"Error reading {filename}: {e}")

    return vba_coords

def find_coordinate_mapping(server_meshes, vba_coords):
    """
    サーバーメッシュとVBA座標の対応関係を分析
    """
    print(f"=== 座標マッピング分析 ===")
    print(f"サーバーメッシュ数: {len(server_meshes)}")
    print(f"VBA座標数: {len(vba_coords)}")

    # 境界値でマッチング可能性を探る
    matches = []
    for server_mesh in server_meshes:
        for vba_coord in vba_coords:
            # 境界値が完全一致する場合
            if (server_mesh['advisary_bound'] == vba_coord.get('advisary_bound') and
                server_mesh['warning_bound'] == vba_coord.get('warning_bound') and
                server_mesh['dosyakei_bound'] == vba_coord.get('dosyakei_bound')):

                matches.append({
                    'server_meshcode': server_mesh['meshcode'],
                    'server_lat': server_mesh['lat'],
                    'server_lon': server_mesh['lon'],
                    'vba_x': vba_coord['x'],
                    'vba_y': vba_coord['y'],
                    'vba_meshcode': vba_coord['vba_meshcode'],
                    'advisary': server_mesh['advisary_bound'],
                    'warning': server_mesh['warning_bound'],
                    'dosyakei': server_mesh['dosyakei_bound']
                })

    return matches

def analyze_coordinate_pattern(matches):
    """
    座標変換パターンを分析
    """
    print(f"\n=== 座標変換パターン分析 ===")
    print(f"境界値一致ペア数: {len(matches)}")

    if len(matches) == 0:
        print("境界値一致するペアが見つかりませんでした")
        return

    # 最初の10ペアを詳細表示
    print(f"\n境界値一致ペア詳細 (最初の10個):")
    for i, match in enumerate(matches[:10]):
        print(f"  {i+1}. server={match['server_meshcode']} (lat={match['server_lat']:.6f}, lon={match['server_lon']:.6f})")
        print(f"     vba=x{match['vba_x']}_y{match['vba_y']} ({match['vba_meshcode']})")
        print(f"     境界値: {match['advisary']}/{match['warning']}/{match['dosyakei']}")

    # 座標範囲の分析
    if matches:
        server_lats = [m['server_lat'] for m in matches]
        server_lons = [m['server_lon'] for m in matches]
        vba_xs = [m['vba_x'] for m in matches]
        vba_ys = [m['vba_y'] for m in matches]

        print(f"\n座標範囲分析:")
        print(f"  サーバー緯度: {min(server_lats):.6f} ～ {max(server_lats):.6f}")
        print(f"  サーバー経度: {min(server_lons):.6f} ～ {max(server_lons):.6f}")
        print(f"  VBA X: {min(vba_xs)} ～ {max(vba_xs)}")
        print(f"  VBA Y: {min(vba_ys)} ～ {max(vba_ys)}")

        # 変換式の推測
        print(f"\n変換係数の推測:")
        if len(matches) >= 2:
            # 線形変換の可能性を探る
            lat_to_y_ratios = []
            lon_to_x_ratios = []

            for match in matches:
                if match['server_lat'] != 0:
                    lat_to_y_ratios.append(match['vba_y'] / match['server_lat'])
                if match['server_lon'] != 0:
                    lon_to_x_ratios.append(match['vba_x'] / match['server_lon'])

            if lat_to_y_ratios:
                avg_lat_ratio = sum(lat_to_y_ratios) / len(lat_to_y_ratios)
                print(f"  平均 Y/緯度比: {avg_lat_ratio:.2f}")

            if lon_to_x_ratios:
                avg_lon_ratio = sum(lon_to_x_ratios) / len(lon_to_x_ratios)
                print(f"  平均 X/経度比: {avg_lon_ratio:.2f}")

def enhanced_boundary_matching():
    """
    境界値を使用した詳細マッチング分析
    """
    print("=== 境界値ベース詳細マッチング分析 ===")

    server_meshes = get_server_meshes()
    if not server_meshes:
        return

    # 各都道府県で個別分析
    prefectures = ['shiga', 'kyoto', 'osaka', 'hyogo', 'nara', 'wakayama']

    for pref in prefectures:
        print(f"\n{pref} 分析:")

        # サーバーメッシュ（該当府県のみ）
        pref_server_meshes = [m for m in server_meshes if m['pref'] == pref]

        # VBA座標データ読み込み
        vba_coords = read_vba_coordinates(pref)

        # 境界値データをVBA SWI CSVから取得
        try:
            with open(f'data/{pref}_swi.csv', 'r', encoding='shift_jis') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 6:
                        # 空行をスキップ
                        if row[0].strip() == '' and row[1].strip() == '':
                            continue

                        try:
                            x = int(row[1])
                            y = int(row[2])
                            advisary = int(row[3]) if row[3].strip() != '' else 0
                            warning = int(row[4]) if row[4].strip() != '' else 0
                            dosyakei = int(row[5]) if row[5].strip() != '' else 0

                            # 対応するvba_coordsエントリに境界値を追加
                            for vba_coord in vba_coords:
                                if vba_coord['x'] == x and vba_coord['y'] == y:
                                    vba_coord['advisary_bound'] = advisary
                                    vba_coord['warning_bound'] = warning
                                    vba_coord['dosyakei_bound'] = dosyakei
                                    break
                        except ValueError:
                            continue

        except Exception as e:
            print(f"  Error reading {pref}_swi.csv: {e}")
            continue

        # マッチング実行
        matches = find_coordinate_mapping(pref_server_meshes, vba_coords)

        print(f"  サーバーメッシュ: {len(pref_server_meshes)}")
        print(f"  VBA座標: {len(vba_coords)}")
        print(f"  境界値一致: {len(matches)}")

        if matches:
            analyze_coordinate_pattern(matches[:5])  # 最初の5つを分析

if __name__ == "__main__":
    enhanced_boundary_matching()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
境界値一致メッシュで実際のSWI・Rain値を比較
"""
import requests
import csv

def get_server_mesh_by_code(meshcode):
    """
    特定のメッシュコードのサーバーデータを取得
    """
    try:
        url = "http://localhost:5000/api/test-full-soil-rainfall-index"
        response = requests.get(url, timeout=120)
        if response.status_code != 200:
            return None

        data = response.json()

        for pref_code, pref_data in data['prefectures'].items():
            for area in pref_data.get('areas', []):
                for mesh in area.get('meshes', []):
                    if mesh.get('code') == meshcode:
                        return mesh
        return None

    except Exception as e:
        print(f"エラー: {e}")
        return None

def get_vba_mesh_data(pref, x, y):
    """
    VBA CSVからx,y座標に対応するデータを取得
    """
    result = {'rain': None, 'swi': None}

    # Rain データ
    try:
        with open(f'data/{pref}_rain.csv', 'r', encoding='shift_jis') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 6:
                    try:
                        if int(row[1]) == x and int(row[2]) == y:
                            rain_timeline = []
                            for i, val_str in enumerate(row[3:]):
                                if val_str.strip() == '':
                                    break
                                try:
                                    value = float(val_str)
                                    rain_timeline.append({"ft": i * 3, "value": value})
                                except ValueError:
                                    break
                            result['rain'] = rain_timeline
                            break
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Rain読み込みエラー: {e}")

    # SWI データ
    try:
        with open(f'data/{pref}_swi.csv', 'r', encoding='shift_jis') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 7:
                    # 空行をスキップ
                    if row[0].strip() == '' and row[1].strip() == '':
                        continue
                    try:
                        if int(row[1]) == x and int(row[2]) == y:
                            # 境界値
                            advisary = int(row[3]) if row[3].strip() != '' else 0
                            warning = int(row[4]) if row[4].strip() != '' else 0
                            dosyakei = int(row[5]) if row[5].strip() != '' else 0

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

                            result['swi'] = {
                                'advisary_bound': advisary,
                                'warning_bound': warning,
                                'dosyakei_bound': dosyakei,
                                'timeline': swi_timeline
                            }
                            break
                    except ValueError:
                        continue
    except Exception as e:
        print(f"SWI読み込みエラー: {e}")

    return result

def compare_specific_values():
    """
    境界値一致メッシュで実際の計算値を比較
    """
    print("=== 境界値一致メッシュの実値比較 ===")

    # 滋賀県の境界値一致ケースを分析
    test_cases = [
        {
            'server_meshcode': '52352679',
            'vba_meshes': [
                {'x': 2869, 'y': 4187},  # 28694187
                {'x': 2869, 'y': 4188},  # 28694188
                {'x': 2875, 'y': 4185},  # 28754185
                {'x': 2875, 'y': 4186},  # 28754186
                {'x': 2876, 'y': 4186},  # 28764186
            ]
        }
    ]

    for test_case in test_cases:
        server_meshcode = test_case['server_meshcode']
        print(f"\nサーバーメッシュ: {server_meshcode}")

        # サーバーデータ取得
        server_mesh = get_server_mesh_by_code(server_meshcode)
        if not server_mesh:
            print("  サーバーデータ取得失敗")
            continue

        print(f"  座標: lat={server_mesh['lat']}, lon={server_mesh['lon']}")
        print(f"  境界値: {server_mesh['advisary_bound']}/{server_mesh['warning_bound']}/{server_mesh['dosyakei_bound']}")

        # Rain timeline (最初の6つ)
        server_rain = server_mesh.get('rain_timeline', [])[:6]
        print(f"  サーバーrain: {server_rain}")

        # SWI timeline (最初の6つ)
        server_swi = server_mesh.get('swi_timeline', [])[:6]
        print(f"  サーバーswi: {server_swi}")

        # 対応するVBAメッシュのデータを比較
        print(f"\n  対応VBAメッシュの比較:")
        for vba_mesh in test_case['vba_meshes']:
            x, y = vba_mesh['x'], vba_mesh['y']
            vba_meshcode = f"{x * 10000 + y}"

            print(f"    VBAメッシュ: {vba_meshcode} (x={x}, y={y})")

            vba_data = get_vba_mesh_data('shiga', x, y)

            if vba_data['rain']:
                vba_rain = vba_data['rain'][:6]
                print(f"      VBA rain: {vba_rain}")

                # 値の比較
                rain_match = True
                if len(server_rain) == len(vba_rain):
                    for i in range(len(server_rain)):
                        if abs(server_rain[i]['value'] - vba_rain[i]['value']) > 0.01:
                            rain_match = False
                            break
                else:
                    rain_match = False

                print(f"      Rain一致: {'OK' if rain_match else 'NG'}")

            if vba_data['swi']:
                vba_swi_data = vba_data['swi']
                print(f"      VBA境界値: {vba_swi_data['advisary_bound']}/{vba_swi_data['warning_bound']}/{vba_swi_data['dosyakei_bound']}")

                vba_swi = vba_swi_data['timeline'][:6]
                print(f"      VBA swi: {vba_swi}")

                # 値の比較
                swi_match = True
                if len(server_swi) == len(vba_swi):
                    for i in range(len(server_swi)):
                        if abs(server_swi[i]['value'] - vba_swi[i]['value']) > 0.01:
                            swi_match = False
                            break
                else:
                    swi_match = False

                print(f"      SWI一致: {'OK' if swi_match else 'NG'}")

if __name__ == "__main__":
    compare_specific_values()
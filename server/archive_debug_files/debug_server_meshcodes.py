#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サーバーが使用しているメッシュコードの詳細分析
"""
import requests
import json

def analyze_server_meshcodes():
    """
    サーバーが使用している実際のメッシュコードを分析
    """
    print("=== サーバーメッシュコード詳細分析 ===")

    try:
        url = "http://localhost:5000/api/test-full-soil-rainfall-index"
        response = requests.get(url, timeout=120)
        if response.status_code != 200:
            print(f"Server error: {response.status_code}")
            return

        data = response.json()

        print(f"レスポンス構造:")
        print(f"  prefectures: {list(data.get('prefectures', {}).keys())}")

        all_meshes = []
        for pref_code, pref_data in data['prefectures'].items():
            pref_mesh_count = 0
            sample_meshes = []

            for area in pref_data.get('areas', []):
                for mesh in area.get('meshes', []):
                    all_meshes.append({
                        'pref': pref_code,
                        'area': area.get('name', ''),
                        'meshcode': mesh.get('code', ''),
                        'lat': mesh.get('lat'),
                        'lon': mesh.get('lon'),
                        'advisary_bound': mesh.get('advisary_bound'),
                        'warning_bound': mesh.get('warning_bound'),
                        'dosyakei_bound': mesh.get('dosyakei_bound')
                    })
                    pref_mesh_count += 1

                    # 最初の3つをサンプルとして保存
                    if len(sample_meshes) < 3:
                        sample_meshes.append(mesh)

            print(f"\n{pref_code} ({pref_data.get('name', '')}): {pref_mesh_count} meshes")
            for i, mesh in enumerate(sample_meshes):
                print(f"  サンプル{i+1}: code={mesh.get('code')}, lat={mesh.get('lat')}, lon={mesh.get('lon')}")
                if 'rain_timeline' in mesh and mesh['rain_timeline']:
                    print(f"    rain_timeline (最初の3つ): {mesh['rain_timeline'][:3]}")
                if 'swi_timeline' in mesh and mesh['swi_timeline']:
                    print(f"    swi_timeline (最初の3つ): {mesh['swi_timeline'][:3]}")

        print(f"\n総メッシュ数: {len(all_meshes)}")

        # メッシュコード形式の分析
        print(f"\nメッシュコード形式分析:")
        sample_codes = [mesh['meshcode'] for mesh in all_meshes[:10]]
        for code in sample_codes:
            print(f"  {code} (長さ: {len(code)})")

        # 滋賀県の具体的なメッシュを詳細表示
        shiga_meshes = [mesh for mesh in all_meshes if mesh['pref'] == 'shiga'][:5]
        print(f"\n滋賀県メッシュ詳細 (最初の5つ):")
        for mesh in shiga_meshes:
            print(f"  code={mesh['meshcode']}, area={mesh['area']}")
            print(f"    座標: lat={mesh['lat']}, lon={mesh['lon']}")
            print(f"    境界値: advisary={mesh['advisary_bound']}, warning={mesh['warning_bound']}, dosyakei={mesh['dosyakei_bound']}")

    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    analyze_server_meshcodes()
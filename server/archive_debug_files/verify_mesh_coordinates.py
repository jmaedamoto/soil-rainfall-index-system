#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メッシュ座標とCSVファイルの対応関係を詳細検証
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.data_service import DataService

def main():
    print("=== メッシュ座標とCSV対応関係検証 ===")
    
    data_service = DataService()
    prefectures = data_service.prepare_areas()
    shiga = next((p for p in prefectures if p.code == "shiga"), None)
    
    if not shiga:
        print("滋賀県データが見つかりません")
        return
    
    # 最初のエリアの最初の5メッシュを確認
    first_area = shiga.areas[0]
    print(f"エリア名: {first_area.name}")
    print(f"メッシュ数: {len(first_area.meshes)}")
    
    print("\\n--- メッシュ詳細情報 ---")
    for i, mesh in enumerate(first_area.meshes[:5]):
        print(f"メッシュ{i+1}:")
        print(f"  コード: {mesh.code}")
        print(f"  緯度経度: ({mesh.lat}, {mesh.lon})")
        print(f"  x, y: ({mesh.x}, {mesh.y})")
        
        # meshcode_to_index での計算結果を確認
        calc_x, calc_y = data_service.meshcode_to_index(mesh.code)
        print(f"  計算x, y: ({calc_x}, {calc_y})")
        
        if calc_x != mesh.x or calc_y != mesh.y:
            print(f"  [ERROR] 座標不一致! メッシュ({mesh.x}, {mesh.y}) vs 計算({calc_x}, {calc_y})")
        else:
            print(f"  [OK] 座標一致")
    
    # CSVファイルの期待値を確認
    print("\\n--- CSV期待値確認 ---")
    
    # Rain CSV確認
    rain_expected = {}
    try:
        with open('data/shiga_rain.csv', 'r', encoding='iso-8859-1') as f:
            lines = f.readlines()
        
        for line in lines[:10]:  # 最初の10行
            parts = line.strip().split(',')
            if len(parts) >= 9 and parts[1] and parts[2]:
                try:
                    area_name = parts[0]
                    x = int(parts[1])
                    y = int(parts[2])
                    rain_values = [float(parts[i]) for i in range(3, 9) if parts[i]]
                    print(f"Rain CSV: {area_name} ({x}, {y}) = {rain_values}")
                    rain_expected[(x, y)] = rain_values
                except:
                    continue
    except Exception as e:
        print(f"Rain CSV読み込みエラー: {e}")
    
    # SWI CSV確認
    swi_expected = {}
    try:
        with open('data/shiga_swi.csv', 'r', encoding='iso-8859-1') as f:
            lines = f.readlines()
        
        for line in lines[:10]:  # 最初の10行
            parts = line.strip().split(',')
            if len(parts) >= 4 and parts[1] and parts[2] and parts[3]:
                try:
                    area_name = parts[0]
                    x = int(parts[1])
                    y = int(parts[2])
                    swi_value = float(parts[3])
                    print(f"SWI CSV: {area_name} ({x}, {y}) = {swi_value}")
                    swi_expected[(x, y)] = swi_value
                except:
                    continue
    except Exception as e:
        print(f"SWI CSV読み込みエラー: {e}")
    
    # メッシュとCSVの対応確認
    print("\\n--- メッシュ-CSV対応確認 ---")
    for i, mesh in enumerate(first_area.meshes[:5]):
        mesh_key = (mesh.x, mesh.y)
        rain_data = rain_expected.get(mesh_key)
        swi_data = swi_expected.get(mesh_key)
        
        print(f"メッシュ{i+1} ({mesh.code}): ({mesh.x}, {mesh.y})")
        if rain_data:
            print(f"  Rain期待値: {rain_data}")
        else:
            print(f"  Rain期待値: 見つからず")
        
        if swi_data:
            print(f"  SWI期待値: {swi_data}")
        else:
            print(f"  SWI期待値: 見つからず")

if __name__ == "__main__":
    main()
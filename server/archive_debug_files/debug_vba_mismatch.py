#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBA期待値とサーバー結果の不一致詳細分析
"""
import pandas as pd
import json
import requests
import csv

def read_first_few_meshes_from_vba_csv(filename: str, data_type: str, limit: int = 3):
    """
    VBA CSVファイルから最初の数メッシュのデータを読み取り、詳細表示
    """
    print(f"\n=== {filename} - {data_type} 詳細分析 ===")

    try:
        with open(filename, 'r', encoding='shift_jis') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i >= limit:
                    break

                print(f"Row {i+1}: {len(row)} columns")
                if len(row) >= 10:
                    print(f"  First 10 columns: {row[:10]}")
                    if len(row) > 10:
                        print(f"  Remaining columns sample: {row[10:15]}...")
                else:
                    print(f"  All columns: {row}")

                if len(row) >= 3:
                    try:
                        if data_type == "rain":
                            area_name = row[0]
                            x = int(row[1])
                            y = int(row[2])
                            meshcode = str(x * 10000 + y)
                            rain_values = []
                            for j, val_str in enumerate(row[3:]):
                                if val_str.strip() == '':
                                    break
                                try:
                                    value = float(val_str)
                                    rain_values.append({"ft": j * 3, "value": value})
                                    if j >= 5:  # 最初の6つだけ表示
                                        break
                                except ValueError:
                                    break

                            print(f"  解析結果: meshcode={meshcode}, rain_timeline={rain_values}")

                        elif data_type == "swi":
                            if row[0].strip() == '' and row[1].strip() == '':
                                print(f"  空行をスキップ")
                                continue

                            area_name = row[0]
                            x = int(row[1])
                            y = int(row[2])
                            meshcode = str(x * 10000 + y)

                            # 境界値データ
                            advisary = int(row[3]) if row[3].strip() != '' else 0
                            warning = int(row[4]) if row[4].strip() != '' else 0
                            dosyakei = int(row[5]) if row[5].strip() != '' else 0

                            swi_values = []
                            for j, val_str in enumerate(row[6:]):
                                if val_str.strip() == '':
                                    break
                                try:
                                    value = float(val_str)
                                    swi_values.append({"ft": j * 3, "value": value})
                                    if j >= 5:  # 最初の6つだけ表示
                                        break
                                except ValueError:
                                    break

                            print(f"  解析結果: meshcode={meshcode}")
                            print(f"    境界値: advisary={advisary}, warning={warning}, dosyakei={dosyakei}")
                            print(f"    swi_timeline={swi_values}")

                    except Exception as e:
                        print(f"  解析エラー: {e}")

    except Exception as e:
        print(f"ファイル読み込みエラー: {e}")

def get_server_mesh_details(meshcodes: list):
    """
    指定されたメッシュコードのサーバー結果を取得
    """
    try:
        url = "http://localhost:5000/api/test-full-soil-rainfall-index"
        response = requests.get(url, timeout=120)
        if response.status_code != 200:
            print(f"Server error: {response.status_code}")
            return {}

        data = response.json()
        server_meshes = {}

        if 'prefectures' in data:
            for pref_code, pref_data in data['prefectures'].items():
                if 'areas' in pref_data:
                    for area in pref_data['areas']:
                        if 'meshes' in area:
                            for mesh in area['meshes']:
                                meshcode = mesh.get('code', '')
                                if meshcode in meshcodes:
                                    server_meshes[meshcode] = mesh

        return server_meshes

    except Exception as e:
        print(f"サーバー結果取得エラー: {e}")
        return {}

def compare_specific_meshes():
    """
    具体的なメッシュでVBAとサーバー結果を詳細比較
    """
    print("=== VBAとサーバー結果の詳細比較分析 ===")

    # 1. VBA CSVファイルから最初の数メッシュを詳細分析
    print("\n1. VBA CSVファイル詳細分析")
    read_first_few_meshes_from_vba_csv('data/shiga_rain.csv', 'rain', 3)
    read_first_few_meshes_from_vba_csv('data/shiga_swi.csv', 'swi', 3)

    # 2. 特定メッシュのサーバー結果を取得
    print("\n2. サーバー結果詳細分析")
    target_meshcodes = ["28694187", "28694188", "28714185"]  # 最初の3メッシュ
    server_results = get_server_mesh_details(target_meshcodes)

    for meshcode in target_meshcodes:
        if meshcode in server_results:
            mesh = server_results[meshcode]
            print(f"\n  メッシュコード: {meshcode}")
            print(f"    座標: lat={mesh.get('lat')}, lon={mesh.get('lon')}")
            print(f"    境界値: advisary={mesh.get('advisary_bound')}, warning={mesh.get('warning_bound')}, dosyakei={mesh.get('dosyakei_bound')}")

            rain_timeline = mesh.get('rain_timeline', [])
            if rain_timeline:
                print(f"    rain_timeline (最初の6つ): {rain_timeline[:6]}")

            swi_timeline = mesh.get('swi_timeline', [])
            if swi_timeline:
                print(f"    swi_timeline (最初の6つ): {swi_timeline[:6]}")
        else:
            print(f"\n  メッシュコード: {meshcode} - サーバー結果に見つからず")

if __name__ == "__main__":
    compare_specific_meshes()
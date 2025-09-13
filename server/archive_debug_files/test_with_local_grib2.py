#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ローカルのGRIB2ファイル（2023年6月2日）を使用してサーバー処理をテスト
VBA CSV出力と比較
"""
import sys
import os

# 現在のディレクトリをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.main_service import MainService
import csv
import json

def test_local_grib2_processing():
    """
    ローカルのGRIB2ファイルでサーバー処理をテスト
    """
    print("=== ローカルGRIB2ファイルでサーバー処理テスト ===")

    # ローカルファイルパス
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"

    print(f"SWIファイル: {swi_file}")
    print(f"ガイダンスファイル: {guidance_file}")

    # ファイル存在確認
    if not os.path.exists(swi_file):
        print(f"SWIファイルが存在しません: {swi_file}")
        return None

    if not os.path.exists(guidance_file):
        print(f"ガイダンスファイルが存在しません: {guidance_file}")
        return None

    try:
        print("サーバー処理実行中...")

        # MainServiceを使用してローカルファイル処理
        main_service = MainService()
        result = main_service.main_process_from_files(swi_file, guidance_file)

        if result.get('status') == 'success':
            print("サーバー処理成功")
            return result
        else:
            print(f"サーバー処理エラー: {result.get('message', 'Unknown error')}")
            return None

    except Exception as e:
        print(f"処理エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_vba_csv_first_row():
    """
    VBA CSVの最初の数行を読み込んでサンプル比較
    """
    print("\n=== VBA CSV サンプルデータ読み込み ===")

    prefectures = ['shiga', 'kyoto', 'osaka', 'hyogo', 'nara', 'wakayama']
    vba_samples = {}

    for pref in prefectures:
        vba_samples[pref] = {'rain': [], 'swi': []}

        # Rain CSV読み込み（最初の3行）
        try:
            with open(f'data/{pref}_rain.csv', 'r', encoding='shift_jis') as f:
                reader = csv.reader(f)
                rows = list(reader)

                print(f"{pref}_rain.csv: {len(rows)} 行")
                print(f"  1行目（ヘッダー）: {rows[0][:5]}...")  # 最初の5列

                # 2行目以降の最初の3つをサンプルとして取得
                for i, row in enumerate(rows[1:4]):  # 2-4行目
                    if len(row) >= 6:
                        try:
                            area_name = row[0].strip()
                            x = int(row[1])
                            y = int(row[2])

                            # 雨量データ（最初の6つ）
                            rain_values = []
                            for j, val_str in enumerate(row[3:9]):  # FT=0,3,6,9,12,15
                                if val_str.strip() != '':
                                    rain_values.append({"ft": j * 3, "value": float(val_str)})

                            vba_samples[pref]['rain'].append({
                                'row_index': i + 2,  # 実際の行番号
                                'area_name': area_name,
                                'x': x,
                                'y': y,
                                'rain_timeline': rain_values
                            })

                            print(f"    行{i+2}: {area_name} x={x} y={y} rain={rain_values}")

                        except (ValueError, IndexError) as e:
                            print(f"    行{i+2}: 解析エラー {e}")
                            continue

        except Exception as e:
            print(f"Error reading {pref}_rain.csv: {e}")

        # SWI CSV読み込み（最初の3行）
        try:
            with open(f'data/{pref}_swi.csv', 'r', encoding='shift_jis') as f:
                reader = csv.reader(f)
                rows = list(reader)

                print(f"{pref}_swi.csv: {len(rows)} 行")
                print(f"  1行目（ヘッダー）: {rows[0][:7]}...")  # 最初の7列

                # 2行目以降の最初の3つをサンプルとして取得
                for i, row in enumerate(rows[1:4]):  # 2-4行目
                    if len(row) >= 10:
                        try:
                            area_name = row[0].strip()
                            x = int(row[1])
                            y = int(row[2])

                            # 境界値
                            advisary = int(row[3]) if row[3].strip() != '' else 0
                            warning = int(row[4]) if row[4].strip() != '' else 0
                            dosyakei = int(row[5]) if row[5].strip() != '' else 0

                            # SWIデータ（最初の6つ）
                            swi_values = []
                            for j, val_str in enumerate(row[6:12]):  # FT=0,3,6,9,12,15
                                if val_str.strip() != '':
                                    swi_values.append({"ft": j * 3, "value": float(val_str)})

                            vba_samples[pref]['swi'].append({
                                'row_index': i + 2,  # 実際の行番号
                                'area_name': area_name,
                                'x': x,
                                'y': y,
                                'advisary_bound': advisary,
                                'warning_bound': warning,
                                'dosyakei_bound': dosyakei,
                                'swi_timeline': swi_values
                            })

                            print(f"    行{i+2}: {area_name} x={x} y={y} 境界={advisary}/{warning}/{dosyakei} swi={swi_values}")

                        except (ValueError, IndexError) as e:
                            print(f"    行{i+2}: 解析エラー {e}")
                            continue

        except Exception as e:
            print(f"Error reading {pref}_swi.csv: {e}")

        print()

    return vba_samples

def compare_server_result_with_vba_samples(server_result, vba_samples):
    """
    サーバー結果とVBAサンプルの詳細比較
    """
    print("=== サーバー結果 vs VBAサンプル 詳細比較 ===")

    if not server_result or 'prefectures' not in server_result:
        print("サーバー結果が無効です")
        return

    # 滋賀県を例にして詳細比較
    pref_code = 'shiga'
    if pref_code not in server_result['prefectures']:
        print(f"{pref_code}のデータがサーバー結果にありません")
        return

    server_pref = server_result['prefectures'][pref_code]
    vba_pref_samples = vba_samples.get(pref_code, {})

    print(f"\n{pref_code}県 詳細比較:")
    print(f"  サーバーエリア数: {len(server_pref.get('areas', []))}")

    # サーバーの最初のエリア・メッシュを詳細表示
    if server_pref.get('areas'):
        first_area = server_pref['areas'][0]
        area_name = first_area.get('name', '')
        print(f"  最初のエリア: {area_name}")

        if first_area.get('meshes'):
            for i, mesh in enumerate(first_area['meshes'][:3]):  # 最初の3メッシュ
                print(f"    メッシュ{i+1}: {mesh.get('code', 'N/A')}")
                print(f"      境界値: {mesh.get('advisary_bound')}/{mesh.get('warning_bound')}/{mesh.get('dosyakei_bound')}")

                rain_timeline = mesh.get('rain_timeline', [])
                print(f"      Rain: {rain_timeline[:3] if rain_timeline else 'なし'}")

                swi_timeline = mesh.get('swi_timeline', [])
                print(f"      SWI: {swi_timeline[:3] if swi_timeline else 'なし'}")

    # VBAサンプルと照合
    print(f"\n  VBA {pref_code} サンプル:")
    for rain_sample in vba_pref_samples.get('rain', [])[:2]:
        print(f"    Rain行{rain_sample['row_index']}: {rain_sample['area_name']} x={rain_sample['x']} y={rain_sample['y']}")
        print(f"      値: {rain_sample['rain_timeline']}")

    for swi_sample in vba_pref_samples.get('swi', [])[:2]:
        print(f"    SWI行{swi_sample['row_index']}: {swi_sample['area_name']} x={swi_sample['x']} y={swi_sample['y']}")
        print(f"      境界値: {swi_sample['advisary_bound']}/{swi_sample['warning_bound']}/{swi_sample['dosyakei_bound']}")
        print(f"      値: {swi_sample['swi_timeline']}")

def main():
    """
    メイン処理
    """
    # 1. ローカルGRIB2ファイルでサーバー処理
    server_result = test_local_grib2_processing()

    if not server_result:
        print("サーバー処理に失敗したため、比較を中断します")
        return

    # 2. VBA CSVサンプルデータ読み込み
    vba_samples = load_vba_csv_first_row()

    # 3. サーバー結果とVBAサンプルの比較
    compare_server_result_with_vba_samples(server_result, vba_samples)

    # 4. 結果をファイルに保存
    with open('server_vs_vba_comparison.json', 'w', encoding='utf-8') as f:
        comparison_data = {
            'server_result': server_result,
            'vba_samples': vba_samples
        }
        json.dump(comparison_data, f, ensure_ascii=False, indent=2)

    print("\n比較結果を server_vs_vba_comparison.json に保存しました")

if __name__ == "__main__":
    main()
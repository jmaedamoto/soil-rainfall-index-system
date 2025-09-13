#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBA X,Y座標とGRIB2データの正しいマッピングを修正
"""
import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.main_service import MainService
from services.calculation_service import CalculationService

def analyze_vba_coordinate_system():
    """
    VBA X,Y座標システムの解析とGRIB2データとの正しい対応関係を確立
    """
    print("=== VBA座標システム解析 ===")

    # GRIB2データ取得
    main_service = MainService()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"

    base_info, swi_grib2 = main_service.grib2_service.unpack_swi_grib2_from_file(swi_file)
    _, guidance_grib2 = main_service.grib2_service.unpack_guidance_grib2_from_file(guidance_file)

    print(f"SWI GRIB2 grid: {base_info.x_num} x {base_info.y_num}")
    print(f"Guidance GRIB2 grid: {guidance_grib2['base_info'].x_num} x {guidance_grib2['base_info'].y_num}")

    # VBAの既知データを読み込み
    test_cases = []
    with open('data/shiga_swi.csv', 'r', encoding='shift_jis') as f:
        reader = csv.reader(f)
        rows = list(reader)

        # 2-4行目のテストケース
        for row in rows[1:4]:
            if len(row) >= 10:
                area = row[0].strip()
                x = int(row[1])
                y = int(row[2])
                expected_swi = float(row[6])  # FT=0のSWI値

                test_cases.append({
                    'area': area,
                    'x': x,
                    'y': y,
                    'expected_swi': expected_swi
                })

    print(f"\nテストケース数: {len(test_cases)}")

    # 各種マッピング方式をテスト
    calc_service = CalculationService()

    for i, case in enumerate(test_cases):
        print(f"\n=== テストケース {i+1}: {case['area']} x={case['x']} y={case['y']} ===")
        print(f"VBA期待SWI値: {case['expected_swi']}")

        # 方式1: VBA X,Yを直接GRIB2グリッドインデックスとして使用
        print(f"\n方式1: 直接グリッドインデックス使用")
        try:
            # SWIグリッド: 2560 x 3360
            # VBA X,Yが2800-2900, 4100-4200の範囲なので、これがグリッド座標かもしれない
            swi_index_direct = (case['y'] - 1) * base_info.x_num + (case['x'] - 1)
            if 0 <= swi_index_direct < len(swi_grib2['swi']):
                swi_raw = swi_grib2['swi'][swi_index_direct]
                swi_value = swi_raw / 10
                print(f"  SWIインデックス: {swi_index_direct}")
                print(f"  SWI Raw値: {swi_raw} → {swi_value}")
                print(f"  差分: {abs(swi_value - case['expected_swi']):.4f}")
            else:
                print(f"  ERROR: インデックス {swi_index_direct} が範囲外")
        except:
            print(f"  ERROR: 方式1計算エラー")

        # 方式2: VBA座標を相対座標として処理（関西地方の範囲で調整）
        print(f"\n方式2: 関西地方相対座標変換")
        try:
            # 関西地方の推定範囲
            # 緯度: 33-36度 → GRIB2グリッド上での位置を計算
            # 経度: 134-137度

            # VBA X,Y座標から緯度経度を逆算
            # 関西地方のGRIB2データ範囲を推定
            kansai_lat_start = 33.0
            kansai_lat_end = 36.0
            kansai_lon_start = 134.0
            kansai_lon_end = 137.0

            # VBA座標の範囲を推定
            vba_x_min, vba_x_max = 2800, 2900  # 概算
            vba_y_min, vba_y_max = 4100, 4300  # 概算

            # VBA座標を0-1の相対座標に変換
            rel_x = (case['x'] - vba_x_min) / (vba_x_max - vba_x_min)
            rel_y = (case['y'] - vba_y_min) / (vba_y_max - vba_y_min)

            # 相対座標を関西地方の緯度経度に変換
            est_lat = kansai_lat_start + rel_y * (kansai_lat_end - kansai_lat_start)
            est_lon = kansai_lon_start + rel_x * (kansai_lon_end - kansai_lon_start)

            print(f"  推定座標: lat={est_lat:.6f}, lon={est_lon:.6f}")

            # この推定座標でget_data_num()を使用
            swi_index_calc = calc_service.get_data_num(est_lat, est_lon, base_info)
            if 1 <= swi_index_calc <= len(swi_grib2['swi']):
                swi_raw = swi_grib2['swi'][swi_index_calc - 1]
                swi_value = swi_raw / 10
                print(f"  SWIインデックス: {swi_index_calc - 1}")
                print(f"  SWI Raw値: {swi_raw} → {swi_value}")
                print(f"  差分: {abs(swi_value - case['expected_swi']):.4f}")
            else:
                print(f"  ERROR: インデックス {swi_index_calc} が範囲外")
        except Exception as e:
            print(f"  ERROR: 方式2計算エラー: {e}")

        # 方式3: VBA X,YをGRIB2の標準地域グリッドとして解釈
        print(f"\n方式3: 標準地域グリッド解釈")
        try:
            # VBA座標が実際のJMA標準地域メッシュ座標である可能性
            # X,Y -> 緯度経度の標準変換式を適用

            # 標準地域メッシュの計算方式
            # X座標 (東西方向): 100度からの距離を1.5分単位で表現
            # Y座標 (南北方向): 基準緯度からの距離を1分単位で表現

            mesh_lat = case['y'] / 60.0  # 1分 = 1/60度単位から度単位へ
            mesh_lon = 100.0 + case['x'] * 1.5 / 60.0  # 1.5分単位から度単位へ

            print(f"  標準メッシュ座標: lat={mesh_lat:.6f}, lon={mesh_lon:.6f}")

            # この座標でget_data_num()を使用
            swi_index_mesh = calc_service.get_data_num(mesh_lat, mesh_lon, base_info)
            if 1 <= swi_index_mesh <= len(swi_grib2['swi']):
                swi_raw = swi_grib2['swi'][swi_index_mesh - 1]
                swi_value = swi_raw / 10
                print(f"  SWIインデックス: {swi_index_mesh - 1}")
                print(f"  SWI Raw値: {swi_raw} → {swi_value}")
                print(f"  差分: {abs(swi_value - case['expected_swi']):.4f}")
            else:
                print(f"  ERROR: インデックス {swi_index_mesh} が範囲外")
        except Exception as e:
            print(f"  ERROR: 方式3計算エラー: {e}")

        # 方式4: 逆算法 - 期待値からGRIB2データを検索
        print(f"\n方式4: 逆算法（期待値検索）")
        try:
            expected_raw = case['expected_swi'] * 10
            tolerance = 5  # ±0.5の許容範囲

            matches = []
            for idx, raw_val in enumerate(swi_grib2['swi']):
                if abs(raw_val - expected_raw) <= tolerance:
                    matches.append((idx, raw_val))

            print(f"  期待Raw値: {expected_raw}")
            print(f"  一致候補数: {len(matches)}")

            if matches:
                for match_idx, match_val in matches[:3]:  # 最初の3つを表示
                    print(f"    インデックス {match_idx}: Raw={match_val} → {match_val/10}")

                    # このインデックスから逆算してVBA座標との関係を推測
                    y_calc = match_idx // base_info.x_num + 1
                    x_calc = match_idx % base_info.x_num + 1
                    print(f"    逆算座標: x={x_calc}, y={y_calc}")
                    print(f"    VBA座標との差: dx={x_calc - case['x']}, dy={y_calc - case['y']}")

        except Exception as e:
            print(f"  ERROR: 方式4計算エラー: {e}")

def main():
    """
    メイン処理
    """
    analyze_vba_coordinate_system()

if __name__ == "__main__":
    main()
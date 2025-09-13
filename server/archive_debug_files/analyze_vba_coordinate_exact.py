#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VBA座標システムの正確な解析とGRIB2との直接マッピング
"""
import sys
import os
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.main_service import MainService

def analyze_vba_coordinate_exact():
    """
    VBA X,Y座標とGRIB2データの正確なマッピングを分析
    """
    print("=== VBA座標システム正確解析 ===")

    # GRIB2データ取得
    main_service = MainService()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"

    base_info, swi_grib2 = main_service.grib2_service.unpack_swi_grib2_from_file(swi_file)
    _, guidance_grib2 = main_service.grib2_service.unpack_guidance_grib2_from_file(guidance_file)

    print(f"SWI GRIB2: {base_info.x_num} x {base_info.y_num} = {base_info.grid_num}")
    print(f"Guidance GRIB2: {guidance_grib2['base_info'].x_num} x {guidance_grib2['base_info'].y_num}")

    # VBA座標範囲の正確な分析
    print(f"\nSWI GRIB2詳細:")
    print(f"  開始: lat={base_info.s_lat/1000000:.6f}, lon={base_info.s_lon/1000000:.6f}")
    print(f"  終了: lat={base_info.e_lat/1000000:.6f}, lon={base_info.e_lon/1000000:.6f}")
    print(f"  解像度: lat={base_info.d_lat/1000000:.6f}, lon={base_info.d_lon/1000000:.6f}")

    guidance_base = guidance_grib2['base_info']
    print(f"\nGuidance GRIB2詳細:")
    print(f"  開始: lat={guidance_base.s_lat/1000000:.6f}, lon={guidance_base.s_lon/1000000:.6f}")
    print(f"  終了: lat={guidance_base.e_lat/1000000:.6f}, lon={guidance_base.e_lon/1000000:.6f}")
    print(f"  解像度: lat={guidance_base.d_lat/1000000:.6f}, lon={guidance_base.d_lon/1000000:.6f}")

    # VBA CSVから座標範囲を分析
    print(f"\n=== VBA座標範囲分析 ===")

    all_vba_coords = []
    expected_values = {}

    for pref in ['shiga', 'kyoto', 'osaka', 'hyogo', 'nara', 'wakayama']:
        swi_file = f'data/{pref}_swi.csv'
        if os.path.exists(swi_file):
            try:
                with open(swi_file, 'r', encoding='shift_jis') as f:
                    reader = csv.reader(f)
                    rows = list(reader)

                    for row in rows[1:]:  # skip header
                        if len(row) >= 7:
                            try:
                                area = row[0].strip()
                                vba_x = int(row[1])
                                vba_y = int(row[2])
                                advisary = int(row[3]) if row[3].strip() != '' else 9999
                                warning = int(row[4]) if row[4].strip() != '' else 9999
                                dosyakei = int(row[5]) if row[5].strip() != '' else 9999
                                swi_ft0 = float(row[6])

                                all_vba_coords.append((vba_x, vba_y))

                                # 特定の座標のデータを保存
                                if area == "大津市南部" and vba_x == 2869 and vba_y == 4187:
                                    expected_values[(vba_x, vba_y)] = {
                                        'area': area,
                                        'advisary': advisary,
                                        'warning': warning,
                                        'dosyakei': dosyakei,
                                        'swi_ft0': swi_ft0
                                    }

                            except (ValueError, IndexError):
                                continue
            except Exception as e:
                print(f"Error reading {swi_file}: {e}")

    if all_vba_coords:
        vba_x_values = [coord[0] for coord in all_vba_coords]
        vba_y_values = [coord[1] for coord in all_vba_coords]

        print(f"VBA X範囲: {min(vba_x_values)} - {max(vba_x_values)}")
        print(f"VBA Y範囲: {min(vba_y_values)} - {max(vba_y_values)}")
        print(f"総VBA座標数: {len(all_vba_coords)}")

    # 特定の座標での直接マッピングテスト
    print(f"\n=== 直接マッピングテスト ===")

    for (vba_x, vba_y), expected in expected_values.items():
        print(f"\nテスト: VBA座標({vba_x}, {vba_y}) - {expected['area']}")
        print(f"  期待SWI値: {expected['swi_ft0']}")

        # 方法1: VBA座標を直接GRIB2インデックスとして使用
        print(f"  方法1: 直接インデックス")
        try:
            # SWI: VBA Y,X をそのまま配列インデックスとして使用
            swi_index_direct = (vba_y - 1) * base_info.x_num + (vba_x - 1)
            if 0 <= swi_index_direct < len(swi_grib2['swi']):
                swi_raw = swi_grib2['swi'][swi_index_direct]
                swi_value = swi_raw / 10
                print(f"    SWI直接: index={swi_index_direct}, raw={swi_raw}, value={swi_value}")
                print(f"    差分: {abs(swi_value - expected['swi_ft0']):.4f}")
            else:
                print(f"    SWI直接: index={swi_index_direct} 範囲外")
        except Exception as e:
            print(f"    SWI直接エラー: {e}")

        # 方法2: VBA座標オフセット調整
        print(f"  方法2: オフセット調整")
        for x_offset in [-2800, -2000, -1000, 0]:
            for y_offset in [-4000, -3000, -2000, -1000, 0]:
                try:
                    adj_x = vba_x + x_offset
                    adj_y = vba_y + y_offset

                    if adj_x >= 0 and adj_y >= 0:
                        swi_index_adj = adj_y * base_info.x_num + adj_x
                        if 0 <= swi_index_adj < len(swi_grib2['swi']):
                            swi_raw = swi_grib2['swi'][swi_index_adj]
                            swi_value = swi_raw / 10
                            diff = abs(swi_value - expected['swi_ft0'])

                            if diff < 1.0:  # 1.0以下の差分のみ表示
                                print(f"    オフセット({x_offset}, {y_offset}): index={swi_index_adj}, value={swi_value}, 差分={diff:.4f}")

                except Exception:
                    continue

        # 方法3: 既存のget_data_num関数での逆算確認
        print(f"  方法3: 期待値からの逆算")
        expected_raw = expected['swi_ft0'] * 10
        for idx, raw_val in enumerate(swi_grib2['swi']):
            if abs(raw_val - expected_raw) <= 5:  # ±0.5の許容範囲
                y_calc = idx // base_info.x_num
                x_calc = idx % base_info.x_num
                print(f"    一致: index={idx}, raw={raw_val}, calc_pos=({x_calc}, {y_calc})")
                print(f"    VBA座標との差: dx={x_calc - vba_x}, dy={y_calc - vba_y}")

                # 最初の一致のみ表示
                break

def main():
    analyze_vba_coordinate_exact()

if __name__ == "__main__":
    main()
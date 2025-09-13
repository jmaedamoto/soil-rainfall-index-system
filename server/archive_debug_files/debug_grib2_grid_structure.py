#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIB2グリッド構造の詳細分析
VBA座標とGRIB2グリッドの関係を正確に把握
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.main_service import MainService

def analyze_grib2_grid_structure():
    """GRIB2データのグリッド構造を詳しく分析"""
    print("=== GRIB2グリッド構造分析 ===")

    main_service = MainService()
    swi_file = "data/Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20230602000000_rmax00.bin"

    # SWI GRIB2解析
    print("=== SWI GRIB2データ解析 ===")
    base_info, swi_grib2 = main_service.grib2_service.unpack_swi_grib2_from_file(swi_file)

    print(f"グリッド数: x={base_info.x_num}, y={base_info.y_num}, total={base_info.grid_num}")
    print(f"開始座標: lat={base_info.s_lat/1000000:.6f}, lon={base_info.s_lon/1000000:.6f}")
    print(f"終了座標: lat={base_info.e_lat/1000000:.6f}, lon={base_info.e_lon/1000000:.6f}")
    print(f"解像度: lat={base_info.d_lat/1000000:.6f}, lon={base_info.d_lon/1000000:.6f}")

    # 緯度経度範囲の計算
    lat_range = (base_info.e_lat - base_info.s_lat) / 1000000
    lon_range = (base_info.e_lon - base_info.s_lon) / 1000000
    print(f"緯度範囲: {lat_range:.6f}度 ({base_info.y_num}グリッド)")
    print(f"経度範囲: {lon_range:.6f}度 ({base_info.x_num}グリッド)")

    # データ配列サイズ
    print(f"SWI配列サイズ: {len(swi_grib2['swi'])}")
    print(f"first_tunk配列サイズ: {len(swi_grib2['first_tunk'])}")
    print(f"second_tunk配列サイズ: {len(swi_grib2['second_tunk'])}")

    # Guidance GRIB2解析
    print("\n=== Guidance GRIB2データ解析 ===")
    _, guidance_grib2 = main_service.grib2_service.unpack_guidance_grib2_from_file(guidance_file)
    guidance_base = guidance_grib2['base_info']

    print(f"グリッド数: x={guidance_base.x_num}, y={guidance_base.y_num}, total={guidance_base.grid_num}")
    print(f"開始座標: lat={guidance_base.s_lat/1000000:.6f}, lon={guidance_base.s_lon/1000000:.6f}")
    print(f"終了座標: lat={guidance_base.e_lat/1000000:.6f}, lon={guidance_base.e_lon/1000000:.6f}")
    print(f"解像度: lat={guidance_base.d_lat/1000000:.6f}, lon={guidance_base.d_lon/1000000:.6f}")
    print(f"データ系列数: {len(guidance_grib2['data'])}")

    if len(guidance_grib2['data']) > 0:
        first_data = guidance_grib2['data'][0]
        print(f"最初のデータ系列サイズ: {len(first_data['value'])}")

    # 関西地方の座標範囲確認
    print("\n=== 関西地方座標範囲確認 ===")
    kansai_coords = [
        ("大阪", 34.6937, 135.5023),
        ("京都", 35.0116, 135.7681),
        ("神戸", 34.6901, 135.1956),
        ("奈良", 34.6851, 135.8048),
        ("大津", 35.0044, 135.8686),
        ("和歌山", 34.2261, 135.1675)
    ]

    for name, lat, lon in kansai_coords:
        # get_data_num関数でのインデックス計算
        y = int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
        x = int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
        index = (y - 1) * base_info.x_num + x

        print(f"{name}: lat={lat:.4f}, lon={lon:.4f} -> x={x}, y={y}, index={index}")

        # インデックス有効性チェック
        if 1 <= index <= base_info.grid_num:
            print(f"  -> 有効なインデックス（範囲内）")
        else:
            print(f"  -> 無効なインデックス（範囲外: 1-{base_info.grid_num}）")

    # VBA座標例での計算
    print("\n=== VBA座標例での計算確認 ===")
    vba_coords = [
        (2869, 4187),  # VBAの例
        (2874, 4187),
        (2880, 4196)
    ]

    for vba_x, vba_y in vba_coords:
        # VBA座標をそのまま使った場合のインデックス
        index_direct = (vba_y - 1) * base_info.x_num + vba_x

        print(f"VBA座標({vba_x}, {vba_y})")
        print(f"  直接使用: index={index_direct}")
        print(f"  有効範囲: 1-{base_info.grid_num}")
        print(f"  結果: {'範囲内' if 1 <= index_direct <= base_info.grid_num else '範囲外'}")

    # 正しいマッピング方法の検討
    print("\n=== 正しいマッピング方法の検討 ===")
    print("問題: VBA座標(2869, 4187)は直接GRIB2グリッド座標として使用できない")
    print("解決策を検討する必要がある:")
    print("1. VBA座標は実際のGRIB2グリッド座標ではない可能性")
    print("2. VBA座標は独自の座標系を使用している可能性")
    print("3. Module.basでの座標変換ロジックの詳細確認が必要")

if __name__ == "__main__":
    analyze_grib2_grid_structure()
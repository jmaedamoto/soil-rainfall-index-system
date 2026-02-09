# -*- coding: utf-8 -*-
"""
URL設定機能のテスト
"""
from datetime import datetime
from src.config.config_service import ConfigService


def test_url_building():
    """URL構築機能のテスト"""
    print("=== URL構築機能テスト ===\n")

    # ConfigService初期化
    config = ConfigService()

    # テスト用の初期時刻
    test_time = datetime(2025, 10, 28, 12, 0, 0)

    # 設定値の取得
    print("【設定値確認】")
    grib2_config = config.get_grib2_config()
    print(f"Base URL: {grib2_config['base_url']}")
    print(f"SWI Path: {grib2_config['swi_path']}")
    print(f"Guidance Path: {grib2_config['guidance_path']}")
    print()

    # SWI URL構築
    print("【SWI URL構築】")
    swi_url = config.build_swi_url(test_time)
    print(f"初期時刻: {test_time}")
    print(f"SWI URL: {swi_url}")
    print()

    # ガイダンスURL構築（0,6,12,18時 → rmax00）
    print("【ガイダンスURL構築（12時 → rmax00）】")
    guidance_url = config.build_guidance_url(test_time)
    print(f"初期時刻: {test_time}")
    print(f"Guidance URL: {guidance_url}")
    print()

    # ガイダンスURL構築（3,9,15,21時 → rmax03）
    test_time_odd = datetime(2025, 10, 28, 15, 0, 0)
    print("【ガイダンスURL構築（15時 → rmax03）】")
    guidance_url_odd = config.build_guidance_url(test_time_odd)
    print(f"初期時刻: {test_time_odd}")
    print(f"Guidance URL: {guidance_url_odd}")
    print()

    # 期待値との比較
    print("【検証】")
    expected_swi = "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/2025/10/28/Z__C_RJTD_20251028120000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    expected_guidance = "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/2025/10/28/guid_msm_grib2_20251028120000_rmax00.bin"
    expected_guidance_odd = "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/2025/10/28/guid_msm_grib2_20251028150000_rmax03.bin"

    print(f"SWI URL一致: {swi_url == expected_swi}")
    print(f"Guidance URL一致（12時）: {guidance_url == expected_guidance}")
    print(f"Guidance URL一致（15時）: {guidance_url_odd == expected_guidance_odd}")
    print()

    if swi_url == expected_swi and guidance_url == expected_guidance and guidance_url_odd == expected_guidance_odd:
        print("✅ 全てのテスト成功！")
    else:
        print("❌ テスト失敗")


if __name__ == '__main__':
    test_url_building()

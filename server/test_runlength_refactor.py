# -*- coding: utf-8 -*-
"""
ランレングス展開リファクタリング検証スクリプト
リファクタリング前後で完全に同一の結果を返すことを検証
"""
import json
import sys
import os

# パス追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from services.grib2_service import Grib2Service


def generate_baseline_data():
    """現在の実装で基準データを生成"""
    print("=" * 60)
    print("基準データ生成開始（リファクタリング前の実装）")
    print("=" * 60)

    service = Grib2Service()

    # テストファイルパス
    swi_file = "data/Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20250101000000_rmax00.bin"

    baseline_data = {}

    # SWIファイル解析
    print(f"\nSWIファイル解析: {swi_file}")
    if os.path.exists(swi_file):
        try:
            base_info, swi_result = service.unpack_swi_grib2_from_file(swi_file)
            baseline_data['swi'] = {
                'base_info': {
                    'initial_date': base_info.initial_date.isoformat(),
                    'grid_num': base_info.grid_num,
                    'x_num': base_info.x_num,
                    'y_num': base_info.y_num,
                },
                'swi_data': swi_result['swi'][:1000],  # 最初の1000個をサンプル
                'swi_data_length': len(swi_result['swi']),
            }
            print(f"  OK SWIデータ数: {len(swi_result['swi'])}")
            print(f"  OK 先頭10個: {swi_result['swi'][:10]}")
        except Exception as e:
            print(f"  NG SWIファイル解析エラー: {e}")
            baseline_data['swi'] = None
    else:
        print(f"  NG ファイルが存在しません")
        baseline_data['swi'] = None

    # ガイダンスファイル解析
    print(f"\nガイダンスファイル解析: {guidance_file}")
    if os.path.exists(guidance_file):
        try:
            base_info, guidance_result = service.unpack_guidance_grib2_from_file(guidance_file)

            # 1時間・3時間雨量データをサンプリング
            data_1h = guidance_result['data_1h']
            data_3h = guidance_result['data_3h']

            baseline_data['guidance'] = {
                'base_info': {
                    'initial_date': base_info.initial_date.isoformat(),
                    'grid_num': base_info.grid_num,
                },
                'data_1h_count': len(data_1h),
                'data_3h_count': len(data_3h),
            }

            # 各時系列の最初の500個をサンプル
            for i, item in enumerate(data_1h):
                baseline_data['guidance'][f'data_1h_ft{item["ft"]}_sample'] = item['value'][:500]
                baseline_data['guidance'][f'data_1h_ft{item["ft"]}_length'] = len(item['value'])

            for i, item in enumerate(data_3h):
                baseline_data['guidance'][f'data_3h_ft{item["ft"]}_sample'] = item['value'][:500]
                baseline_data['guidance'][f'data_3h_ft{item["ft"]}_length'] = len(item['value'])

            print(f"  OK 1時間雨量データセット数: {len(data_1h)}")
            print(f"  OK 3時間雨量データセット数: {len(data_3h)}")

        except Exception as e:
            print(f"  NG ガイダンスファイル解析エラー: {e}")
            baseline_data['guidance'] = None
    else:
        print(f"  NG ファイルが存在しません")
        baseline_data['guidance'] = None

    # JSON保存
    output_file = "baseline_runlength_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(baseline_data, f, indent=2, ensure_ascii=False)

    print(f"\n基準データ保存完了: {output_file}")
    print(f"ファイルサイズ: {os.path.getsize(output_file):,} bytes")

    return baseline_data


if __name__ == "__main__":
    baseline_data = generate_baseline_data()
    print("\n基準データ生成完了")

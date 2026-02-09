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


def compare_data():
    """基準データとリファクタリング後のデータを比較"""
    print("=" * 60)
    print("リファクタリング検証（完全一致確認）")
    print("=" * 60)

    # 基準データ読み込み
    baseline_file = "baseline_runlength_test.json"
    if not os.path.exists(baseline_file):
        print(f"NG 基準データファイルが存在しません: {baseline_file}")
        return False

    with open(baseline_file, 'r', encoding='utf-8') as f:
        baseline_data = json.load(f)

    print(f"OK 基準データ読み込み完了: {baseline_file}")

    # リファクタリング後のデータ生成
    service = Grib2Service()

    # テストファイルパス
    swi_file = "data/Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_file = "data/guid_msm_grib2_20250101000000_rmax00.bin"

    refactored_data = {}

    # SWIファイル解析
    print(f"\nSWIファイル解析: {swi_file}")
    if os.path.exists(swi_file):
        try:
            base_info, swi_result = service.unpack_swi_grib2_from_file(swi_file)
            refactored_data['swi'] = {
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
        except Exception as e:
            print(f"  NG SWIファイル解析エラー: {e}")
            refactored_data['swi'] = None
    else:
        print(f"  NG ファイルが存在しません")
        refactored_data['swi'] = None

    # ガイダンスファイル解析
    print(f"\nガイダンスファイル解析: {guidance_file}")
    if os.path.exists(guidance_file):
        try:
            base_info, guidance_result = service.unpack_guidance_grib2_from_file(guidance_file)

            # 1時間・3時間雨量データをサンプリング
            data_1h = guidance_result['data_1h']
            data_3h = guidance_result['data_3h']

            refactored_data['guidance'] = {
                'base_info': {
                    'initial_date': base_info.initial_date.isoformat(),
                    'grid_num': base_info.grid_num,
                },
                'data_1h_count': len(data_1h),
                'data_3h_count': len(data_3h),
            }

            # 各時系列の最初の500個をサンプル
            for i, item in enumerate(data_1h):
                refactored_data['guidance'][f'data_1h_ft{item["ft"]}_sample'] = item['value'][:500]
                refactored_data['guidance'][f'data_1h_ft{item["ft"]}_length'] = len(item['value'])

            for i, item in enumerate(data_3h):
                refactored_data['guidance'][f'data_3h_ft{item["ft"]}_sample'] = item['value'][:500]
                refactored_data['guidance'][f'data_3h_ft{item["ft"]}_length'] = len(item['value'])

            print(f"  OK 1時間雨量データセット数: {len(data_1h)}")
            print(f"  OK 3時間雨量データセット数: {len(data_3h)}")

        except Exception as e:
            print(f"  NG ガイダンスファイル解析エラー: {e}")
            refactored_data['guidance'] = None
    else:
        print(f"  NG ファイルが存在しません")
        refactored_data['guidance'] = None

    # 完全一致検証
    print("\n" + "=" * 60)
    print("完全一致検証")
    print("=" * 60)

    all_matched = True
    tolerance = 1e-10  # 浮動小数点許容誤差

    # SWIデータ検証
    if baseline_data.get('swi') and refactored_data.get('swi'):
        print("\n[SWIデータ検証]")

        # データ長検証
        baseline_length = baseline_data['swi']['swi_data_length']
        refactored_length = refactored_data['swi']['swi_data_length']
        if baseline_length == refactored_length:
            print(f"  OK データ長一致: {baseline_length}")
        else:
            print(f"  NG データ長不一致: {baseline_length} != {refactored_length}")
            all_matched = False

        # サンプルデータ検証
        baseline_swi = baseline_data['swi']['swi_data']
        refactored_swi = refactored_data['swi']['swi_data']

        mismatch_count = 0
        for i in range(len(baseline_swi)):
            diff = abs(baseline_swi[i] - refactored_swi[i])
            if diff > tolerance:
                if mismatch_count < 5:  # 最初の5個だけ表示
                    print(f"  NG インデックス{i}: {baseline_swi[i]} != {refactored_swi[i]} (差分: {diff})")
                mismatch_count += 1

        if mismatch_count == 0:
            print(f"  OK 全{len(baseline_swi)}個のサンプルデータ完全一致")
        else:
            print(f"  NG {mismatch_count}個の不一致")
            all_matched = False

    # ガイダンスデータ検証
    if baseline_data.get('guidance') and refactored_data.get('guidance'):
        print("\n[ガイダンスデータ検証]")

        # データセット数検証
        for key in ['data_1h_count', 'data_3h_count']:
            baseline_count = baseline_data['guidance'][key]
            refactored_count = refactored_data['guidance'][key]
            if baseline_count == refactored_count:
                print(f"  OK {key}: {baseline_count}")
            else:
                print(f"  NG {key}不一致: {baseline_count} != {refactored_count}")
                all_matched = False

        # 各時系列データ検証
        all_keys = [k for k in baseline_data['guidance'].keys() if k.endswith('_sample')]

        for key in all_keys:
            baseline_values = baseline_data['guidance'][key]
            refactored_values = refactored_data['guidance'][key]

            mismatch_count = 0
            for i in range(len(baseline_values)):
                diff = abs(baseline_values[i] - refactored_values[i])
                if diff > tolerance:
                    if mismatch_count < 3:  # 最初の3個だけ表示
                        print(f"  NG {key}[{i}]: {baseline_values[i]} != {refactored_values[i]}")
                    mismatch_count += 1

            if mismatch_count == 0:
                print(f"  OK {key}: 全{len(baseline_values)}個一致")
            else:
                print(f"  NG {key}: {mismatch_count}個の不一致")
                all_matched = False

    # 最終判定
    print("\n" + "=" * 60)
    if all_matched:
        print("結果: 完全一致確認 - リファクタリング成功")
        print("=" * 60)
        return True
    else:
        print("結果: 不一致検出 - リファクタリング失敗")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = compare_data()
    sys.exit(0 if success else 1)

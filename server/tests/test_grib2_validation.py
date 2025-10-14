# -*- coding: utf-8 -*-
"""
GRIB2最適化の検証スクリプト
baseline_grib2_test.json と optimized_grib2_test.json を比較
"""
import json
from typing import Any, List


def compare_values(path: str, baseline_val: Any, optimized_val: Any) -> List[str]:
    """2つの値を比較してエラーリストを返す"""
    errors = []

    if type(baseline_val) != type(optimized_val):
        errors.append(f"{path}: Type mismatch - {type(baseline_val).__name__} vs {type(optimized_val).__name__}")
        return errors

    if isinstance(baseline_val, dict):
        # 辞書の比較
        baseline_keys = set(baseline_val.keys())
        optimized_keys = set(optimized_val.keys())

        if baseline_keys != optimized_keys:
            missing = baseline_keys - optimized_keys
            extra = optimized_keys - baseline_keys
            if missing:
                errors.append(f"{path}: Missing keys in optimized: {missing}")
            if extra:
                errors.append(f"{path}: Extra keys in optimized: {extra}")

        # 共通キーの比較
        for key in baseline_keys & optimized_keys:
            errors.extend(compare_values(f"{path}.{key}", baseline_val[key], optimized_val[key]))

    elif isinstance(baseline_val, list):
        # リストの比較
        if len(baseline_val) != len(optimized_val):
            errors.append(f"{path}: List length mismatch - {len(baseline_val)} vs {len(optimized_val)}")
            return errors

        for i, (base_item, opt_item) in enumerate(zip(baseline_val, optimized_val)):
            errors.extend(compare_values(f"{path}[{i}]", base_item, opt_item))

    elif isinstance(baseline_val, float):
        # 浮動小数点の比較（許容誤差1e-10）
        if abs(baseline_val - optimized_val) > 1e-10:
            errors.append(f"{path}: Float value mismatch - {baseline_val} vs {optimized_val}")

    else:
        # その他の値の比較
        if baseline_val != optimized_val:
            errors.append(f"{path}: Value mismatch - {baseline_val} vs {optimized_val}")

    return errors


def main():
    print("=== GRIB2最適化検証開始 ===\n")

    # ファイル読み込み
    with open('baseline_grib2_test.json', 'r', encoding='utf-8') as f:
        baseline = json.load(f)

    with open('optimized_grib2_test.json', 'r', encoding='utf-8') as f:
        optimized = json.load(f)

    # calculation_timeフィールドを除外
    baseline_copy = baseline.copy()
    optimized_copy = optimized.copy()
    baseline_copy.pop('calculation_time', None)
    optimized_copy.pop('calculation_time', None)

    # 比較実行
    errors = compare_values("root", baseline_copy, optimized_copy)

    if len(errors) == 0:
        print("[OK] VALIDATION PASSED")
        print("All data matches perfectly!")
        print(f"\nTotal meshes validated: {sum(len(area['meshes']) for pref in baseline['prefectures'].values() for area in pref['areas'])}")
    else:
        print("[FAIL] VALIDATION FAILED")
        print(f"\nTotal errors: {len(errors)}")
        print("\nFirst 10 errors:")
        for error in errors[:10]:
            print(f"  - {error}")

        if len(errors) > 10:
            print(f"\n... and {len(errors) - 10} more errors")

    print("\n=== 検証完了 ===")


if __name__ == "__main__":
    main()

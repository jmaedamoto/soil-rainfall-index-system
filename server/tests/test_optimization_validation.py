"""
最適化前後の出力完全一致検証スクリプト

最適化実装後にこのスクリプトを実行して、
baseline_optimization_test.json と完全一致することを確認する。
"""
import json
import sys
from typing import Dict, Any, List, Tuple


def load_json(filepath: str) -> Dict[str, Any]:
    """JSONファイルを読み込む"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_values(path: str, baseline_val: Any, optimized_val: Any) -> List[str]:
    """2つの値を比較してエラーリストを返す"""
    errors = []

    if type(baseline_val) != type(optimized_val):
        errors.append(f"{path}: Type mismatch - baseline: {type(baseline_val)}, optimized: {type(optimized_val)}")
        return errors

    if isinstance(baseline_val, dict):
        baseline_keys = set(baseline_val.keys())
        optimized_keys = set(optimized_val.keys())

        if baseline_keys != optimized_keys:
            missing = baseline_keys - optimized_keys
            extra = optimized_keys - baseline_keys
            if missing:
                errors.append(f"{path}: Missing keys in optimized: {missing}")
            if extra:
                errors.append(f"{path}: Extra keys in optimized: {extra}")

        for key in baseline_keys & optimized_keys:
            errors.extend(compare_values(f"{path}.{key}", baseline_val[key], optimized_val[key]))

    elif isinstance(baseline_val, list):
        if len(baseline_val) != len(optimized_val):
            errors.append(f"{path}: List length mismatch - baseline: {len(baseline_val)}, optimized: {len(optimized_val)}")
            return errors

        for i, (b_item, o_item) in enumerate(zip(baseline_val, optimized_val)):
            errors.extend(compare_values(f"{path}[{i}]", b_item, o_item))

    elif isinstance(baseline_val, float):
        # 浮動小数点の比較（1e-10の誤差まで許容）
        if abs(baseline_val - optimized_val) > 1e-10:
            errors.append(f"{path}: Float value mismatch - baseline: {baseline_val}, optimized: {optimized_val}")

    else:
        if baseline_val != optimized_val:
            errors.append(f"{path}: Value mismatch - baseline: {baseline_val}, optimized: {optimized_val}")

    return errors


def validate_optimization(baseline_path: str, optimized_path: str) -> Tuple[bool, List[str]]:
    """
    最適化前後のJSONを完全比較

    Returns:
        (is_valid, errors): 完全一致ならTrue、差異があればFalseとエラーリスト
    """
    print(f"Loading baseline data from: {baseline_path}")
    baseline = load_json(baseline_path)

    print(f"Loading optimized data from: {optimized_path}")
    optimized = load_json(optimized_path)

    print("\n=== Validation Starting ===")

    # トップレベル統計
    baseline_meshes = [m for p in baseline['prefectures'].values()
                      for a in p['areas'] for m in a['meshes']]
    optimized_meshes = [m for p in optimized['prefectures'].values()
                       for a in p['areas'] for m in a['meshes']]

    print(f"Baseline meshes: {len(baseline_meshes)}")
    print(f"Optimized meshes: {len(optimized_meshes)}")

    # calculation_timeを除外してコピー作成（タイムスタンプは常に異なるため）
    baseline_copy = baseline.copy()
    optimized_copy = optimized.copy()
    baseline_copy.pop('calculation_time', None)
    optimized_copy.pop('calculation_time', None)

    # 完全比較
    errors = compare_values("root", baseline_copy, optimized_copy)

    if not errors:
        print("\n[OK] VALIDATION PASSED: Complete match")
        print(f"   - {len(baseline_meshes)} meshes")
        print(f"   - {len(baseline_meshes[0]['swi_timeline'])} time steps")
        print(f"   - All fields match perfectly")
        return True, []
    else:
        print(f"\n[FAIL] VALIDATION FAILED: {len(errors)} differences")
        for i, error in enumerate(errors[:10], 1):
            print(f"   {i}. {error}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")
        return False, errors


if __name__ == "__main__":
    baseline_file = "d:/development/soil-rainfall-index-system/server/baseline_optimization_test.json"

    if len(sys.argv) > 1:
        optimized_file = sys.argv[1]
    else:
        # デフォルト: 最適化後のテストAPI結果
        optimized_file = "d:/development/soil-rainfall-index-system/server/optimized_test_result.json"

    is_valid, errors = validate_optimization(baseline_file, optimized_file)

    sys.exit(0 if is_valid else 1)

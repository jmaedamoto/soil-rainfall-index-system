# GRIB2分析・VBA比較テストインフラ

前回のセッションで構築された、GRIB2データ解析とVBA結果比較のための包括的なテストスイートです。

## ディレクトリ構成

### `/grib2_analysis/`
GRIB2ファイル構造の詳細解析・比較テスト
- `debug_grib2_detailed.py` - GRIB2バイナリ構造の詳細解析
- `debug_grib2_structure.py` - セクション構造の分析
- `compare_*.py` - CSV vs GRIB2データの全メッシュ比較
- `test_simple_swi_comparison.py` - シンプルなSWI値比較テスト

### `/vba_comparison/`
VBAアルゴリズムとの精密比較テスト
- `debug_exact_comparison.py` - VBA計算結果との完全一致確認
- `debug_complete_mapping.py` - 座標マッピングの完全検証
- `debug_runlength_step.py` - ランレングス展開の詳細ステップ解析
- `debug_level_array.py` - レベル配列構築の詳細検証
- `debug_meshcode_mapping.py` - メッシュコードマッピングの検証
- `debug_ft_mapping.py` - FTマッピング処理の検証

### `/coordinate_tests/`
座標変換・位置計算の検証テスト
- `test_coordinate_conversion.py` - 緯度経度⇔グリッド座標変換テスト
- `debug_single_point.py` - 単一ポイントでの詳細座標解析

## 使用目的

このテストインフラは以下の技術課題の解決を目的として構築されました：

1. **GRIB2解析精度の検証**: バイナリデータの解析結果が正確かの確認
2. **VBA互換性の確認**: 元のVBAコードと完全に同一の結果を出力するかの検証
3. **座標変換の正確性**: 緯度経度⇔グリッドインデックス変換の精度確認
4. **全メッシュでのデータ整合性**: 26,051メッシュ全体でのデータ一貫性確認

## テスト実行方法

```bash
# GRIB2解析テスト
cd server
python tests/grib2_analysis/debug_grib2_detailed.py

# VBA比較テスト
python tests/vba_comparison/debug_exact_comparison.py

# 座標変換テスト
python tests/coordinate_tests/test_coordinate_conversion.py
```

## 前回の作業成果

- 19個の専門的テスト・デバッグスクリプトを構築
- GRIB2バイナリ解析の詳細ステップをトレース可能
- VBAアルゴリズムとの差異を特定する精密比較機能
- 大規模メッシュデータでの整合性確認機能

このテストインフラにより、システムの技術的精度と信頼性が大幅に向上しました。
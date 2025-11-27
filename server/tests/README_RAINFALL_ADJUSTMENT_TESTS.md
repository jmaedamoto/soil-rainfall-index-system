# 雨量調整機能 テストガイド

## 概要

雨量調整機能の正当性と機能性を検証するための統合テストスイート。

## テストファイル

### 1. test_rainfall_adjustment_integration.py
**統合テスト - 恒等性検証**

編集なしの雨量調整が元の計算結果と100%一致することを検証します。

**テスト内容**:
1. 元のGRIB2データでベースライン計算
2. 市町村別雨量を抽出
3. 抽出した雨量をそのまま（編集なし）で再計算
4. ベースラインと再計算結果の危険度時系列を比較
5. 100%一致を確認

**実行方法**:
```bash
# Windows
cd server
python tests\test_rainfall_adjustment_integration.py

# または
run_rainfall_adjustment_test.bat

# Linux/Mac
cd server
python tests/test_rainfall_adjustment_integration.py
```

**期待結果**:
```
============================================================
テスト結果サマリー
============================================================
比較対象市町村数: 208
総比較ポイント数: 5,616
一致数: 5,616
不一致数: 0
一致率: 100.00%

[SUCCESS] テスト成功: 100%一致しました！
```

**検証項目**:
- ✅ 雨量抽出の正確性
- ✅ 調整比率計算の正確性
- ✅ 雨量調整の正確性
- ✅ SWI・危険度再計算の正確性
- ✅ 恒等性の保証

### 2. test_rainfall_adjustment_functional.py
**機能テスト - 雨量増減と危険度の関係**

雨量の増加・減少が危険度に正しく反映されることを検証します。

**テスト内容**:
1. **雨量増加テスト**: 雨量を2倍にして危険度が上がる（または維持される）ことを確認
2. **雨量減少テスト**: 雨量を半分にして危険度が下がる（または維持される）ことを確認

**実行方法**:
```bash
cd server
python tests\test_rainfall_adjustment_functional.py
```

**期待結果**:
```
============================================================
Functional Test Summary
============================================================
Rainfall Increase Test: PASSED
Rainfall Decrease Test: PASSED
============================================================

[SUCCESS] All functional tests passed
```

**検証項目**:
- ✅ 雨量増加 → 危険度上昇の動作確認
- ✅ 雨量減少 → 危険度低下の動作確認
- ✅ タンクモデルの正しい応答

## テストデータ

### 必要ファイル
以下のファイルが `server/data/` ディレクトリに必要です：

```
server/data/
├── Z__C_RJTD_20250101000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin
├── guid_msm_grib2_20250101000000_rmax00.bin
├── dosha_*.csv (6府県分)
└── dosyakei_*.csv (6府県分)
```

### データ内容
- **SWI GRIB2**: 土壌雨量指数の初期データ
- **ガイダンス GRIB2**: 降水量予測データ
- **CSV**: 境界データ・土砂災害データ

## テスト実行環境

### 必要な環境
- Python 3.8+
- 必要ライブラリ: `pip install -r requirements.txt`
- メモリ: 4GB以上推奨
- 実行時間: 統合テスト約3分、機能テスト約6分

### 注意事項
1. テストは26,045メッシュを処理するため、時間がかかります
2. ログが大量に出力されますが、最後のサマリーで結果を確認できます
3. Windows環境では文字エンコーディングの警告が出る場合がありますが、テスト結果には影響しません

## テスト結果の解釈

### 成功の判定基準

#### 統合テスト
- **一致率100%**: すべての市町村・すべての時刻で危険度が一致
- **不一致数0**: 一件も不一致がない

#### 機能テスト
- **雨量増加テスト**: 調整後の最大危険度 ≥ ベースラインの最大危険度
- **雨量減少テスト**: 調整後の最大危険度 ≤ ベースラインの最大危険度

### 失敗時の対処

テストが失敗した場合は、ログを確認してください：

1. **不一致の詳細**: どの市町村のどの時刻で不一致が発生したか
2. **エラーメッセージ**: 例外が発生した場合の詳細
3. **データ確認**: テストデータが正しく配置されているか

## トラブルシューティング

### よくある問題

#### 1. テストファイルが見つからない
```
ERROR - テストファイルが見つかりません
```

**対処**: `server/data/` ディレクトリに必要なGRIB2ファイルが配置されているか確認

#### 2. メモリ不足
```
MemoryError
```

**対処**:
- 不要なアプリケーションを終了
- システムのメモリを増やす

#### 3. プロキシエラー
```
ProxyError: HTTPConnectionPool
```

**対処**: `config/app_config.yaml` でプロキシ設定を確認

## CI/CD統合

### GitHub Actionsでの実行例

```yaml
name: Rainfall Adjustment Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: |
          cd server
          pip install -r requirements.txt
      - name: Run integration test
        run: |
          cd server
          python tests/test_rainfall_adjustment_integration.py
      - name: Run functional test
        run: |
          cd server
          python tests/test_rainfall_adjustment_functional.py
```

## レポート

テスト実行後、以下のレポートを参照してください：
- `RAINFALL_ADJUSTMENT_TEST_REPORT.md`: 統合テストの詳細レポート

## 関連ドキュメント

- `/server/services/rainfall_adjustment_service.py`: 雨量調整サービスの実装
- `/server/src/api/controllers/rainfall_controller.py`: APIコントローラー
- `/client/src/pages/RainfallAdjustment.tsx`: クライアント側UI

---

**作成日**: 2025年11月27日
**最終更新**: 2025年11月27日
**作成者**: Claude (Anthropic)

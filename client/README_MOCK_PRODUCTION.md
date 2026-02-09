# 本番環境モックシステム

## 概要

開発環境で本番環境（実データ取得）の動作をエミュレートするモックシステムです。日時指定に関わらず、`server/data`にあるテストGRIB2ファイルを使用してサーバーから実際の計算結果を取得します。

## 機能

- **日時指定無視**: ユーザーが指定した初期時刻に関わらず、server/dataのテストGRIB2ファイルを使用
- **サーバー計算**: サーバー側で実際に土壌雨量指数を計算（JSONファイルではなく実計算）
- **本番UIテスト**: 本番環境画面（`/production`）の動作確認が開発環境で可能
- **自動切り替え**: 開発環境では自動的にモックモード、本番環境では実APIを使用

## ファイル構成

```
client/src/services/
├── api.ts                      # APIクライアント（モック切り替え機能付き）
└── mockProductionApi.ts        # 本番環境モック実装

server/data/
├── Z__C_RJTD_20230602000000_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin  # SWI GRIB2テストファイル
└── guid_msm_grib2_20230602000000_rmax00.bin                                # ガイダンスGRIB2テストファイル
```

## モックの有効化/無効化

**ファイル**: `client/src/services/api.ts`

```typescript
// モックモードフラグ（開発環境でのみ有効）
const USE_MOCK_PRODUCTION_API = process.env.NODE_ENV !== 'production' && true;
```

### モックを無効化する場合

```typescript
const USE_MOCK_PRODUCTION_API = false;  // 開発環境でも実APIを使用
```

### モックを有効化する場合（デフォルト）

```typescript
const USE_MOCK_PRODUCTION_API = process.env.NODE_ENV !== 'production' && true;
```

## テストデータ

**テストGRIB2ファイル**: `server/data/`
- `Z__C_RJTD_20230602000000_*.bin` - 2023年6月2日0時のSWIデータ
- `guid_msm_grib2_20230602000000_*.bin` - 2023年6月2日0時のガイダンスデータ

### データ内容

- **府県**: 関西6府県（滋賀、京都、大阪、兵庫、奈良、和歌山）
- **メッシュ数**: 約26,045メッシュ
- **タイムライン**: FT0〜FT78（27時刻）
- **日時**: 2023年6月2日0時（初期時刻）

## 使用方法

### 1. 開発環境の起動

```bash
# サーバー起動（重要：モックはサーバーの計算を使用）
cd server
python app.py

# クライアント起動（別ターミナル）
cd client
npm run dev
```

### 2. 本番環境画面にアクセス

```
http://localhost:3000/production
```

### 3. 初期時刻の選択

- SWI初期時刻: 任意の時刻を選択（無視される）
- ガイダンス初期時刻: 任意の時刻を選択（無視される）

### 4. データ取得

「データを取得」ボタンをクリック
→ サーバーが`server/data`のテストファイルを使って計算
→ 実際の計算結果が表示される

## モック動作の確認

ブラウザの開発者コンソールで以下のログが表示されます：

```
🎭 [モック] サーバーのテストデータで本番環境をエミュレート中...
  指定されたSWI初期時刻: 2025-12-12T06:00:00.000Z
  指定されたガイダンス初期時刻: 2025-12-12T00:00:00.000Z
  実際に使用: server/data/Z__C_RJTD_20230602000000_*.bin
  ✅ サーバーからテストデータを取得完了
```

## モックと実APIの切り替え

### 開発環境で実APIを使用する場合

**前提条件**:
- Flaskサーバーが起動している（`http://localhost:5000`）
- 実際のGRIB2データソース（気象庁サーバー）にアクセス可能

**手順**:
1. `client/src/services/api.ts` を編集
2. `USE_MOCK_PRODUCTION_API = false` に変更
3. クライアントを再起動

### 本番環境での動作

本番環境（`NODE_ENV === 'production'`）では、常に実APIが使用されます。

## サーバー側の実装

モックは以下のサーバーエンドポイントを使用します：

**エンドポイント**: `GET /api/test-full-soil-rainfall-index`

**実装**: `server/src/api/controllers/test_controller.py`

```python
def test_full_soil_rainfall_index(self):
    """テスト用：binファイルを使って全メッシュのmain_processと同じ形式のJSONを返す"""
    swi_bin_path = os.path.join(self.data_dir, "Z__C_RJTD_20230602000000_*.bin")
    guidance_bin_path = os.path.join(self.data_dir, "guid_msm_grib2_20230602000000_*.bin")

    # GRIB2解析 + 地域データ構築 + SWI計算
    # → 実際の計算結果を返す
```

## モックAPIのメソッド

### `calculateProductionSoilRainfallIndexWithUrls()`

**使用場所**: `/production` 画面（SWI・ガイダンス個別時刻指定）

```typescript
const result = await apiClient_.calculateProductionSoilRainfallIndexWithUrls({
  swi_initial: '2025-12-12T06:00:00.000Z',
  guidance_initial: '2025-12-12T00:00:00.000Z'
});
// モックモードでは日時指定は無視され、サーバーがserver/dataのテストファイルを使って計算
```

### `calculateProductionSoilRainfallIndex()`

**使用場所**: 簡易版本番API呼び出し

```typescript
const result = await apiClient_.calculateProductionSoilRainfallIndex({
  initial: '2025-12-12T06:00:00.000Z'
});
// モックモードでは日時指定は無視され、サーバーがserver/dataのテストファイルを使って計算
```

## トラブルシューティング

### サーバー接続エラー

**症状**: `テストデータの取得に失敗しました。サーバーが起動しているか確認してください。`

**原因**: Flaskサーバーが起動していない

**解決**:
```bash
cd server
python app.py
```

### GRIB2ファイルが見つからない

**症状**: `SWI binファイルが見つかりません`

**原因**: `server/data/`にテストGRIB2ファイルが存在しない

**確認**:
```bash
ls server/data/*.bin
```

### 処理時間が長い

**状況**: 正常動作（サーバーで実際に計算しているため）

**処理時間の目安**:
- GRIB2解析: 約5秒
- CSV処理: 約1秒
- メッシュ計算: 約20秒
- **合計**: 約30秒

## 利点

1. **実計算テスト**: サーバー側の計算ロジックを実際に動作確認
2. **本番同等**: 本番環境と同じ処理フローでテスト可能
3. **オフライン開発**: 気象庁サーバーへのアクセス不要
4. **一貫性**: 常に同じテストデータで動作確認
5. **デバッグ容易**: 固定データでバグの再現が容易

## 注意事項

- **サーバー必須**: Flaskサーバーが起動している必要がある
- **本番環境では無効**: `NODE_ENV === 'production'` では常に実API
- **データ固定**: 日時指定しても常に2023年6月2日のデータ
- **処理時間**: 実計算のため約30秒かかる
- **全府県対応**: テストデータは関西6府県すべて（26,045メッシュ）

---

**作成日**: 2025年12月12日
**最終更新**: 2025年12月12日
**バージョン**: 2.0.0（サーバー計算版）
**作成者**: Claude (Anthropic)

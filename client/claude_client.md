# 土壌雨量指数計算システム - クライアント開発仕様書

## プロジェクト概要

React TypeScript + Vite を使用した土壌雨量指数計算システムのフロントエンドクライアント  
Flask Python APIバックエンドと連携し、関西6府県26,051メッシュのリアルタイム土壌雨量指数を可視化

### 技術スタック（実装済み）
- **フレームワーク**: React 18 + TypeScript
- **ビルドツール**: Vite  
- **地図表示**: Leaflet + react-leaflet
- **グラフ表示**: Chart.js + react-chartjs-2
- **HTTPクライアント**: Axios
- **状態管理**: React useState/useEffect
- **スタイリング**: インラインスタイル（CSS-in-JS）

## 機能要件

### 1. メイン機能（実装済み）
- [x] 土壌雨量指数計算の実行（Flask API連携）
- [x] リアルタイムデータ表示（26,051メッシュ対応）
- [x] 地図上での可視化（Leafletマップ）
- [x] 警戒レベルの表示（4段階リスクレベル）
- [x] 時系列グラフ表示（Chart.js）

### 2. UI/UX要件（実装済み）
- [x] レスポンシブデザイン（PC/タブレット対応）
- [x] プログレスバー付きローディング表示
- [x] 直感的な操作性（時間スライダー、メッシュクリック）
- [x] 高速な表示レスポンス（120秒タイムアウト対応）

### 3. データ表示機能（実装済み）
- [x] 都道府県別データ表示（関西6府県）
- [x] 地域別データ表示（市区町村レベル）
- [x] メッシュ別詳細表示（1km×1kmグリッド）
- [x] 時系列変化の表示（FT時間スライダー）

## ページ構成（実装済み）

### 1. 統合ダッシュボード（/）
- [x] システム概要とデータ情報表示
- [x] 最新の警戒状況サマリー
- [x] 自動データ読み込み機能
- [x] プログレス表示付きローディング

### 2. 地図表示エリア（統合）
- [x] インタラクティブ地図（Leaflet）
- [x] 1km×1kmメッシュグリッド表示
- [x] リスクレベル色分け（注意/警報/土砂災害）
- [x] 白地図背景 + 都道府県境界線
- [x] メッシュクリック詳細表示
- [x] 時間スライダー（FT時間変更）

### 3. データ分析エリア（統合）
- [x] メッシュ分析ツール（26,051個の詳細統計）
- [x] リスクレベル分布表示
- [x] 境界値サンプル表示
- [x] 時系列データ調査機能

### 4. グラフ表示エリア（統合）
- [x] 地域リスク時系列グラフ（選択した地域）
- [x] メッシュ詳細時系列グラフ（選択したメッシュ）
- [x] Chart.js による動的グラフ描画

### 5. デバッグ・データ調査ツール（統合）
- [x] サンプルデータダウンロード
- [x] 全データダウンロード
- [x] ブラウザコンソール詳細分析
- [x] データ構造調査機能

## コンポーネント設計（実装済み）

### 1. メインページコンポーネント
```
/src/pages/
└── SoilRainfallDashboard.tsx    # 統合ダッシュボード（メインページ）
```

### 2. 共通コンポーネント
```
/src/components/common/
└── ProgressBar.tsx              # プログレスバー（実装済み）
```

### 3. 地図コンポーネント（実装済み）
```
/src/components/map/
├── SoilRainfallMap.tsx          # メイン地図コンポーネント（Leaflet）
├── TimeSlider.tsx               # 時間スライダー（インデックスベース修正済み）
└── LeafletIcons.ts             # Leafletアイコン設定
```

### 4. グラフコンポーネント（実装済み）
```
/src/components/charts/
├── RiskTimelineChart.tsx        # リスクレベル時系列グラフ
└── SoilRainfallTimelineChart.tsx # 土壌雨量指数時系列グラフ
```

### 5. デバッグ・分析コンポーネント（実装済み）
```
/src/components/debug/
├── DataDownloader.tsx           # データダウンロード機能
└── MeshAnalyzer.tsx            # メッシュ分析ツール
```

### 6. サービス・型定義（実装済み）
```
/src/services/
└── api.ts                      # APIクライアント（120秒タイムアウト対応）

/src/types/
└── api.ts                      # TypeScript型定義（完全対応）

/src/hooks/
└── LeafletIcons.ts             # Leafletアイコン修正フック
```

## 状態管理設計

### 1. Global State（Context API）
```typescript
interface AppState {
  user: UserState;
  settings: SettingsState;
  ui: UIState;
}

interface UserState {
  preferences: UserPreferences;
  notifications: NotificationSettings;
}

interface SettingsState {
  mapSettings: MapSettings;
  displaySettings: DisplaySettings;
  updateInterval: number;
}

interface UIState {
  loading: boolean;
  selectedPrefecture: string | null;
  selectedArea: string | null;
  currentTime: Date;
}
```

### 2. Server State（React Query）
```typescript
// API呼び出し用のカスタムフック
useCalculationData(initialTime: string)
useHealthCheck()
usePrefectureData(prefectureCode: string)
useTimeSeriesData(meshCode: string)
```

## API通信設計

### 1. APIクライアント
```typescript
// /src/services/api.ts
class SoilRainfallAPIClient {
  async calculateSoilRainfallIndex(params: CalculationParams): Promise<CalculationResult>
  async getHealthStatus(): Promise<HealthStatus>
  async getPrefectureData(code: string): Promise<PrefectureData>
  async getTimeSeriesData(meshCode: string): Promise<TimeSeriesData>
}
```

### 2. 型定義
```typescript
// /src/types/api.ts
interface CalculationParams {
  initial: string; // ISO8601形式
}

interface CalculationResult {
  status: 'success' | 'error';
  calculation_time: string;
  initial_time: string;
  prefectures: Record<string, Prefecture>;
}

interface Prefecture {
  name: string;
  code: string;
  areas: Area[];
}

interface Area {
  name: string;
  meshes: Mesh[];
  risk_timeline: RiskTimePoint[];
}

interface Mesh {
  code: string;
  lat: number;
  lon: number;
  advisary_bound: number;
  warning_bound: number;
  dosyakei_bound: number;
  swi_timeline: TimeSeriesPoint[];
  rain_timeline: TimeSeriesPoint[];
}
```

## UI/UXデザイン

### 1. デザインシステム
- **カラーパレット**: 警戒レベルに応じた色分け
  - レベル0（正常）: 緑色系
  - レベル1（注意）: 黄色系
  - レベル2（警報）: オレンジ色系
  - レベル3（土砂災害）: 赤色系

### 2. レスポンシブデザイン
- **デスクトップ**: 1200px以上
- **タブレット**: 768px - 1199px
- **モバイル**: 767px以下（必要に応じて対応）

### 3. アクセシビリティ
- WAI-ARIA準拠
- キーボードナビゲーション対応
- 色覚異常への配慮

## パフォーマンス要件

### 1. 表示速度
- 初期表示: 3秒以内
- 計算結果表示: 10秒以内
- 地図操作レスポンス: 1秒以内

### 2. データ処理
- 26,000+メッシュデータの効率的表示
- 仮想化スクロール対応
- 必要に応じたデータのページング

### 3. メモリ使用量
- 大量データの効率的メモリ管理
- 不要なデータのクリーンアップ

## 開発環境

### 1. 開発サーバー
```bash
npm run dev          # 開発サーバー起動
npm run build        # プロダクションビルド
npm run preview      # ビルド結果プレビュー
npm run lint         # ESLint実行
npm run type-check   # TypeScript型チェック
```

### 2. 必要な依存関係
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "react-query": "^3.39.0",
    "axios": "^1.3.0",
    "leaflet": "^1.9.0",
    "react-leaflet": "^4.2.0",
    "chart.js": "^4.2.0",
    "react-chartjs-2": "^5.2.0",
    "@types/leaflet": "^1.9.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "@typescript-eslint/eslint-plugin": "^5.0.0",
    "@typescript-eslint/parser": "^5.0.0",
    "eslint": "^8.0.0",
    "eslint-plugin-react": "^7.32.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "typescript": "^4.9.0",
    "vite": "^4.1.0"
  }
}
```

## テスト戦略

### 1. 単体テスト
- React Testing Library使用
- コンポーネントの動作テスト
- カスタムフックのテスト

### 2. 統合テスト
- API通信のテスト
- 画面間の連携テスト

### 3. E2Eテスト
- Playwright使用
- 主要なユーザーフローのテスト

## セキュリティ

### 1. データ保護
- APIキーの適切な管理
- XSS対策
- CSRF対策

### 2. 入力値検証
- ユーザー入力の適切な検証
- SQLインジェクション対策

## デプロイメント

### 1. ビルド設定
- 本番環境用の最適化
- 環境変数の管理
- CDN配信対応

### 2. CI/CD
- 自動テスト実行
- 自動デプロイメント
- 品質チェック

## 今後の検討事項

### 1. 機能拡張
- [ ] モバイルアプリ対応
- [ ] オフライン機能
- [ ] 多言語対応
- [ ] ダークモード対応

### 2. 技術的改善
- [ ] PWA化
- [ ] WebAssembly活用
- [ ] WebGL地図表示
- [ ] リアルタイム通信（WebSocket）

### 3. ユーザビリティ
- [ ] ユーザーフィードバック機能
- [ ] カスタマイズ可能なダッシュボード
- [ ] データ比較機能
- [ ] 履歴機能

---

**作成日**: 2025年7月28日  
**最終更新**: 2025年7月28日  
**バージョン**: 1.0.0  
**作成者**: Claude (Anthropic)  
**プロジェクト**: 土壌雨量指数計算システム - クライアント開発仕様書
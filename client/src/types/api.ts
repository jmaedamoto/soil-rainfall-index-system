// 土壌雨量指数計算システム API型定義

export interface TimeSeriesPoint {
  ft: number;  // 予測時間（時間）
  value: number;  // 値
}

export interface RiskTimePoint {
  ft: number;  // 予測時間（時間）
  value: number;  // リスクレベル（0-3）
}

export interface Mesh {
  code: string;  // メッシュコード
  lat: number;   // 緯度
  lon: number;   // 経度
  advisary_bound: number;   // 注意報基準値
  warning_bound: number;    // 警報基準値
  dosyakei_bound: number;   // 土砂災害基準値
  swi_timeline: TimeSeriesPoint[];  // 土壌雨量指数時系列（3時間ごと）
  swi_hourly_timeline: TimeSeriesPoint[];  // 土壌雨量指数時系列（1時間ごと）
  rain_1hour_timeline: TimeSeriesPoint[]; // 1時間ごとの雨量時系列（推定）
  rain_1hour_max_timeline: TimeSeriesPoint[]; // 3時間内の最大1時間雨量時系列
  rain_timeline: TimeSeriesPoint[]; // 3時間ごとの合計雨量時系列
  risk_hourly_timeline: RiskTimePoint[]; // 1時間ごとの危険度時系列
  risk_3hour_max_timeline: RiskTimePoint[]; // 3時間ごとの最大危険度時系列（1時間雨量ベース）
}

export interface Area {
  name: string;  // 地域名
  meshes: Mesh[];  // メッシュデータ
  risk_timeline: RiskTimePoint[];  // リスク時系列
}

export interface Prefecture {
  name: string;  // 都道府県名
  code: string;  // 都道府県コード
  areas: Area[];  // 地域データ
}

export interface CalculationResult {
  status: 'success' | 'error';
  calculation_time: string;     // 計算時刻（ISO8601）
  initial_time: string;         // 初期時刻（ISO8601） - 後方互換性
  swi_initial_time?: string;    // SWI初期時刻（ISO8601）
  guid_initial_time?: string;   // ガイダンス初期時刻（ISO8601）
  prefectures: Record<string, Prefecture>;  // 都道府県データ
  used_urls?: {                 // 本番API使用時のGRIB2 URL（デバッグ用）
    swi_url: string;
    guidance_url: string;
  };
  statistics?: {                // テストAPI使用時の統計情報
    total_meshes: number;
    processed_meshes: number;
    success_rate: string;
  };
  note?: string;                // テストAPI使用時の説明
}

export interface CalculationParams {
  initial?: string;        // 初期時刻（ISO8601形式） - 後方互換性
  swi_initial?: string;    // SWI初期時刻（ISO8601形式）
  guid_initial?: string;   // ガイダンス初期時刻（ISO8601形式）
}

export interface HealthStatus {
  status: 'success' | 'error';
  message?: string;
  architecture?: string;
  version?: string;
}

// リスクレベルの定義
export enum RiskLevel {
  NORMAL = 0,     // 正常
  CAUTION = 1,    // 注意
  WARNING = 2,    // 警報
  DISASTER = 3    // 土砂災害
}

// リスクレベルの色定義
export const RISK_COLORS = {
  [RiskLevel.NORMAL]: 'transparent',   // 無色（透明）
  [RiskLevel.CAUTION]: '#FFC107',      // 黄
  [RiskLevel.WARNING]: '#FF9800',      // オレンジ
  [RiskLevel.DISASTER]: '#F44336'      // 赤
} as const;

// リスクレベルのラベル
export const RISK_LABELS = {
  [RiskLevel.NORMAL]: '正常',
  [RiskLevel.CAUTION]: '注意',
  [RiskLevel.WARNING]: '警報',
  [RiskLevel.DISASTER]: '土砂災害'
} as const;
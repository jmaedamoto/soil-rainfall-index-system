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
  swi_hourly_timeline?: TimeSeriesPoint[];  // 土壌雨量指数時系列（1時間ごと）※レスポンスサイズ削減のため除外
  rain_1hour_timeline?: TimeSeriesPoint[]; // 1時間ごとの雨量時系列（推定）※レスポンスサイズ削減のため除外
  rain_1hour_max_timeline?: TimeSeriesPoint[]; // 3時間内の最大1時間雨量時系列※レスポンスサイズ削減のため除外
  rain_timeline: TimeSeriesPoint[]; // 3時間ごとの合計雨量時系列
  risk_hourly_timeline?: RiskTimePoint[]; // 1時間ごとの危険度時系列※レスポンスサイズ削減のため除外
  risk_3hour_max_timeline: RiskTimePoint[]; // 3時間ごとの最大危険度時系列（1時間雨量ベース）
}

export interface Area {
  name: string;  // 地域名（市町村名）
  secondary_subdivision_name?: string;  // 所属する二次細分名
  meshes: Mesh[];  // メッシュデータ
  risk_timeline: RiskTimePoint[];  // リスク時系列
}

export interface SecondarySubdivision {
  name: string;  // 二次細分名（例：「阪神」「播磨北西部」）
  area_names: string[];  // 所属市町村名リスト
  rain_1hour_max_timeline: TimeSeriesPoint[];  // 二次細分内の最大1時間雨量
  rain_3hour_timeline: TimeSeriesPoint[];  // 二次細分内の最大3時間雨量
  risk_timeline: RiskTimePoint[];  // 二次細分内の最大リスク
}

export interface Prefecture {
  name: string;  // 都道府県名
  code: string;  // 都道府県コード
  areas: Area[];  // 地域データ（市町村）
  secondary_subdivisions?: SecondarySubdivision[];  // 二次細分リスト
  prefecture_rain_1hour_max_timeline?: TimeSeriesPoint[];  // 府県全体の最大1時間雨量
  prefecture_rain_3hour_timeline?: TimeSeriesPoint[];  // 府県全体の最大3時間雨量
  prefecture_risk_timeline?: RiskTimePoint[];  // 府県全体の最大リスク
}

export interface CacheMetadata {
  cache_key: string;
  created_at: string;           // ISO8601形式
  swi_initial: string;
  guidance_initial: string;
  mesh_count: number;
  file_size_mb: number;
  compressed: boolean;
  compression_format: string;
}

export interface CacheInfo {
  cache_key: string;
  cache_hit: boolean;           // キャッシュヒットフラグ
  cache_metadata: CacheMetadata | null;
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
    swi_initial_time?: string;
    guidance_initial_time?: string;
  };
  cache_info?: CacheInfo;       // キャッシュ情報
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

// リスクレベルの定義（政府ガイドライン準拠: レベル0,2,3,4）
export enum RiskLevel {
  NORMAL = 0,     // レベル0: 正常
  CAUTION = 2,    // レベル2: 注意
  WARNING = 3,    // レベル3: 警報
  DISASTER = 4    // レベル4: 土砂災害
}

// リスクレベルの色定義
export const RISK_COLORS = {
  [RiskLevel.NORMAL]: 'transparent',   // 無色（透明）
  [RiskLevel.CAUTION]: '#FFC107',      // 黄色
  [RiskLevel.WARNING]: '#F44336',      // 赤色
  [RiskLevel.DISASTER]: '#9C27B0'      // 紫色
} as const;

// リスクレベルのラベル
export const RISK_LABELS = {
  [RiskLevel.NORMAL]: '正常',
  [RiskLevel.CAUTION]: '注意',
  [RiskLevel.WARNING]: '警報',
  [RiskLevel.DISASTER]: '土砂災害'
} as const;

// リスクタイムライン表示モード
export type RiskTimelineViewMode = 'municipality' | 'subdivision' | 'prefecture-all';

// 雨量調整機能用の型定義

export interface AreaRainfallForecast {
  status: 'success' | 'error';
  swi_initial_time: string;         // SWI初期時刻（ISO8601）
  guidance_initial_time: string;    // ガイダンス初期時刻（ISO8601）
  area_rainfall: Record<string, TimeSeriesPoint[]>;  // 市町村別雨量時系列
  subdivision_rainfall?: Record<string, TimeSeriesPoint[]>;  // 二次細分別雨量時系列
}

export interface RainfallAdjustmentRequest {
  swi_initial: string;              // SWI初期時刻（ISO8601）
  guidance_initial: string;         // ガイダンス初期時刻（ISO8601）
  area_adjustments: Record<string, Record<number, number>>;  // 市町村別調整後雨量
  subdivision_adjustments?: Record<string, Record<number, number>>;  // 二次細分別調整後雨量
}
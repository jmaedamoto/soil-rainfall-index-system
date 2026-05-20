// 土壌雨量指数計算システム API型定義

export interface TimeSeriesPoint {
  ft: number;  // 予測時間（時間）
  value: number;  // 値
}

export interface RiskTimePoint {
  ft: number;  // 予測時間（時間）
  value: number;  // リスクレベル（0-3）
}

export type RiskRule = 'legacy' | 'lead_time_to_level4';

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
  level4_threshold?: number;  // 領域内のレベル4基準値の最大値
  swi_timeline?: TimeSeriesPoint[];  // 領域内のSWI最大値
  rain_3hour_timeline?: TimeSeriesPoint[];  // 領域内の前3時間雨量最大値
}

export interface SecondarySubdivision {
  name: string;  // 二次細分名（例：「阪神」「播磨北西部」）
  area_names: string[];  // 所属市町村名リスト
  rain_1hour_max_timeline: TimeSeriesPoint[];  // 二次細分内の最大1時間雨量
  rain_3hour_timeline: TimeSeriesPoint[];  // 二次細分内の最大3時間雨量
  risk_timeline: RiskTimePoint[];  // 二次細分内の最大リスク
  level4_threshold?: number;  // 二次細分内のレベル4基準値の最大値
  swi_timeline?: TimeSeriesPoint[];  // 二次細分内のSWI最大値
}

export interface Prefecture {
  name: string;  // 都道府県名
  code: string;  // 都道府県コード
  areas: Area[];  // 地域データ（市町村）
  secondary_subdivisions?: SecondarySubdivision[];  // 二次細分リスト
  prefecture_rain_1hour_max_timeline?: TimeSeriesPoint[];  // 府県全体の最大1時間雨量
  prefecture_rain_3hour_timeline?: TimeSeriesPoint[];  // 府県全体の最大3時間雨量
  prefecture_risk_timeline?: RiskTimePoint[];  // 府県全体の最大リスク
  level4_threshold?: number;  // 府県内のレベル4基準値の最大値
  swi_timeline?: TimeSeriesPoint[];  // 府県内のSWI最大値
  rain_3hour_timeline?: TimeSeriesPoint[];  // 府県内の前3時間雨量最大値
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
  [RiskLevel.NORMAL]: '#FFFFFF',       // 白色（正常）
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

// セッションベースAPI用の型定義

export interface SessionInfo {
  session_id: string;
  created_at: string;               // ISO8601形式
  expires_at: string;               // ISO8601形式
  last_accessed: string;            // ISO8601形式
  swi_initial_time: string;         // SWI初期時刻
  guidance_initial_time: string;    // ガイダンス初期時刻
  guidance_type?: 'msm' | 'gsm';
  risk_rule?: RiskRule;
  prefecture_count: number;
  prefecture_codes: string[];
}

export interface LightweightCalculationResult {
  status: 'success' | 'error';
  session_id: string;               // セッションID
  swi_initial_time: string;         // SWI初期時刻（ISO8601）
  guidance_initial_time: string;    // ガイダンス初期時刻（ISO8601）
  guidance_type?: 'msm' | 'gsm';
  risk_rule?: RiskRule;
  available_prefectures: string[];  // 利用可能な府県コード
  available_times: number[];        // 利用可能なFT値
  used_urls?: {                     // 使用したGRIB2 URL
    swi_url: string;
    swi_initial_time: string;
    guidance_url: string;
    guidance_initial_time: string;
    guidance_type?: 'msm' | 'gsm';
    risk_rule?: RiskRule;
  };
}

// 軽量な府県データ（危険度時系列のみ）
export interface LightweightPrefectureData {
  name: string;
  code: string;
  level4_threshold?: number;
  swi_timeline?: TimeSeriesPoint[];
  rain_3hour_timeline?: TimeSeriesPoint[];
  areas: Array<{
    name: string;
    secondary_subdivision_name: string;
    risk_timeline: RiskTimePoint[];
    level4_threshold?: number;
    swi_timeline?: TimeSeriesPoint[];
    rain_3hour_timeline?: TimeSeriesPoint[];
  }>;
  secondary_subdivisions: Array<{
    name: string;
    area_names: string[];
    risk_timeline: RiskTimePoint[];
    level4_threshold?: number;
    swi_timeline?: TimeSeriesPoint[];
    rain_3hour_timeline?: TimeSeriesPoint[];
  }>;
  prefecture_risk_timeline: RiskTimePoint[];
}

export interface PrefectureDataResponse {
  status: 'success' | 'error';
  prefecture: LightweightPrefectureData;  // 軽量データに変更
  error?: string;
}

export interface RiskAtTimeResponse {
  status: 'success' | 'error';
  ft: number;
  mesh_risks: Record<string, number>;  // メッシュコード → リスク値
  mesh_coords?: Record<string, { lat: number; lon: number }>;  // メッシュコード → 座標（初回のみ、省略可）
  error?: string;
}

export interface MeshDetailResponse {
  status: 'success' | 'error';
  mesh: Mesh;
  error?: string;
}

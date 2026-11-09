import type { Mesh } from './api';
import type { TimeSeriesPoint, RiskTimePoint } from './api';
import type { AdjustmentMode, InputMode, RainfallViewMode, ScopeRainfall } from '../features/rainfall-adjustment/types';
import type { RegionCode } from '../features/production-session/regions';

export interface SessionInfo {
  session_id: string;
  created_at: string;
  expires_at: string;
  last_accessed: string;
  swi_initial_time: string;
  guidance_initial_time: string;
  guidance_type?: 'msm' | 'gsm';
  input_mode?: InputMode;
  adjustment_mode?: AdjustmentMode;
  prefecture_count: number;
  prefecture_codes: string[];
  prefecture_details?: Array<{
    code: string;
    name: string;
  }>;
}

export interface LightweightCalculationResult {
  status: 'success' | 'error';
  session_id: string;
  swi_initial_time: string;
  guidance_initial_time: string;
  guidance_type?: 'msm' | 'gsm';
  region?: RegionCode;
  available_prefectures: string[];
  available_prefecture_details?: Array<{
    code: string;
    name: string;
  }>;
  available_times: number[];
  used_urls?: {
    swi_url: string;
    swi_initial_time: string;
    guidance_url: string;
    guidance_initial_time: string;
    guidance_type?: 'msm' | 'gsm';
    region?: RegionCode;
  };
}

export interface LightweightPrefectureData {
  name: string;
  code: string;
  swi_timeline?: TimeSeriesPoint[];
  rain_3hour_timeline?: TimeSeriesPoint[];
  areas: Array<{
    name: string;
    secondary_subdivision_name: string;
    risk_timeline: RiskTimePoint[];
    swi_timeline?: TimeSeriesPoint[];
    rain_3hour_timeline?: TimeSeriesPoint[];
  }>;
  secondary_subdivisions: Array<{
    name: string;
    area_names: string[];
    risk_timeline: RiskTimePoint[];
    swi_timeline?: TimeSeriesPoint[];
    rain_3hour_timeline?: TimeSeriesPoint[];
  }>;
  prefecture_risk_timeline: RiskTimePoint[];
}

export interface PrefectureDataResponse {
  status: 'success' | 'error';
  prefecture: LightweightPrefectureData;
  error?: string;
}

export interface RiskAtTimeResponse {
  status: 'success' | 'error';
  ft: number;
  mesh_risks: Record<string, number>;
  mesh_coords: Record<string, { lat: number; lon: number }>;
  error?: string;
}

export interface MeshDetailResponse {
  status: 'success' | 'error';
  mesh: Mesh;
  error?: string;
}

export interface SnakeLineResponse {
  status: 'success' | 'error';
  mesh_code: string;
  lat: number;
  lon: number;
  advisory_bound: number;
  dosyakei_bound: number | null;
  level4_curve: number[] | null;
  swi_hourly_timeline: TimeSeriesPoint[];
  rain_1hour_timeline: TimeSeriesPoint[];
  error?: string;
}

export interface RainfallDataResponse {
  adjustment_scope?: RainfallViewMode;
  scope_rainfall?: ScopeRainfall;
  scope_errors?: Partial<Record<RainfallViewMode, string>>;
  area_rainfall: Record<string, TimeSeriesPoint[]>;
  subdivision_rainfall: Record<string, TimeSeriesPoint[]>;
  area_rainfall_24hour?: Record<string, TimeSeriesPoint[]>;
  subdivision_rainfall_24hour?: Record<string, TimeSeriesPoint[]>;
  guidance_type?: 'msm' | 'gsm';
  input_mode?: InputMode;
  adjustment_mode?: AdjustmentMode;
}

export interface RecalculateResponse {
  session_id: string;
  adjusted: boolean;
  ft: number;
  mesh_risks: Record<string, number>;
  mesh_coords: Record<string, { lat: number; lon: number }>;
}

export interface AdjustedRainfallPreviewMesh {
  lat: number;
  lon: number;
  rain_3hour: Array<number | null>;
  rain_1hour_max: Array<number | null>;
}

export interface AdjustedRainfallPreviewResponse {
  display_hours: 24 | 48 | 72;
  times: number[];
  meshes: Record<string, AdjustedRainfallPreviewMesh>;
  mesh_count: number;
}

export interface RecalculateRequest {
  adjustment_scope?: RainfallViewMode;
  adjustments: Record<string, Array<{ ft: number; value: number }>>;
  aggregate_adjustments?: Record<string, Array<{ ft: number; value: number }>>;
  input_mode?: InputMode;
  adjustment_mode?: AdjustmentMode;
  swi_initial: string;
  guidance_initial: string;
  data_source: string;
  guidance_type?: 'msm' | 'gsm';
}

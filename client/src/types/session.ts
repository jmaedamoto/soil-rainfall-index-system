import type { Mesh, RiskRule } from './api';
import type { TimeSeriesPoint, RiskTimePoint } from './api';
import type { AdjustmentMode, InputMode } from '../features/rainfall-adjustment/types';

export interface SessionInfo {
  session_id: string;
  created_at: string;
  expires_at: string;
  last_accessed: string;
  swi_initial_time: string;
  guidance_initial_time: string;
  guidance_type?: 'msm' | 'gsm';
  risk_rule?: RiskRule;
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
  risk_rule?: RiskRule;
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
    risk_rule?: RiskRule;
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

export interface RainfallDataResponse {
  area_rainfall: Record<string, TimeSeriesPoint[]>;
  subdivision_rainfall: Record<string, TimeSeriesPoint[]>;
  area_orders?: Record<string, string[]>;
  subdivision_orders?: Record<string, string[]>;
  area_rainfall_24hour?: Record<string, TimeSeriesPoint[]>;
  subdivision_rainfall_24hour?: Record<string, TimeSeriesPoint[]>;
  guidance_type?: 'msm' | 'gsm';
  risk_rule?: RiskRule;
  input_mode?: InputMode;
  adjustment_mode?: AdjustmentMode;
}

export interface RecalculateResponse {
  session_id: string;
  adjusted: boolean;
  ft: number;
  guidance_type?: 'msm' | 'gsm';
  risk_rule?: RiskRule;
  mesh_risks: Record<string, number>;
  mesh_coords: Record<string, { lat: number; lon: number }>;
}

export interface RecalculateRequest {
  adjustments: Record<string, Array<{ ft: number; value: number }>>;
  aggregate_adjustments?: Record<string, Array<{ ft: number; value: number }>>;
  input_mode?: InputMode;
  adjustment_mode?: AdjustmentMode;
  swi_initial: string;
  guidance_initial: string;
  data_source: string;
  guidance_type?: 'msm' | 'gsm';
  risk_rule?: RiskRule;
}

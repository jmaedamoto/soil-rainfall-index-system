import type { CacheInfo, Mesh } from './api';
import type { TimeSeriesPoint, RiskTimePoint } from './api';
import type { AdjustmentMode } from '../features/rainfall-adjustment/types';

export interface SessionInfo {
  session_id: string;
  created_at: string;
  expires_at: string;
  last_accessed: string;
  swi_initial_time: string;
  guidance_initial_time: string;
  adjustment_mode?: AdjustmentMode;
  prefecture_count: number;
  prefecture_codes: string[];
}

export interface LightweightCalculationResult {
  status: 'success' | 'error';
  session_id: string;
  swi_initial_time: string;
  guidance_initial_time: string;
  available_prefectures: string[];
  available_times: number[];
  cache_info?: CacheInfo;
  used_urls?: {
    swi_url: string;
    swi_initial_time: string;
    guidance_url: string;
    guidance_initial_time: string;
  };
}

export interface LightweightPrefectureData {
  name: string;
  code: string;
  areas: Array<{
    name: string;
    secondary_subdivision_name: string;
    risk_timeline: RiskTimePoint[];
  }>;
  secondary_subdivisions: Array<{
    name: string;
    area_names: string[];
    risk_timeline: RiskTimePoint[];
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
  mesh_coords?: Record<string, { lat: number; lon: number }>;
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
  adjustment_mode?: AdjustmentMode;
}

export interface RecalculateResponse {
  session_id: string;
  adjusted: boolean;
  ft: number;
  mesh_risks: Record<string, number>;
  mesh_coords: Record<string, { lat: number; lon: number }>;
}

export interface RecalculateRequest {
  adjustments: Record<string, Array<{ ft: number; value: number }>>;
  adjustment_mode?: AdjustmentMode;
  swi_initial: string;
  guidance_initial: string;
  data_source: string;
}

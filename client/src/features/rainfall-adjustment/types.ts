import type { TimeSeriesPoint } from '../../types/api';

export interface CellSelection {
  areaName: string;
  ft: number;
}

export type RainfallMap = Record<string, TimeSeriesPoint[]>;

export type RainfallViewMode = 'municipality' | 'subdivision' | 'primary' | 'prefecture';

export type InputMode = '3hour' | '24hour';

export type AdjustmentMode =
  | 'ratio_3hour'
  | 'fill_3hour'
  | 'fill_3hour_area_max'
  | 'fill_24hour_uniform'
  | 'ratio_24hour_uniform'
  | 'fill_24hour_peak_mesh'
  | 'ratio_24hour_peak_mesh';

export type ScopeRainfall = Partial<Record<RainfallViewMode, Record<InputMode, RainfallMap>>>;

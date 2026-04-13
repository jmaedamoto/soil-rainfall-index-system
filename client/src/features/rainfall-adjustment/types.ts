import type { TimeSeriesPoint } from '../../types/api';

export interface CellSelection {
  areaName: string;
  ft: number;
}

export type RainfallMap = Record<string, TimeSeriesPoint[]>;

export type RainfallViewMode = 'municipality' | 'subdivision';

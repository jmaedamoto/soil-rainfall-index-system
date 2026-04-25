import type { TimeSeriesPoint } from '../../types/api';
import type { AdjustmentMode, InputMode, RainfallMap } from './types';

export const WINDOW_24H_SERIES: ReadonlyArray<TimeSeriesPoint> = [
  { ft: 24, value: 0 },
  { ft: 48, value: 0 },
] as const;

export const getCellKey = (areaName: string, ft: number) => `${areaName}:${ft}`;

export const cloneRainfallMap = (rainfall: RainfallMap): RainfallMap =>
  JSON.parse(JSON.stringify(rainfall));

export const groupRainfallByPrefecture = (
  rainfall: RainfallMap
): Record<string, Record<string, TimeSeriesPoint[]>> => {
  const grouped: Record<string, Record<string, TimeSeriesPoint[]>> = {};

  Object.entries(rainfall).forEach(([areaName, timeseries]) => {
    const parts = areaName.split('_');
    if (parts.length < 2) return;

    const prefName = parts[0];
    if (!grouped[prefName]) {
      grouped[prefName] = {};
    }
    grouped[prefName][areaName] = timeseries;
  });

  return grouped;
};

export const countModifiedCells = (
  originalData: RainfallMap,
  adjustedData: RainfallMap
): number => {
  let count = 0;

  Object.entries(adjustedData).forEach(([areaName, timeseries]) => {
    const originalTimeseries = originalData[areaName];
    if (!originalTimeseries) return;

    timeseries.forEach((point, index) => {
      if (Math.abs(point.value - originalTimeseries[index].value) > 0.01) {
        count += 1;
      }
    });
  });

  return count;
};

export const buildRainfallAdjustments = (
  originalData: RainfallMap,
  adjustedData: RainfallMap
): RainfallMap => {
  const adjustments: RainfallMap = {};

  Object.entries(adjustedData).forEach(([areaName, timeseries]) => {
    const originalTimeseries = originalData[areaName];
    if (!originalTimeseries) return;

    const hasChange = timeseries.some(
      (point, index) => Math.abs(point.value - originalTimeseries[index].value) > 0.01
    );

    if (hasChange) {
      adjustments[areaName] = timeseries;
    }
  });

  return adjustments;
};

export const getDefaultAdjustmentMode = (inputMode: InputMode): AdjustmentMode =>
  inputMode === '24hour' ? 'ratio_24hour_uniform' : 'ratio_3hour';

export const getAllowedAdjustmentModes = (inputMode: InputMode): AdjustmentMode[] =>
  inputMode === '24hour'
    ? ['fill_24hour_uniform', 'ratio_24hour_uniform', 'ratio_24hour_peak_mesh']
    : ['ratio_3hour', 'fill_3hour'];

export const getAdjustmentModeLabel = (mode: AdjustmentMode): string => {
  switch (mode) {
    case 'ratio_3hour':
      return '比率補正';
    case 'fill_3hour':
      return '塗りつぶし';
    case 'fill_24hour_uniform':
      return '均等按分して塗りつぶし';
    case 'ratio_24hour_uniform':
      return '均等按分して比率補正';
    case 'ratio_24hour_peak_mesh':
      return '最大24時間格子基準で比率補正';
  }
};

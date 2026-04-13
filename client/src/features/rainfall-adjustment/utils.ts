import type { TimeSeriesPoint } from '../../types/api';
import type { RainfallMap } from './types';

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

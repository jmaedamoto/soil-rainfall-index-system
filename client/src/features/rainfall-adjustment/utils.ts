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
    ? ['fill_24hour_uniform', 'ratio_24hour_uniform', 'fill_24hour_peak_mesh', 'ratio_24hour_peak_mesh']
    : ['ratio_3hour', 'fill_3hour', 'fill_3hour_area_max'];

export const getAdjustmentModeLabel = (mode: AdjustmentMode): string => {
  switch (mode) {
    case 'ratio_3hour':
      return '比率補正';
    case 'fill_3hour':
      return '塗りつぶし';
    case 'fill_3hour_area_max':
      return '雨量を変えずに塗りつぶす';
    case 'fill_24hour_uniform':
      return '均等按分して塗りつぶし';
    case 'ratio_24hour_uniform':
      return '均等按分して比率補正';
    case 'fill_24hour_peak_mesh':
      return '最大24時間格子の時間分布で塗りつぶし';
    case 'ratio_24hour_peak_mesh':
      return '最大24時間格子基準で比率補正';
  }
};

export const getAdjustmentModeDescription = (mode: AdjustmentMode): string => {
  switch (mode) {
    case 'ratio_3hour':
      return '市町村または二次細分の代表3時間雨量に対する入力値の比率を求め、対象メッシュの同じ時刻の雨量にその比率を掛けます。元の時間分布とメッシュ間の大小関係を保ちたい場合に使います。';
    case 'fill_3hour':
      return '選択した時刻の対象メッシュ雨量を入力値で塗りつぶします。複数の領域にまたがるメッシュは、同じ時刻で大きい入力値を採用します。';
    case 'fill_3hour_area_max':
      return 'ガイダンスの時系列は変えず、各市町村内で時刻ごとに最大雨量の格子値を求め、その値で同じ市町村内の全格子を塗りつぶします。';
    case 'fill_24hour_uniform':
      return '入力した24時間合計雨量を8つの3時間区間に均等に分け、対象メッシュをその値で塗りつぶします。時間分布を指定しない単純な一括入力向けです。';
    case 'ratio_24hour_uniform':
      return '入力した24時間合計雨量を8つの3時間区間に均等に分け、各時刻で比率補正します。元のメッシュ差を残しながら24時間総量を反映します。';
    case 'fill_24hour_peak_mesh':
      return '対象領域で24時間合計が最大のメッシュの時間分布を使い、入力した24時間合計になるよう各時刻へ配分して塗りつぶします。ピークの出方を反映したい場合に使います。';
    case 'ratio_24hour_peak_mesh':
      return '対象領域で24時間合計が最大のメッシュを基準に、入力した24時間合計へ合わせる比率を求めて補正します。代表的な時間分布とメッシュ差の両方を残したい場合に使います。';
  }
};

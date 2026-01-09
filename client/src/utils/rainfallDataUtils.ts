import { TimeSeriesPoint } from '../types/api';

/**
 * 雨量データ処理のユーティリティ
 */

export class RainfallDataUtils {
  /**
   * 府県別にデータをグループ化（市町村または二次細分）
   */
  static groupByPrefecture(
    data: Record<string, TimeSeriesPoint[]>
  ): Record<string, Record<string, TimeSeriesPoint[]>> {
    const grouped: Record<string, Record<string, TimeSeriesPoint[]>> = {};

    Object.entries(data).forEach(([key, timeseries]) => {
      const parts = key.split('_');
      if (parts.length >= 2) {
        const prefName = parts[0];
        if (!grouped[prefName]) {
          grouped[prefName] = {};
        }
        grouped[prefName][key] = timeseries;
      }
    });

    return grouped;
  }

  /**
   * FT値のリストを取得（タイムラインの時刻）
   */
  static getFtValues(timeseries: TimeSeriesPoint[]): number[] {
    return timeseries.map(p => p.ft);
  }

  /**
   * 調整データを配列形式に変換（API送信用）
   */
  static convertToApiFormat(
    rainfall: Record<string, TimeSeriesPoint[]>
  ): Record<string, Array<{ ft: number; value: number }>> {
    const adjustments: Record<string, Array<{ ft: number; value: number }>> = {};

    Object.entries(rainfall).forEach(([areaName, timeseries]) => {
      adjustments[areaName] = timeseries;
    });

    return adjustments;
  }

  /**
   * データをディープコピー
   */
  static deepCopy<T>(data: T): T {
    return JSON.parse(JSON.stringify(data));
  }

  /**
   * 単一セルの値を更新
   */
  static updateCellValue(
    data: Record<string, TimeSeriesPoint[]>,
    areaName: string,
    ft: number,
    value: number
  ): Record<string, TimeSeriesPoint[]> {
    const updated = { ...data };
    const areaData = updated[areaName];

    if (areaData) {
      updated[areaName] = areaData.map(point =>
        point.ft === ft ? { ...point, value: Math.round(value) } : point
      );
    }

    return updated;
  }

  /**
   * データをリセット（元の値に戻す）
   */
  static resetToOriginal(
    originalData: Record<string, TimeSeriesPoint[]>
  ): Record<string, TimeSeriesPoint[]> {
    return this.deepCopy(originalData);
  }

  /**
   * セルが修正されているかチェック
   */
  static isCellModified(
    originalValue: number,
    currentValue: number,
    tolerance: number = 0.01
  ): boolean {
    return Math.abs(originalValue - currentValue) > tolerance;
  }
}

/**
 * Excelライクなセル選択ロジックのユーティリティ
 */

export interface CellSelection {
  areaName: string;
  ft: number;
}

export class CellSelectionManager {
  /**
   * セルキーを生成
   */
  static getCellKey(areaName: string, ft: number): string {
    return `${areaName}:${ft}`;
  }

  /**
   * セルキーをパース
   */
  static parseCellKey(cellKey: string): CellSelection | null {
    const [areaName, ftStr] = cellKey.split(':');
    const ft = parseInt(ftStr);

    if (isNaN(ft)) {
      return null;
    }

    return { areaName, ft };
  }

  /**
   * 単一セル選択
   */
  static selectSingle(areaName: string, ft: number): Set<string> {
    return new Set([this.getCellKey(areaName, ft)]);
  }

  /**
   * トグル選択（Ctrl/Cmd + クリック）
   */
  static toggleSelection(
    currentSelection: Set<string>,
    areaName: string,
    ft: number
  ): Set<string> {
    const key = this.getCellKey(areaName, ft);
    const newSelection = new Set(currentSelection);

    if (newSelection.has(key)) {
      newSelection.delete(key);
    } else {
      newSelection.add(key);
    }

    return newSelection;
  }

  /**
   * 範囲選択（Shift + クリック、またはドラッグ）
   */
  static selectRange(
    start: CellSelection,
    end: CellSelection,
    areaNames: string[],
    ftValues: number[]
  ): Set<string> {
    const startAreaIndex = areaNames.indexOf(start.areaName);
    const endAreaIndex = areaNames.indexOf(end.areaName);

    if (startAreaIndex === -1 || endAreaIndex === -1) {
      return new Set();
    }

    const startFtIndex = ftValues.indexOf(start.ft);
    const endFtIndex = ftValues.indexOf(end.ft);

    if (startFtIndex === -1 || endFtIndex === -1) {
      return new Set();
    }

    const minAreaIndex = Math.min(startAreaIndex, endAreaIndex);
    const maxAreaIndex = Math.max(startAreaIndex, endAreaIndex);
    const minFtIndex = Math.min(startFtIndex, endFtIndex);
    const maxFtIndex = Math.max(startFtIndex, endFtIndex);

    const newSelection = new Set<string>();

    for (let i = minAreaIndex; i <= maxAreaIndex; i++) {
      const areaName = areaNames[i];
      for (let j = minFtIndex; j <= maxFtIndex; j++) {
        const ft = ftValues[j];
        newSelection.add(this.getCellKey(areaName, ft));
      }
    }

    return newSelection;
  }

  /**
   * 選択されたセルに一括で値を適用
   */
  static applyBulkValue<T extends { ft: number; value: number }>(
    data: Record<string, T[]>,
    selectedCells: Set<string>,
    newValue: number
  ): Record<string, T[]> {
    const updated = { ...data };

    selectedCells.forEach(cellKey => {
      const cell = this.parseCellKey(cellKey);
      if (!cell) return;

      const { areaName, ft } = cell;

      if (updated[areaName]) {
        updated[areaName] = updated[areaName].map(point =>
          point.ft === ft ? { ...point, value: newValue } as T : point
        );
      }
    });

    return updated;
  }

  /**
   * 修正されたセルの数をカウント
   */
  static countModified<T extends { ft: number; value: number }>(
    originalData: Record<string, T[]>,
    adjustedData: Record<string, T[]>,
    tolerance: number = 0.01
  ): number {
    let count = 0;

    Object.entries(adjustedData).forEach(([areaName, timeseries]) => {
      const originalTimeseries = originalData[areaName];

      if (originalTimeseries) {
        timeseries.forEach((point, index) => {
          if (Math.abs(point.value - originalTimeseries[index].value) > tolerance) {
            count++;
          }
        });
      }
    });

    return count;
  }

  /**
   * 特定の府県内の修正数をカウント
   */
  static countModifiedInPrefix<T extends { ft: number; value: number }>(
    prefectureData: Record<string, T[]>,
    originalData: Record<string, T[]>,
    tolerance: number = 0.01
  ): number {
    let count = 0;

    Object.entries(prefectureData).forEach(([areaName, timeseries]) => {
      const originalTimeseries = originalData[areaName];

      if (originalTimeseries) {
        timeseries.forEach((point, index) => {
          if (Math.abs(point.value - originalTimeseries[index].value) > tolerance) {
            count++;
          }
        });
      }
    });

    return count;
  }
}

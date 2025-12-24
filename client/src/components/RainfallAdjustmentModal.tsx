import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { calculateWithAdjustedRainfall } from '../services/rainfallApi';
import { TimeSeriesPoint, CalculationResult, Prefecture } from '../types/api';

interface RainfallAdjustmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  swiInitial: string;
  guidanceInitial: string;
  dataSource: 'test' | 'production';
  existingData: Record<string, Prefecture> | null; // 既存の計算結果データ
  onResultCalculated: (result: CalculationResult) => void;
}

interface CellSelection {
  areaName: string;
  ft: number;
}

const RainfallAdjustmentModal: React.FC<RainfallAdjustmentModalProps> = ({
  isOpen,
  onClose,
  swiInitial,
  guidanceInitial,
  dataSource: _dataSource,
  existingData,
  onResultCalculated
}) => {
  const [originalRainfall, setOriginalRainfall] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [adjustedRainfall, setAdjustedRainfall] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [originalSubdivisionRainfall, setOriginalSubdivisionRainfall] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [adjustedSubdivisionRainfall, setAdjustedSubdivisionRainfall] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<'loading' | 'editing' | 'calculating'>('loading');
  const [selectedPrefecture, setSelectedPrefecture] = useState<string>('');
  const [viewMode, setViewMode] = useState<'municipality' | 'subdivision'>('municipality');

  // セル選択状態
  const [selectedCells, setSelectedCells] = useState<Set<string>>(new Set());
  const [selectionStart, setSelectionStart] = useState<CellSelection | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const [bulkEditValue, setBulkEditValue] = useState<string>('');
  const [showBulkEdit, setShowBulkEdit] = useState(false);

  // 府県別にグループ化（市町村）
  const rainfallByPrefecture = useMemo(() => {
    const grouped: Record<string, Record<string, TimeSeriesPoint[]>> = {};

    Object.entries(adjustedRainfall).forEach(([areaName, timeseries]) => {
      const parts = areaName.split('_');
      if (parts.length >= 2) {
        const prefName = parts[0];
        if (!grouped[prefName]) {
          grouped[prefName] = {};
        }
        grouped[prefName][areaName] = timeseries;
      }
    });

    return grouped;
  }, [adjustedRainfall]);

  // 府県別にグループ化（二次細分）
  const subdivisionRainfallByPrefecture = useMemo(() => {
    const grouped: Record<string, Record<string, TimeSeriesPoint[]>> = {};
    Object.entries(adjustedSubdivisionRainfall).forEach(([subdivName, timeseries]) => {
      const parts = subdivName.split('_');
      if (parts.length >= 2) {
        const prefName = parts[0];
        if (!grouped[prefName]) {
          grouped[prefName] = {};
        }
        grouped[prefName][subdivName] = timeseries;
      }
    });
    return grouped;
  }, [adjustedSubdivisionRainfall]);

  // セルキーを生成
  const getCellKey = (areaName: string, ft: number) => `${areaName}:${ft}`;

  // モーダルが開かれたときの初期化
  useEffect(() => {
    if (isOpen) {
      setStep('loading');
      setSelectedCells(new Set());
      setError(null);
    }
  }, [isOpen]);

  // セルが選択されているか判定
  const isCellSelected = (areaName: string, ft: number) => {
    return selectedCells.has(getCellKey(areaName, ft));
  };

  // セルクリックハンドラ
  const handleCellMouseDown = (areaName: string, ft: number, e: React.MouseEvent) => {
    e.preventDefault();

    if (e.ctrlKey || e.metaKey) {
      // Ctrl/Cmd + クリック: トグル選択
      const key = getCellKey(areaName, ft);
      const newSelected = new Set(selectedCells);
      if (newSelected.has(key)) {
        newSelected.delete(key);
      } else {
        newSelected.add(key);
      }
      setSelectedCells(newSelected);
    } else if (e.shiftKey && selectionStart) {
      // Shift + クリック: 範囲選択
      selectRange(selectionStart, { areaName, ft });
    } else {
      // 通常クリック: 単一選択
      setSelectedCells(new Set([getCellKey(areaName, ft)]));
      setSelectionStart({ areaName, ft });
      setIsSelecting(true);
    }
  };

  // セルドラッグハンドラ
  const handleCellMouseEnter = (areaName: string, ft: number) => {
    if (isSelecting && selectionStart) {
      selectRange(selectionStart, { areaName, ft });
    }
  };

  // マウスアップハンドラ
  const handleMouseUp = useCallback(() => {
    setIsSelecting(false);
  }, []);

  useEffect(() => {
    document.addEventListener('mouseup', handleMouseUp);
    return () => document.removeEventListener('mouseup', handleMouseUp);
  }, [handleMouseUp]);

  // 範囲選択
  const selectRange = (start: CellSelection, end: CellSelection) => {
    const currentData = viewMode === 'municipality'
      ? rainfallByPrefecture[selectedPrefecture] || {}
      : subdivisionRainfallByPrefecture[selectedPrefecture] || {};

    const areaNames = Object.keys(currentData);
    const startAreaIndex = areaNames.indexOf(start.areaName);
    const endAreaIndex = areaNames.indexOf(end.areaName);

    if (startAreaIndex === -1 || endAreaIndex === -1) return;

    const firstTimeseries = Object.values(currentData)[0];
    if (!firstTimeseries || firstTimeseries.length === 0) return;

    const ftValues = firstTimeseries.map(p => p.ft);
    const startFtIndex = ftValues.indexOf(start.ft);
    const endFtIndex = ftValues.indexOf(end.ft);

    const minAreaIndex = Math.min(startAreaIndex, endAreaIndex);
    const maxAreaIndex = Math.max(startAreaIndex, endAreaIndex);
    const minFtIndex = Math.min(startFtIndex, endFtIndex);
    const maxFtIndex = Math.max(startFtIndex, endFtIndex);

    const newSelected = new Set<string>();
    for (let i = minAreaIndex; i <= maxAreaIndex; i++) {
      const areaName = areaNames[i];
      for (let j = minFtIndex; j <= maxFtIndex; j++) {
        const ft = ftValues[j];
        newSelected.add(getCellKey(areaName, ft));
      }
    }

    setSelectedCells(newSelected);
  };

  // 一括編集を適用
  const applyBulkEdit = () => {
    const value = parseFloat(bulkEditValue);
    if (isNaN(value) || value < 0) {
      alert('0以上の数値を入力してください');
      return;
    }

    const intValue = Math.round(value);

    if (viewMode === 'municipality') {
      setAdjustedRainfall(prev => {
        const updated = { ...prev };
        selectedCells.forEach(cellKey => {
          const [areaName, ftStr] = cellKey.split(':');
          const ft = parseInt(ftStr);
          if (updated[areaName]) {
            updated[areaName] = updated[areaName].map(point =>
              point.ft === ft ? { ...point, value: intValue } : point
            );
          }
        });
        return updated;
      });
    } else {
      setAdjustedSubdivisionRainfall(prev => {
        const updated = { ...prev };
        selectedCells.forEach(cellKey => {
          const [areaName, ftStr] = cellKey.split(':');
          const ft = parseInt(ftStr);
          if (updated[areaName]) {
            updated[areaName] = updated[areaName].map(point =>
              point.ft === ft ? { ...point, value: intValue } : point
            );
          }
        });
        return updated;
      });
    }

    setShowBulkEdit(false);
    setBulkEditValue('');
    setSelectedCells(new Set());
  };

  // 単一セルの値変更
  const handleRainfallChange = (areaName: string, ft: number, value: string) => {
    const numValue = parseFloat(value);
    if (isNaN(numValue) || numValue < 0) return;

    const intValue = Math.round(numValue);

    if (viewMode === 'municipality') {
      setAdjustedRainfall(prev => {
        const updated = { ...prev };
        const areaData = updated[areaName];
        if (areaData) {
          updated[areaName] = areaData.map(point =>
            point.ft === ft ? { ...point, value: intValue } : point
          );
        }
        return updated;
      });
    } else {
      setAdjustedSubdivisionRainfall(prev => {
        const updated = { ...prev };
        const subdivData = updated[areaName];
        if (subdivData) {
          updated[areaName] = subdivData.map(point =>
            point.ft === ft ? { ...point, value: intValue } : point
          );
        }
        return updated;
      });
    }
  };

  // 元に戻す
  const resetToOriginal = () => {
    if (viewMode === 'municipality') {
      setAdjustedRainfall(JSON.parse(JSON.stringify(originalRainfall)));
    } else {
      setAdjustedSubdivisionRainfall(JSON.parse(JSON.stringify(originalSubdivisionRainfall)));
    }
    setSelectedCells(new Set());
  };

  // 既存データから雨量情報を抽出
  useEffect(() => {
    if (isOpen && step === 'loading' && existingData) {
      setLoading(true);
      setError(null);

      try {
        // 既存データから市町村別雨量を抽出
        const areaRainfall: Record<string, TimeSeriesPoint[]> = {};
        const subdivRainfall: Record<string, TimeSeriesPoint[]> = {};

        Object.values(existingData).forEach(prefecture => {
          // 市町村別
          prefecture.areas.forEach(area => {
            const areaKey = `${prefecture.name}_${area.name}`;

            if (area.meshes.length > 0) {
              // 市町村内の全メッシュから最大雨量を計算
              const ftSet = new Set<number>();
              area.meshes.forEach(mesh => {
                if (mesh.rain_timeline) {
                  mesh.rain_timeline.forEach(point => ftSet.add(point.ft));
                }
              });

              const timeline: TimeSeriesPoint[] = Array.from(ftSet).sort((a, b) => a - b).map(ft => {
                const maxValue = Math.max(
                  ...area.meshes
                    .map(mesh => mesh.rain_timeline?.find(p => p.ft === ft)?.value || 0)
                );
                return { ft, value: maxValue };
              });

              areaRainfall[areaKey] = timeline;
            }
          });

          // 二次細分別
          if (prefecture.secondary_subdivisions) {
            prefecture.secondary_subdivisions.forEach(subdiv => {
              const subdivKey = `${prefecture.name}_${subdiv.name}`;
              if (subdiv.rain_3hour_timeline) {
                subdivRainfall[subdivKey] = subdiv.rain_3hour_timeline.map(p => ({
                  ft: p.ft,
                  value: p.value
                }));
              }
            });
          }
        });

        setOriginalRainfall(areaRainfall);
        setAdjustedRainfall(JSON.parse(JSON.stringify(areaRainfall)));
        setOriginalSubdivisionRainfall(subdivRainfall);
        setAdjustedSubdivisionRainfall(JSON.parse(JSON.stringify(subdivRainfall)));

        const prefNames = Object.keys(existingData);
        if (prefNames.length > 0) {
          const firstPrefName = Object.values(existingData)[0].name; // Prefectureオブジェクトのname属性を使用
          setSelectedPrefecture(firstPrefName);
        }

        setStep('editing');
      } catch (err) {
        setError(err instanceof Error ? err.message : '雨量データの抽出に失敗しました');
      } finally {
        setLoading(false);
      }
    }
  }, [isOpen, step, existingData]);

  // 再計算実行
  const handleRecalculate = async () => {
    setStep('calculating');
    setError(null);

    try {
      const currentRainfall = viewMode === 'municipality' ? adjustedRainfall : adjustedSubdivisionRainfall;
      const adjustments: Record<string, Record<string, number>> = {};

      Object.entries(currentRainfall).forEach(([areaName, timeseries]) => {
        const areaAdjustments: Record<string, number> = {};
        timeseries.forEach(point => {
          areaAdjustments[point.ft.toString()] = point.value;
        });
        adjustments[areaName] = areaAdjustments;
      });

      const result = await calculateWithAdjustedRainfall({
        swi_initial: swiInitial,
        guidance_initial: guidanceInitial,
        area_adjustments: adjustments
      });

      onResultCalculated(result);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '再計算に失敗しました');
      setStep('editing');
    }
  };

  // 修正数カウント
  const totalModifiedCount = useMemo(() => {
    const originalData = viewMode === 'municipality' ? originalRainfall : originalSubdivisionRainfall;
    const adjustedData = viewMode === 'municipality' ? adjustedRainfall : adjustedSubdivisionRainfall;

    let count = 0;
    Object.entries(adjustedData).forEach(([areaName, timeseries]) => {
      const originalTimeseries = originalData[areaName];
      if (originalTimeseries) {
        timeseries.forEach((point, index) => {
          if (Math.abs(point.value - originalTimeseries[index].value) > 0.01) {
            count++;
          }
        });
      }
    });
    return count;
  }, [viewMode, originalRainfall, adjustedRainfall, originalSubdivisionRainfall, adjustedSubdivisionRainfall]);

  const currentPrefectureData = viewMode === 'municipality'
    ? rainfallByPrefecture[selectedPrefecture] || {}
    : subdivisionRainfallByPrefecture[selectedPrefecture] || {};

  const modifiedCountInPrefecture = useMemo(() => {
    const originalData = viewMode === 'municipality' ? originalRainfall : originalSubdivisionRainfall;

    let count = 0;
    Object.entries(currentPrefectureData).forEach(([areaName, timeseries]) => {
      const originalTimeseries = originalData[areaName];
      if (originalTimeseries) {
        timeseries.forEach((point, index) => {
          if (Math.abs(point.value - originalTimeseries[index].value) > 0.01) {
            count++;
          }
        });
      }
    });
    return count;
  }, [currentPrefectureData, viewMode, originalRainfall, originalSubdivisionRainfall]);

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 10000
    }}>
      <div style={{
        backgroundColor: 'white',
        width: '95vw',
        height: '90vh',
        borderRadius: '8px',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h2 style={{ margin: 0 }}>雨量調整</h2>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              backgroundColor: '#f5f5f5',
              border: '1px solid #ddd',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            閉じる
          </button>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div style={{
              border: '4px solid #f3f3f3',
              borderTop: '4px solid #1976D2',
              borderRadius: '50%',
              width: '40px',
              height: '40px',
              animation: 'spin 1s linear infinite',
              margin: '0 auto'
            }} />
            <p style={{ marginTop: '10px' }}>雨量データを読み込んでいます...</p>
          </div>
        )}

        {error && (
          <div style={{
            backgroundColor: '#ffebee',
            color: '#c62828',
            padding: '12px',
            borderRadius: '4px',
            marginBottom: '15px'
          }}>
            エラー: {error}
          </div>
        )}

        {step === 'editing' && (
          <>
            <div style={{ display: 'flex', gap: '15px', marginBottom: '15px', flexWrap: 'wrap', alignItems: 'center' }}>
              {/* 表示モード切り替え */}
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <label style={{ fontWeight: 'bold' }}>表示:</label>
                <button
                  onClick={() => { setViewMode('municipality'); setSelectedCells(new Set()); }}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: viewMode === 'municipality' ? '#1976D2' : '#f5f5f5',
                    color: viewMode === 'municipality' ? 'white' : 'black',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  市町村別
                </button>
                <button
                  onClick={() => { setViewMode('subdivision'); setSelectedCells(new Set()); }}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: viewMode === 'subdivision' ? '#1976D2' : '#f5f5f5',
                    color: viewMode === 'subdivision' ? 'white' : 'black',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  二次細分別
                </button>
              </div>

              {/* 府県選択 */}
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <label style={{ fontWeight: 'bold' }}>府県:</label>
                <select
                  value={selectedPrefecture}
                  onChange={(e) => { setSelectedPrefecture(e.target.value); setSelectedCells(new Set()); }}
                  style={{
                    padding: '8px 12px',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                >
                  {Object.keys(viewMode === 'municipality' ? rainfallByPrefecture : subdivisionRainfallByPrefecture).map(prefName => (
                    <option key={prefName} value={prefName}>{prefName}</option>
                  ))}
                </select>
              </div>

              {/* セル選択情報 */}
              {selectedCells.size > 0 && (
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <span style={{ fontWeight: 'bold' }}>選択中: {selectedCells.size}セル</span>
                  <button
                    onClick={() => setShowBulkEdit(true)}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#4CAF50',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    一括編集
                  </button>
                  <button
                    onClick={() => setSelectedCells(new Set())}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#f5f5f5',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    選択解除
                  </button>
                </div>
              )}
            </div>

            {/* 一括編集ダイアログ */}
            {showBulkEdit && (
              <div style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100vw',
                height: '100vh',
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                zIndex: 20000
              }}>
                <div style={{
                  backgroundColor: 'white',
                  padding: '30px',
                  borderRadius: '8px',
                  minWidth: '400px'
                }}>
                  <h3>一括編集</h3>
                  <p>{selectedCells.size}個のセルに同じ値を設定します</p>
                  <div style={{ marginTop: '20px', marginBottom: '20px' }}>
                    <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                      雨量 (mm):
                    </label>
                    <input
                      type="number"
                      step="1"
                      min="0"
                      value={bulkEditValue}
                      onChange={(e) => setBulkEditValue(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '16px'
                      }}
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          applyBulkEdit();
                        } else if (e.key === 'Escape') {
                          setShowBulkEdit(false);
                          setBulkEditValue('');
                        }
                      }}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                    <button
                      onClick={() => { setShowBulkEdit(false); setBulkEditValue(''); }}
                      style={{
                        padding: '10px 20px',
                        backgroundColor: '#f5f5f5',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      キャンセル
                    </button>
                    <button
                      onClick={applyBulkEdit}
                      style={{
                        padding: '10px 20px',
                        backgroundColor: '#1976D2',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      適用
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* 統計情報 */}
            <div style={{
              padding: '12px',
              backgroundColor: '#f5f5f5',
              borderRadius: '4px',
              marginBottom: '15px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <span style={{ marginRight: '20px' }}>
                  表示中: {selectedPrefecture} - 全{Object.keys(currentPrefectureData).length}{viewMode === 'municipality' ? '市町村' : '二次細分'}
                </span>
                <span style={{ marginRight: '20px' }}>
                  現在の府県の修正数: {modifiedCountInPrefecture}セル
                </span>
                <span style={{ fontWeight: 'bold', color: totalModifiedCount > 0 ? '#d32f2f' : '#666' }}>
                  全体の修正数: {totalModifiedCount}セル
                </span>
              </div>
              <button
                onClick={resetToOriginal}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#ff9800',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                元に戻す
              </button>
            </div>

            {/* Excelライクな表 */}
            <div style={{
              flex: 1,
              overflow: 'auto',
              border: '1px solid #ddd',
              borderRadius: '4px',
              userSelect: 'none'
            }}>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '13px',
                tableLayout: 'fixed'
              }}>
                <thead style={{ position: 'sticky', top: 0, backgroundColor: '#1976D2', color: 'white', zIndex: 10 }}>
                  <tr>
                    <th style={{
                      padding: '10px 8px',
                      borderRight: '2px solid #fff',
                      textAlign: 'left',
                      fontWeight: 'bold',
                      width: '200px',
                      position: 'sticky',
                      left: 0,
                      backgroundColor: '#1976D2',
                      zIndex: 11
                    }}>
                      {viewMode === 'municipality' ? '市町村名' : '二次細分名'}
                    </th>
                    {Object.keys(currentPrefectureData).length > 0 &&
                      currentPrefectureData[Object.keys(currentPrefectureData)[0]]?.map(point => (
                        <th key={point.ft} style={{
                          padding: '10px 8px',
                          borderRight: '1px solid #fff',
                          textAlign: 'center',
                          fontWeight: 'bold',
                          minWidth: '80px'
                        }}>
                          FT{point.ft}
                        </th>
                      ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(currentPrefectureData).map(([areaName, timeseries]) => {
                    const originalData = viewMode === 'municipality' ? originalRainfall : originalSubdivisionRainfall;
                    return (
                      <tr key={areaName} style={{ borderBottom: '1px solid #eee' }}>
                        <td style={{
                          padding: '8px',
                          fontWeight: 'bold',
                          backgroundColor: '#f5f5f5',
                          borderRight: '2px solid #ddd',
                          position: 'sticky',
                          left: 0,
                          zIndex: 9
                        }}>
                          {areaName.split('_')[1] || areaName}
                        </td>
                        {timeseries.map(point => {
                          const originalPoint = originalData[areaName]?.find(p => p.ft === point.ft);
                          const isModified = originalPoint && Math.abs(originalPoint.value - point.value) > 0.01;
                          const isSelected = isCellSelected(areaName, point.ft);

                          return (
                            <td
                              key={point.ft}
                              style={{
                                padding: '4px',
                                borderRight: '1px solid #eee',
                                textAlign: 'center',
                                backgroundColor: isSelected
                                  ? '#e3f2fd'
                                  : isModified
                                  ? '#fff3cd'
                                  : 'white',
                                border: isSelected ? '2px solid #1976D2' : '1px solid #eee',
                                cursor: 'cell'
                              }}
                              onMouseDown={(e) => handleCellMouseDown(areaName, point.ft, e)}
                              onMouseEnter={() => handleCellMouseEnter(areaName, point.ft)}
                            >
                              <input
                                type="number"
                                step="1"
                                min="0"
                                value={Math.round(point.value)}
                                onChange={(e) => handleRainfallChange(areaName, point.ft, e.target.value)}
                                className="rainfall-input"
                                style={{
                                  width: '100%',
                                  padding: '6px',
                                  border: 'none',
                                  borderRadius: '0',
                                  textAlign: 'center',
                                  backgroundColor: 'transparent',
                                  fontSize: '13px',
                                  fontWeight: isModified ? 'bold' : 'normal'
                                }}
                                onClick={(e) => e.stopPropagation()}
                              />
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* 操作ヘルプ */}
            <div style={{
              marginTop: '10px',
              padding: '10px',
              backgroundColor: '#e3f2fd',
              borderRadius: '4px',
              fontSize: '12px'
            }}>
              <strong>操作方法:</strong>
              クリック=単一選択 | ドラッグ=範囲選択 | Ctrl+クリック=複数選択 | Shift+クリック=範囲拡張
            </div>

            {/* ボタン */}
            <div style={{ display: 'flex', gap: '10px', marginTop: '15px', justifyContent: 'flex-end' }}>
              <button
                onClick={onClose}
                style={{
                  padding: '10px 24px',
                  backgroundColor: '#f5f5f5',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                キャンセル
              </button>
              <button
                onClick={handleRecalculate}
                disabled={totalModifiedCount === 0}
                style={{
                  padding: '10px 24px',
                  backgroundColor: totalModifiedCount > 0 ? '#1976D2' : '#ccc',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: totalModifiedCount > 0 ? 'pointer' : 'not-allowed',
                  fontSize: '14px',
                  fontWeight: 'bold'
                }}
              >
                再計算実行 ({totalModifiedCount}セル修正)
              </button>
            </div>
          </>
        )}

        {step === 'calculating' && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div style={{
              border: '4px solid #f3f3f3',
              borderTop: '4px solid #1976D2',
              borderRadius: '50%',
              width: '40px',
              height: '40px',
              animation: 'spin 1s linear infinite',
              margin: '0 auto'
            }} />
            <p style={{ marginTop: '10px' }}>調整後の雨量で再計算中...</p>
            <p style={{ fontSize: '12px', color: '#666' }}>
              調整対象: {totalModifiedCount}セル
            </p>
          </div>
        )}

        <style>
          {`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }

            /* 雨量入力フィールドのスピナー（矢印ボタン）を非表示 */
            input.rainfall-input::-webkit-outer-spin-button,
            input.rainfall-input::-webkit-inner-spin-button {
              -webkit-appearance: none;
              margin: 0;
            }
            input.rainfall-input[type=number] {
              -moz-appearance: textfield;
            }

            /* セル入力フォーカス時のスタイル */
            input.rainfall-input:focus {
              outline: 2px solid #1976D2;
              outline-offset: -2px;
            }
          `}
        </style>
      </div>
    </div>
  );
};

export default RainfallAdjustmentModal;

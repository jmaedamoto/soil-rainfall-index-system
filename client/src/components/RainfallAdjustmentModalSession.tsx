import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { sessionApiClient } from '../services/sessionApi';
import type { TimeSeriesPoint } from '../types/api';
import type { AdjustmentMode, CellSelection, InputMode, RainfallViewMode } from '../features/rainfall-adjustment/types';
import {
  buildRainfallAdjustments,
  cloneRainfallMap,
  countModifiedCells,
  getAdjustmentModeLabel,
  getAllowedAdjustmentModes,
  getDefaultAdjustmentMode,
  getCellKey,
  groupRainfallByPrefecture,
} from '../features/rainfall-adjustment/utils';

interface RainfallAdjustmentModalSessionProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  swiInitial: string;
  guidanceInitial: string;
  dataSource: 'test' | 'production';
  onSessionRecalculated: (sessionId: string, meshRisks: Record<string, number>, meshCoords: Record<string, { lat: number; lon: number }>) => void;
}

const RainfallAdjustmentModalSession: React.FC<RainfallAdjustmentModalSessionProps> = ({
  isOpen,
  onClose,
  sessionId,
  swiInitial,
  guidanceInitial,
  dataSource,
  onSessionRecalculated
}) => {
  const [originalRainfall, setOriginalRainfall] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [adjustedRainfall, setAdjustedRainfall] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [originalSubdivisionRainfall, setOriginalSubdivisionRainfall] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [adjustedSubdivisionRainfall, setAdjustedSubdivisionRainfall] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [originalRainfall24Hour, setOriginalRainfall24Hour] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [adjustedRainfall24Hour, setAdjustedRainfall24Hour] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [originalSubdivisionRainfall24Hour, setOriginalSubdivisionRainfall24Hour] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [adjustedSubdivisionRainfall24Hour, setAdjustedSubdivisionRainfall24Hour] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<'loading' | 'editing' | 'calculating'>('loading');
  const [selectedPrefecture, setSelectedPrefecture] = useState<string>('');
  const [viewMode, setViewMode] = useState<RainfallViewMode>('municipality');
  const [inputMode, setInputMode] = useState<InputMode>('3hour');
  const [adjustmentMode, setAdjustmentMode] = useState<AdjustmentMode>('ratio_3hour');

  // セル選択状態
  const [selectedCells, setSelectedCells] = useState<Set<string>>(new Set());
  const [selectionStart, setSelectionStart] = useState<CellSelection | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const [bulkEditValue, setBulkEditValue] = useState<string>('');
  const [showBulkEdit, setShowBulkEdit] = useState(false);

  // 府県別にグループ化（市町村）
  const rainfallByPrefecture = useMemo(() => {
    return groupRainfallByPrefecture(adjustedRainfall);
  }, [adjustedRainfall]);

  // 府県別にグループ化（二次細分）
  const subdivisionRainfallByPrefecture = useMemo(() => {
    return groupRainfallByPrefecture(adjustedSubdivisionRainfall);
  }, [adjustedSubdivisionRainfall]);

  const rainfall24HourByPrefecture = useMemo(() => {
    return groupRainfallByPrefecture(adjustedRainfall24Hour);
  }, [adjustedRainfall24Hour]);

  const subdivisionRainfall24HourByPrefecture = useMemo(() => {
    return groupRainfallByPrefecture(adjustedSubdivisionRainfall24Hour);
  }, [adjustedSubdivisionRainfall24Hour]);

  // モーダルが開かれたときの初期化
  useEffect(() => {
    if (isOpen) {
      setStep('loading');
      setSelectedCells(new Set());
      setError(null);
      setInputMode('3hour');
      setAdjustmentMode('ratio_3hour');
    }
  }, [isOpen]);

  const currentAdjustedMap = useMemo(() => {
    if (inputMode === '24hour') {
      return viewMode === 'municipality' ? adjustedRainfall24Hour : adjustedSubdivisionRainfall24Hour;
    }
    return viewMode === 'municipality' ? adjustedRainfall : adjustedSubdivisionRainfall;
  }, [inputMode, viewMode, adjustedRainfall24Hour, adjustedSubdivisionRainfall24Hour, adjustedRainfall, adjustedSubdivisionRainfall]);

  const currentOriginalMap = useMemo(() => {
    if (inputMode === '24hour') {
      return viewMode === 'municipality' ? originalRainfall24Hour : originalSubdivisionRainfall24Hour;
    }
    return viewMode === 'municipality' ? originalRainfall : originalSubdivisionRainfall;
  }, [inputMode, viewMode, originalRainfall24Hour, originalSubdivisionRainfall24Hour, originalRainfall, originalSubdivisionRainfall]);

  const currentGroupedMap = useMemo(() => {
    if (inputMode === '24hour') {
      return viewMode === 'municipality'
        ? rainfall24HourByPrefecture
        : subdivisionRainfall24HourByPrefecture;
    }
    return viewMode === 'municipality'
      ? rainfallByPrefecture
      : subdivisionRainfallByPrefecture;
  }, [inputMode, viewMode, rainfall24HourByPrefecture, subdivisionRainfall24HourByPrefecture, rainfallByPrefecture, subdivisionRainfallByPrefecture]);

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
    const currentData = currentGroupedMap[selectedPrefecture] || {};

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

    const applyEdit = (prev: Record<string, TimeSeriesPoint[]>) => {
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
    };

    if (inputMode === '24hour') {
      if (viewMode === 'municipality') {
        setAdjustedRainfall24Hour(applyEdit);
      } else {
        setAdjustedSubdivisionRainfall24Hour(applyEdit);
      }
    } else {
      if (viewMode === 'municipality') {
        setAdjustedRainfall(applyEdit);
      } else {
        setAdjustedSubdivisionRainfall(applyEdit);
      }
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

    const applyEdit = (prev: Record<string, TimeSeriesPoint[]>) => {
      const updated = { ...prev };
      const areaData = updated[areaName];
      if (areaData) {
        updated[areaName] = areaData.map(point =>
          point.ft === ft ? { ...point, value: intValue } : point
        );
      }
      return updated;
    };

    if (inputMode === '24hour') {
      if (viewMode === 'municipality') {
        setAdjustedRainfall24Hour(applyEdit);
      } else {
        setAdjustedSubdivisionRainfall24Hour(applyEdit);
      }
    } else {
      if (viewMode === 'municipality') {
        setAdjustedRainfall(applyEdit);
      } else {
        setAdjustedSubdivisionRainfall(applyEdit);
      }
    }
  };

  // 元に戻す
  const resetToOriginal = () => {
    if (inputMode === '24hour') {
      if (viewMode === 'municipality') {
        setAdjustedRainfall24Hour(cloneRainfallMap(originalRainfall24Hour));
      } else {
        setAdjustedSubdivisionRainfall24Hour(cloneRainfallMap(originalSubdivisionRainfall24Hour));
      }
    } else {
      if (viewMode === 'municipality') {
        setAdjustedRainfall(cloneRainfallMap(originalRainfall));
      } else {
        setAdjustedSubdivisionRainfall(cloneRainfallMap(originalSubdivisionRainfall));
      }
    }
    setSelectedCells(new Set());
  };

  // セッションから雨量情報を取得
  useEffect(() => {
    if (isOpen && step === 'loading' && sessionId) {
      setLoading(true);
      setError(null);

      const fetchRainfallData = async () => {
        try {
          const data = await sessionApiClient.getRainfallData(sessionId);

          // area_rainfallとsubdivision_rainfallを直接使用
          setOriginalRainfall(data.area_rainfall);
          setAdjustedRainfall(cloneRainfallMap(data.area_rainfall));
          setOriginalSubdivisionRainfall(data.subdivision_rainfall);
          setAdjustedSubdivisionRainfall(cloneRainfallMap(data.subdivision_rainfall));
          setOriginalRainfall24Hour(cloneRainfallMap(data.area_rainfall_24hour ?? {}));
          setAdjustedRainfall24Hour(cloneRainfallMap(data.area_rainfall_24hour ?? {}));
          setOriginalSubdivisionRainfall24Hour(cloneRainfallMap(data.subdivision_rainfall_24hour ?? {}));
          setAdjustedSubdivisionRainfall24Hour(cloneRainfallMap(data.subdivision_rainfall_24hour ?? {}));
          const nextInputMode = data.input_mode ?? '3hour';
          setInputMode(nextInputMode);
          const nextAdjustmentMode = data.adjustment_mode ?? getDefaultAdjustmentMode(nextInputMode);
          setAdjustmentMode(
            getAllowedAdjustmentModes(nextInputMode).includes(nextAdjustmentMode)
              ? nextAdjustmentMode
              : getDefaultAdjustmentMode(nextInputMode)
          );

          // 最初の府県を選択
          const allAreas = Object.keys(data.area_rainfall);
          if (allAreas.length > 0) {
            const firstPrefName = allAreas[0].split('_')[0];
            setSelectedPrefecture(firstPrefName);
          }

          setStep('editing');
        } catch (err) {
          setError(err instanceof Error ? err.message : '雨量データの取得に失敗しました');
        } finally {
          setLoading(false);
        }
      };

      fetchRainfallData();
    }
  }, [isOpen, step, sessionId]);

  // 再計算実行（セッションベース）
  const handleRecalculate = async () => {
    setStep('calculating');
    setError(null);

    try {
      const adjustments = inputMode === '3hour'
        ? buildRainfallAdjustments(currentOriginalMap, currentAdjustedMap)
        : {};
      const aggregateAdjustments = inputMode === '24hour'
        ? buildRainfallAdjustments(currentOriginalMap, currentAdjustedMap)
        : {};

      // 変更がない場合は何もせずに閉じる
      if (Object.keys(adjustments).length === 0 && Object.keys(aggregateAdjustments).length === 0) {
        onClose();
        return;
      }

      console.log(`[Recalculate] Sending ${Object.keys(inputMode === '24hour' ? aggregateAdjustments : adjustments).length} modified areas`);

      // セッションベースAPI呼び出し
      const result = await sessionApiClient.recalculateWithAdjustedRainfall(
        sessionId,
        adjustments,
        aggregateAdjustments,
        inputMode,
        adjustmentMode,
        swiInitial,
        guidanceInitial,
        dataSource
      );

      // 軽量レスポンス（meshRisksとmeshCoords）を親コンポーネントに返す
      onSessionRecalculated(result.session_id, result.mesh_risks, result.mesh_coords);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '再計算に失敗しました');
      setStep('editing');
    }
  };

  // 修正数カウント
  const totalModifiedCount = useMemo(() => {
    return countModifiedCells(currentOriginalMap, currentAdjustedMap);
  }, [currentOriginalMap, currentAdjustedMap]);

  const currentPrefectureData = currentGroupedMap[selectedPrefecture] || {};

  const modifiedCountInPrefecture = useMemo(() => {
    const originalPrefectureData = groupRainfallByPrefecture(currentOriginalMap)[selectedPrefecture] || {};
    return countModifiedCells(originalPrefectureData, currentPrefectureData);
  }, [currentOriginalMap, currentPrefectureData, selectedPrefecture]);

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
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <label style={{ fontWeight: 'bold' }}>入力単位:</label>
                <button
                  onClick={() => {
                    setInputMode('3hour');
                    setAdjustmentMode(getDefaultAdjustmentMode('3hour'));
                    setSelectedCells(new Set());
                  }}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: inputMode === '3hour' ? '#1976D2' : '#f5f5f5',
                    color: inputMode === '3hour' ? 'white' : 'black',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  3時間ごと
                </button>
                <button
                  onClick={() => {
                    setInputMode('24hour');
                    setAdjustmentMode(getDefaultAdjustmentMode('24hour'));
                    setSelectedCells(new Set());
                  }}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: inputMode === '24hour' ? '#1976D2' : '#f5f5f5',
                    color: inputMode === '24hour' ? 'white' : 'black',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  24時間合計
                </button>
              </div>

              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <label style={{ fontWeight: 'bold' }}>調整方式:</label>
                {getAllowedAdjustmentModes(inputMode).map(mode => (
                  <button
                    key={mode}
                    onClick={() => setAdjustmentMode(mode)}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: adjustmentMode === mode ? '#1976D2' : '#f5f5f5',
                      color: adjustmentMode === mode ? 'white' : 'black',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    {getAdjustmentModeLabel(mode)}
                  </button>
                ))}
              </div>

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
                  入力単位: {inputMode === '24hour' ? '24時間合計' : '3時間ごと'}
                </span>
                <span style={{ marginRight: '20px' }}>
                  調整方式: {getAdjustmentModeLabel(adjustmentMode)}
                </span>
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
                          {inputMode === '24hour'
                            ? (point.ft === 24 ? '初期+24h' : point.ft === 48 ? '初期+48h' : `FT${point.ft}`)
                            : `FT${point.ft}`}
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
              {inputMode === '24hour' && (
                <> | 24時間合計は初期+24h と 初期+48h の2区間を編集</>
              )}
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

export default RainfallAdjustmentModalSession;

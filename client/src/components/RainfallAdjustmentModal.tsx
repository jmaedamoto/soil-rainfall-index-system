import React, { useState, useEffect, useMemo } from 'react';
import { getRainfallForecast, calculateWithAdjustedRainfall } from '../services/rainfallApi';
import { TimeSeriesPoint, CalculationResult } from '../types/api';

interface RainfallAdjustmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  swiInitial: string;
  guidanceInitial: string;
  dataSource: 'test' | 'production';
  onResultCalculated: (result: CalculationResult) => void;
}

const RainfallAdjustmentModal: React.FC<RainfallAdjustmentModalProps> = ({
  isOpen,
  onClose,
  swiInitial,
  guidanceInitial,
  dataSource,
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

  // 府県別にグループ化（市町村）
  const rainfallByPrefecture = useMemo(() => {
    const grouped: Record<string, Record<string, TimeSeriesPoint[]>> = {};

    Object.entries(adjustedRainfall).forEach(([areaName, timeseries]) => {
      // "府県名_市町村名" の形式から府県名を抽出
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
      // "府県名_二次細分名" の形式から府県名を抽出
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

  const prefectureList = useMemo(() => {
    return Object.keys(rainfallByPrefecture).sort();
  }, [rainfallByPrefecture]);

  // 初回データ取得時に最初の府県を選択
  useEffect(() => {
    if (prefectureList.length > 0 && !selectedPrefecture) {
      setSelectedPrefecture(prefectureList[0]);
    }
  }, [prefectureList, selectedPrefecture]);

  // モーダルが開かれたら自動的にデータ取得
  useEffect(() => {
    if (isOpen) {
      fetchRainfallData();
    }
  }, [isOpen, swiInitial, guidanceInitial]);

  const fetchRainfallData = async () => {
    setLoading(true);
    setError(null);
    setStep('loading');

    try {
      const data = await getRainfallForecast(swiInitial, guidanceInitial);

      if (data.status === 'success') {
        setOriginalRainfall(data.area_rainfall);
        setAdjustedRainfall(JSON.parse(JSON.stringify(data.area_rainfall)));

        // 二次細分データがあれば設定
        if (data.subdivision_rainfall) {
          setOriginalSubdivisionRainfall(data.subdivision_rainfall);
          setAdjustedSubdivisionRainfall(JSON.parse(JSON.stringify(data.subdivision_rainfall)));
        }

        setStep('editing');
      } else {
        setError('雨量予想データの取得に失敗しました');
      }
    } catch (err) {
      console.error('雨量予想取得エラー:', err);
      setError(`エラー: ${err instanceof Error ? err.message : '不明なエラー'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRainfallChange = (areaName: string, ft: number, newValue: string) => {
    const value = parseFloat(newValue);
    if (isNaN(value) || value < 0) {
      return;
    }

    if (viewMode === 'municipality') {
      setAdjustedRainfall(prev => {
        const updated = { ...prev };
        const areaData = updated[areaName];
        if (areaData) {
          const newAreaData = areaData.map(point =>
            point.ft === ft ? { ...point, value } : point
          );
          updated[areaName] = newAreaData;
        }
        return updated;
      });
    } else {
      setAdjustedSubdivisionRainfall(prev => {
        const updated = { ...prev };
        const subdivData = updated[areaName];
        if (subdivData) {
          const newSubdivData = subdivData.map(point =>
            point.ft === ft ? { ...point, value } : point
          );
          updated[areaName] = newSubdivData;
        }
        return updated;
      });
    }
  };

  const executeRecalculation = async () => {
    setLoading(true);
    setError(null);
    setStep('calculating');

    try {
      const areaAdjustments: Record<string, Record<number, number>> = {};

      for (const [areaName, timeseries] of Object.entries(adjustedRainfall)) {
        areaAdjustments[areaName] = {};
        timeseries.forEach(point => {
          areaAdjustments[areaName][point.ft] = point.value;
        });
      }

      const request = {
        swi_initial: swiInitial,
        guidance_initial: guidanceInitial,
        area_adjustments: areaAdjustments
      };

      const result = await calculateWithAdjustedRainfall(request);

      if (result.status === 'success') {
        onResultCalculated(result);
        onClose();
      } else {
        setError('再計算に失敗しました');
        setStep('editing');
      }
    } catch (err) {
      console.error('再計算エラー:', err);
      setError(`エラー: ${err instanceof Error ? err.message : '不明なエラー'}`);
      setStep('editing');
    } finally {
      setLoading(false);
    }
  };

  const resetToOriginal = () => {
    setAdjustedRainfall(JSON.parse(JSON.stringify(originalRainfall)));
    setAdjustedSubdivisionRainfall(JSON.parse(JSON.stringify(originalSubdivisionRainfall)));
  };

  // 選択された府県のデータ（表示モードに応じて切り替え）
  const currentPrefectureData = useMemo(() => {
    if (viewMode === 'municipality') {
      return rainfallByPrefecture[selectedPrefecture] || {};
    } else {
      return subdivisionRainfallByPrefecture[selectedPrefecture] || {};
    }
  }, [rainfallByPrefecture, subdivisionRainfallByPrefecture, selectedPrefecture, viewMode]);

  // 選択された府県の修正数
  const modifiedCountInPrefecture = useMemo(() => {
    const originalData = viewMode === 'municipality' ? originalRainfall : originalSubdivisionRainfall;
    return Object.entries(currentPrefectureData).reduce((count, [areaName, timeseries]) => {
      return count + timeseries.filter(point => {
        const originalPoint = originalData[areaName]?.find(p => p.ft === point.ft);
        return originalPoint && Math.abs(originalPoint.value - point.value) > 0.01;
      }).length;
    }, 0);
  }, [currentPrefectureData, originalRainfall, originalSubdivisionRainfall, viewMode]);

  // 全体の修正数
  const totalModifiedCount = useMemo(() => {
    if (viewMode === 'municipality') {
      return Object.entries(adjustedRainfall).reduce((count, [areaName, timeseries]) => {
        return count + timeseries.filter(point => {
          const originalPoint = originalRainfall[areaName]?.find(p => p.ft === point.ft);
          return originalPoint && Math.abs(originalPoint.value - point.value) > 0.01;
        }).length;
      }, 0);
    } else {
      return Object.entries(adjustedSubdivisionRainfall).reduce((count, [subdivName, timeseries]) => {
        return count + timeseries.filter(point => {
          const originalPoint = originalSubdivisionRainfall[subdivName]?.find(p => p.ft === point.ft);
          return originalPoint && Math.abs(originalPoint.value - point.value) > 0.01;
        }).length;
      }, 0);
    }
  }, [adjustedRainfall, originalRainfall, adjustedSubdivisionRainfall, originalSubdivisionRainfall, viewMode]);

  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '20px',
        maxWidth: '90vw',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0 }}>雨量予想調整</h2>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            閉じる
          </button>
        </div>

        {/* データソース表示 */}
        <div style={{
          backgroundColor: '#e3f2fd',
          padding: '10px 15px',
          borderRadius: '6px',
          marginBottom: '20px',
          fontSize: '14px'
        }}>
          <strong>データソース:</strong> {dataSource === 'test' ? 'テストデータ' : '本番データ（気象庁GRIB2）'}
        </div>

        {/* エラー表示 */}
        {error && (
          <div style={{
            backgroundColor: '#f8d7da',
            color: '#721c24',
            padding: '10px 15px',
            borderRadius: '4px',
            marginBottom: '20px',
            border: '1px solid #f5c6cb'
          }}>
            {error}
          </div>
        )}

        {/* ローディング状態 */}
        {step === 'loading' && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              border: '4px solid #f3f3f3',
              borderTop: '4px solid #1976D2',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto 20px'
            }} />
            <p>雨量データを取得中...</p>
          </div>
        )}

        {/* 再計算中 */}
        {step === 'calculating' && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              border: '4px solid #f3f3f3',
              borderTop: '4px solid #4CAF50',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto 20px'
            }} />
            <p>危険度を再計算中...</p>
          </div>
        )}

        {/* 編集テーブル */}
        {step === 'editing' && Object.keys(adjustedRainfall).length > 0 && (
          <>
            {/* 府県選択タブ */}
            <div style={{
              display: 'flex',
              gap: '5px',
              marginBottom: '15px',
              borderBottom: '2px solid #ddd',
              overflowX: 'auto'
            }}>
              {prefectureList.map(prefName => (
                <button
                  key={prefName}
                  onClick={() => setSelectedPrefecture(prefName)}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: selectedPrefecture === prefName ? '#1976D2' : '#f5f5f5',
                    color: selectedPrefecture === prefName ? 'white' : '#333',
                    border: 'none',
                    borderRadius: '4px 4px 0 0',
                    cursor: 'pointer',
                    fontWeight: selectedPrefecture === prefName ? 'bold' : 'normal',
                    transition: 'all 0.2s'
                  }}
                >
                  {prefName}
                </button>
              ))}
            </div>

            {/* 表示モード切り替え */}
            <div style={{ marginBottom: '15px', display: 'flex', gap: '10px', alignItems: 'center' }}>
              <label style={{ fontWeight: 'bold' }}>表示:</label>
              <button
                onClick={() => setViewMode('municipality')}
                style={{
                  padding: '8px 16px',
                  backgroundColor: viewMode === 'municipality' ? '#1976D2' : '#f5f5f5',
                  color: viewMode === 'municipality' ? 'white' : '#333',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: viewMode === 'municipality' ? 'bold' : 'normal'
                }}
              >
                市町村別
              </button>
              <button
                onClick={() => setViewMode('subdivision')}
                style={{
                  padding: '8px 16px',
                  backgroundColor: viewMode === 'subdivision' ? '#1976D2' : '#f5f5f5',
                  color: viewMode === 'subdivision' ? 'white' : '#333',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: viewMode === 'subdivision' ? 'bold' : 'normal'
                }}
              >
                二次細分別
              </button>
            </div>

            <div style={{ marginBottom: '15px', display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={resetToOriginal}
                disabled={loading}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#ffc107',
                  color: 'black',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  opacity: loading ? 0.6 : 1
                }}
              >
                元の値にリセット
              </button>
              <button
                onClick={executeRecalculation}
                disabled={loading}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold',
                  opacity: loading ? 0.6 : 1
                }}
              >
                再計算実行
              </button>
              <div style={{ marginLeft: 'auto', fontSize: '14px', color: '#666', textAlign: 'right' }}>
                <div>表示中: {selectedPrefecture} ({Object.keys(currentPrefectureData).length}{viewMode === 'municipality' ? '市町村' : '二次細分'})</div>
                <div>全体修正箇所: {totalModifiedCount} | 表示中: {modifiedCountInPrefecture}</div>
              </div>
            </div>

            <div style={{
              maxHeight: '60vh',
              overflow: 'auto',
              border: '1px solid #ddd',
              borderRadius: '4px'
            }}>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: '14px'
              }}>
                <thead style={{ position: 'sticky', top: 0, backgroundColor: '#f5f5f5', zIndex: 1 }}>
                  <tr>
                    <th style={{ padding: '8px', borderBottom: '2px solid #ddd', textAlign: 'left', minWidth: '150px' }}>
                      {viewMode === 'municipality' ? '市町村' : '二次細分'}
                    </th>
                    {Object.keys(currentPrefectureData).length > 0 &&
                      currentPrefectureData[Object.keys(currentPrefectureData)[0]]?.map(point => (
                        <th key={point.ft} style={{ padding: '8px', borderBottom: '2px solid #ddd', textAlign: 'center', minWidth: '70px' }}>
                          FT{point.ft}
                        </th>
                      ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(currentPrefectureData).map(([areaName, timeseries]) => (
                    <tr key={areaName}>
                      <td style={{ padding: '8px', borderBottom: '1px solid #eee', fontWeight: 'bold' }}>
                        {areaName.split('_')[1] || areaName}
                      </td>
                      {timeseries.map(point => {
                        const originalData = viewMode === 'municipality' ? originalRainfall : originalSubdivisionRainfall;
                        const originalPoint = originalData[areaName]?.find(p => p.ft === point.ft);
                        const isModified = originalPoint && Math.abs(originalPoint.value - point.value) > 0.01;

                        return (
                          <td key={point.ft} style={{ padding: '4px', borderBottom: '1px solid #eee' }}>
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              value={point.value.toFixed(1)}
                              onChange={(e) => handleRainfallChange(areaName, point.ft, e.target.value)}
                              style={{
                                width: '60px',
                                padding: '4px',
                                border: '1px solid #ccc',
                                borderRadius: '4px',
                                textAlign: 'right',
                                backgroundColor: isModified ? '#fff3cd' : 'white'
                              }}
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        <style>
          {`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}
        </style>
      </div>
    </div>
  );
};

export default RainfallAdjustmentModal;

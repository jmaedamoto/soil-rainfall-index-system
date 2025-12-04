import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getRainfallForecast, calculateWithAdjustedRainfall } from '../services/rainfallApi';
import type { AreaRainfallForecast, TimeSeriesPoint, CalculationResult } from '../types/api';
import '../styles/RainfallAdjustment.css';

interface LocationState {
  swiInitial?: string;
  guidanceInitial?: string;
  dataSource?: 'test' | 'production';
}

const RainfallAdjustment: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LocationState;

  // 状態管理（ダッシュボードから渡された値またはデフォルト）
  const [swiInitial, setSwiInitial] = useState<string>(state?.swiInitial || '');
  const [guidanceInitial, setGuidanceInitial] = useState<string>(state?.guidanceInitial || '');
  const [dataSource] = useState(state?.dataSource || 'test');
  const [originalRainfall, setOriginalRainfall] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [adjustedRainfall, setAdjustedRainfall] = useState<Record<string, TimeSeriesPoint[]>>({});
  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * デフォルト時刻を設定（現在時刻の6時間前、6時間刻み）
   */
  const setDefaultTimes = () => {
    const now = new Date();
    // 3時間前
    now.setHours(now.getHours() - 3);
    // 6時間刻みに丸める（0, 6, 12, 18時）
    const roundedHour = Math.floor(now.getHours() / 6) * 6;
    now.setHours(roundedHour, 0, 0, 0);

    const isoString = now.toISOString().slice(0, 19);
    setSwiInitial(isoString);
    setGuidanceInitial(isoString);
  };

  /**
   * 雨量予想データを取得
   */
  const fetchRainfallForecast = async () => {
    if (!swiInitial || !guidanceInitial) {
      setError('SWI初期時刻とガイダンス初期時刻を入力してください');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await getRainfallForecast(swiInitial, guidanceInitial);

      if (data.status === 'success') {
        setOriginalRainfall(data.area_rainfall);
        setAdjustedRainfall(JSON.parse(JSON.stringify(data.area_rainfall))); // ディープコピー
        setCalculationResult(null); // 再計算結果をクリア
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

  /**
   * 雨量値を編集
   */
  const handleRainfallChange = (areaName: string, ft: number, newValue: string) => {
    const value = parseFloat(newValue);
    if (isNaN(value) || value < 0) {
      return;
    }

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
  };

  /**
   * 再計算を実行
   */
  const executeRecalculation = async () => {
    setLoading(true);
    setError(null);

    try {
      // 調整データを作成
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
        setCalculationResult(result);
      } else {
        setError('再計算に失敗しました');
      }
    } catch (err) {
      console.error('再計算エラー:', err);
      setError(`エラー: ${err instanceof Error ? err.message : '不明なエラー'}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * 元の値にリセット
   */
  const resetToOriginal = () => {
    setAdjustedRainfall(JSON.parse(JSON.stringify(originalRainfall)));
  };

  // 初回マウント時の処理
  useEffect(() => {
    // ダッシュボードから時刻が渡された場合、自動的にデータ取得
    if (state?.swiInitial && state?.guidanceInitial) {
      fetchRainfallForecast();
    } else {
      setDefaultTimes();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * ダッシュボードに戻る（調整結果を渡す）
   */
  const returnToDashboard = () => {
    if (calculationResult) {
      navigate('/dashboard', {
        state: {
          adjustedResult: calculationResult,
          swiInitial,
          guidanceInitial,
          dataSource
        }
      });
    }
  };

  return (
    <div className="rainfall-adjustment-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>雨量予想調整</h1>
        <button
          onClick={() => navigate('/dashboard')}
          style={{
            padding: '10px 20px',
            backgroundColor: '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          ダッシュボードに戻る
        </button>
      </div>

      {/* データソース表示 */}
      {dataSource && (
        <div style={{
          backgroundColor: '#e3f2fd',
          padding: '10px 15px',
          borderRadius: '6px',
          marginBottom: '20px',
          fontSize: '14px'
        }}>
          <strong>データソース:</strong> {dataSource === 'test' ? 'テストデータ' : '本番データ（気象庁GRIB2）'}
        </div>
      )}

      {/* 時刻入力セクション */}
      <div className="time-input-section">
        <div className="time-input-group">
          <label>
            SWI初期時刻:
            <input
              type="datetime-local"
              step="1"
              value={swiInitial.replace('Z', '')}
              onChange={(e) => setSwiInitial(e.target.value)}
            />
          </label>
        </div>

        <div className="time-input-group">
          <label>
            ガイダンス初期時刻:
            <input
              type="datetime-local"
              step="1"
              value={guidanceInitial.replace('Z', '')}
              onChange={(e) => setGuidanceInitial(e.target.value)}
            />
          </label>
        </div>

        <button onClick={fetchRainfallForecast} disabled={loading}>
          {loading ? 'データ取得中...' : 'データ取得'}
        </button>

        <button onClick={setDefaultTimes} disabled={loading}>
          デフォルト時刻設定
        </button>
      </div>

      {/* エラー表示 */}
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {/* 雨量編集テーブル */}
      {Object.keys(adjustedRainfall).length > 0 && (
        <div className="rainfall-editor-section">
          <h2>市町村別雨量時系列（編集可能）</h2>

          <div className="button-group">
            <button onClick={resetToOriginal} disabled={loading}>
              元の値にリセット
            </button>
            <button
              onClick={executeRecalculation}
              disabled={loading}
              className="recalculate-button"
            >
              {loading ? '再計算中...' : '再計算実行'}
            </button>
          </div>

          <div className="rainfall-table-container">
            <table className="rainfall-table">
              <thead>
                <tr>
                  <th>市町村</th>
                  {adjustedRainfall[Object.keys(adjustedRainfall)[0]]?.map(point => (
                    <th key={point.ft}>FT{point.ft}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(adjustedRainfall).map(([areaName, timeseries]) => (
                  <tr key={areaName}>
                    <td className="area-name">{areaName}</td>
                    {timeseries.map(point => {
                      const originalPoint = originalRainfall[areaName]?.find(p => p.ft === point.ft);
                      const isModified = originalPoint && Math.abs(originalPoint.value - point.value) > 0.01;

                      return (
                        <td key={point.ft}>
                          <input
                            type="number"
                            step="0.1"
                            min="0"
                            value={point.value.toFixed(1)}
                            onChange={(e) => handleRainfallChange(areaName, point.ft, e.target.value)}
                            className={isModified ? 'modified' : ''}
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="stats-info">
            <p>市町村数: {Object.keys(adjustedRainfall).length}</p>
            <p>
              修正箇所: {
                Object.entries(adjustedRainfall).reduce((count, [areaName, timeseries]) => {
                  return count + timeseries.filter(point => {
                    const originalPoint = originalRainfall[areaName]?.find(p => p.ft === point.ft);
                    return originalPoint && Math.abs(originalPoint.value - point.value) > 0.01;
                  }).length;
                }, 0)
              }
            </p>
          </div>
        </div>
      )}

      {/* 再計算結果表示 */}
      {calculationResult && (
        <div className="calculation-result-section">
          <h2>再計算結果</h2>
          <p>計算完了時刻: {new Date(calculationResult.calculation_time).toLocaleString('ja-JP')}</p>

          <div style={{ marginTop: '15px' }}>
            <button
              onClick={returnToDashboard}
              style={{
                padding: '12px 24px',
                backgroundColor: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: 'bold'
              }}
            >
              調整結果をダッシュボードで表示
            </button>
          </div>

          <p className="info-text" style={{ marginTop: '10px' }}>
            ※ 調整後の危険度を地図・グラフで確認できます
          </p>
        </div>
      )}
    </div>
  );
};

export default RainfallAdjustment;

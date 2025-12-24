import React, { useState, useEffect } from 'react';
import { mockProductionApi } from '../services/mockProductionApi';
import SoilRainfallMap from '../components/map/SoilRainfallMap';
import AreaRiskBarChart from '../components/charts/AreaRiskBarChart';
import CacheInfo from '../components/CacheInfo';
import RainfallAdjustmentModal from '../components/RainfallAdjustmentModal';
import { CalculationResult, Mesh } from '../types/api';

const Production: React.FC = () => {
  const [data, setData] = useState<CalculationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState(0);
  const [selectedPrefecture, setSelectedPrefecture] = useState<string>('');
  const [isTimeChanging, setIsTimeChanging] = useState(false);
  const [isAdjustedData, setIsAdjustedData] = useState(false);

  // SWIとガイダンスの初期時刻を個別に管理
  const [swiInitialTime, setSwiInitialTime] = useState<string>('');
  const [guidanceInitialTime, setGuidanceInitialTime] = useState<string>('');

  // 雨量調整モーダルの状態
  const [isRainfallModalOpen, setIsRainfallModalOpen] = useState(false);

  // 初期時刻の候補を生成（6時間ごと: 0, 6, 12, 18時）
  const generateTimeOptions = () => {
    const options: string[] = [];
    const now = new Date();

    // 過去24時間分の6時間刻み時刻を生成
    for (let i = 0; i < 5; i++) {
      const time = new Date(now.getTime() - i * 6 * 60 * 60 * 1000);
      const hour = Math.floor(time.getHours() / 6) * 6;
      time.setHours(hour, 0, 0, 0);
      options.push(time.toISOString());
    }

    return options;
  };

  useEffect(() => {
    // デフォルトの初期時刻を設定（テストデータ: 2023-06-02 00:00:00）
    const defaultTime = '2023-06-02T00:00:00Z';

    setSwiInitialTime(defaultTime);
    setGuidanceInitialTime(defaultTime);
  }, []);

  const loadData = async () => {
    if (!swiInitialTime || !guidanceInitialTime) {
      setError('初期時刻を選択してください');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setIsAdjustedData(false); // 新規読み込みなので調整済みフラグをクリア

      // モックAPI（開発環境用）を呼び出し - テストデータ使用
      const result = await mockProductionApi.calculateProductionSoilRainfallIndexWithUrls({
        swi_initial: swiInitialTime,
        guidance_initial: guidanceInitialTime
      });
      setData(result);

      // デフォルトで最初の都道府県を選択
      const firstPrefCode = Object.keys(result.prefectures)[0];
      setSelectedPrefecture(firstPrefCode);
    } catch (err) {
      setError(err instanceof Error ? err.message : '予期しないエラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  // 雨量調整結果の処理
  const handleRainfallAdjustmentResult = (result: CalculationResult) => {
    setData(result);
    setIsAdjustedData(true);

    // 時刻をリセット
    const meshes: Mesh[] = Object.values(result.prefectures).flatMap(pref =>
      pref.areas.flatMap(area => area.meshes)
    );

    if (meshes.length > 0) {
      const timeSet = new Set<number>();
      meshes.forEach(mesh => {
        mesh.swi_timeline.forEach(point => {
          timeSet.add(point.ft);
        });
      });
      const times = Array.from(timeSet).sort((a, b) => a - b);
      if (times.length > 0) {
        setSelectedTime(times[0]);
      }
    }
  };

  const timeOptions = generateTimeOptions();

  // 日時フォーマット関数（JST表示）
  const formatDateTime = (isoString: string) => {
    const date = new Date(isoString);
    const jstDate = new Date(date.getTime() + 9 * 60 * 60 * 1000);
    return `${jstDate.getUTCFullYear()}年${jstDate.getUTCMonth() + 1}月${jstDate.getUTCDate()}日 ${jstDate.getUTCHours()}時 (JST)`;
  };

  const handleTimeChange = (newTime: number) => {
    // 同じ時刻が選択された場合は何もしない
    if (newTime === selectedTime) return;

    // ローディング状態を即座に設定
    setIsTimeChanging(true);

    // 状態更新を次のフレームで実行
    requestAnimationFrame(() => {
      setSelectedTime(newTime);
      // 短い遅延の後、ローディング解除
      requestAnimationFrame(() => {
        setTimeout(() => setIsTimeChanging(false), 50);
      });
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (!data) return;
    const maxFt = Math.max(...data.prefectures[Object.keys(data.prefectures)[0]].areas[0].meshes[0].swi_timeline.map(t => t.ft));

    if (e.key === 'ArrowLeft' && selectedTime > 0) {
      handleTimeChange(selectedTime - 3);
    } else if (e.key === 'ArrowRight' && selectedTime < maxFt) {
      handleTimeChange(selectedTime + 3);
    }
  };

  // データがある場合の変数を事前計算
  const allMeshes: Mesh[] = data ? Object.values(data.prefectures).flatMap(pref =>
    pref.areas.flatMap(area => area.meshes)
  ) : [];

  const availableTimes = data && allMeshes.length > 0
    ? allMeshes[0].swi_timeline.map(t => t.ft)
    : [];

  const initialTime = data?.initial_time || swiInitialTime;

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '20px' }}>土壌雨量指数監視システム（本番環境）</h1>

      {/* ローディング表示 */}
      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px', flexDirection: 'column', gap: '20px' }}>
          <div style={{
            width: '50px',
            height: '50px',
            border: '5px solid #f3f3f3',
            borderTop: '5px solid #1976D2',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
          <div style={{ fontSize: '18px' }}>データ読み込み中...</div>
          <div style={{ fontSize: '14px', color: '#666' }}>26,000メッシュのデータを処理しています（2〜3分かかります）</div>
          <style>
            {`
              @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
              }
            `}
          </style>
        </div>
      )}

      {/* データ取得設定 */}
      {!loading && !data && (
        <div style={{
          marginBottom: '20px',
          padding: '20px',
          backgroundColor: '#f5f5f5',
          borderRadius: '8px'
        }}>
          <h2 style={{ marginBottom: '15px' }}>データ取得設定</h2>

          {/* SWI初期時刻 */}
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              土壌雨量指数（SWI）初期時刻:
            </label>
            <select
              value={swiInitialTime}
              onChange={(e) => setSwiInitialTime(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                fontSize: '14px',
                borderRadius: '4px',
                border: '1px solid #ccc'
              }}
            >
              <option value="">-- 初期時刻を選択 --</option>
              {timeOptions.map(time => (
                <option key={time} value={time}>
                  {formatDateTime(time)}
                </option>
              ))}
            </select>
          </div>

          {/* ガイダンス初期時刻 */}
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              降水量予測（ガイダンス）初期時刻:
            </label>
            <select
              value={guidanceInitialTime}
              onChange={(e) => setGuidanceInitialTime(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                fontSize: '14px',
                borderRadius: '4px',
                border: '1px solid #ccc'
              }}
            >
              <option value="">-- 初期時刻を選択 --</option>
              {timeOptions.map(time => (
                <option key={time} value={time}>
                  {formatDateTime(time)}
                </option>
              ))}
            </select>
          </div>

          {/* データ取得ボタン */}
          <button
            onClick={loadData}
            disabled={loading || !swiInitialTime || !guidanceInitialTime}
            style={{
              padding: '10px 20px',
              fontSize: '16px',
              fontWeight: 'bold',
              color: 'white',
              backgroundColor: loading || !swiInitialTime || !guidanceInitialTime ? '#ccc' : '#1976D2',
              border: 'none',
              borderRadius: '4px',
              cursor: loading || !swiInitialTime || !guidanceInitialTime ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'データ取得中...' : 'データを取得'}
          </button>

          {error && (
            <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#ffebee', color: '#c62828', borderRadius: '4px' }}>
              エラー: {error}
            </div>
          )}
        </div>
      )}

      {/* データ表示部分 */}
      {data && (
        <>
          {/* キャッシュ情報表示 */}
          {data.cache_info && (
            <CacheInfo cacheInfo={data.cache_info} />
          )}

          {/* データ情報と操作ボタン */}
          <div style={{
            marginBottom: '20px',
            padding: '15px',
            backgroundColor: '#f5f5f5',
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start'
          }}>
            <div style={{ flex: 1 }}>
              {isAdjustedData && (
                <div style={{
                  backgroundColor: '#fff3cd',
                  padding: '10px',
                  borderRadius: '4px',
                  marginBottom: '10px',
                  border: '1px solid #ffc107'
                }}>
                  <strong>⚠️ 雨量調整済みデータ</strong> - ユーザーが編集した雨量予想に基づく計算結果
                </div>
              )}
              <p><strong>計算時刻:</strong> {new Date(data.calculation_time).toLocaleString('ja-JP')}</p>
              <p><strong>初期時刻:</strong> {formatDateTime(swiInitialTime)}</p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                onClick={() => setData(null)}
                style={{
                  padding: '8px 16px',
                  fontSize: '14px',
                  color: 'white',
                  backgroundColor: '#2196F3',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                初期時刻を変更
              </button>
              <button
                onClick={() => setIsRainfallModalOpen(true)}
                style={{
                  padding: '8px 16px',
                  fontSize: '14px',
                  color: 'white',
                  backgroundColor: '#FF9800',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                雨量調整
              </button>
            </div>
          </div>

          {/* 時刻選択 */}
          <div style={{
            marginBottom: '20px',
            padding: '15px',
            backgroundColor: '#f5f5f5',
            borderRadius: '8px'
          }}>
            <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
              予測時刻 (FT): {selectedTime}時間後
            </label>
            <input
              type="range"
              min={0}
              max={availableTimes.length > 0 ? Math.max(...availableTimes) : 0}
              step={3}
              value={selectedTime}
              onChange={(e) => handleTimeChange(Number(e.target.value))}
              onKeyDown={handleKeyPress}
              style={{ width: '100%' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '5px', fontSize: '12px' }}>
              {availableTimes.map(ft => (
                <span key={ft}>FT{ft}</span>
              ))}
            </div>
          </div>

          {/* 地図表示 */}
          <div style={{ marginBottom: '30px' }}>
            <h2 style={{ marginBottom: '15px' }}>危険度分布図</h2>
            <SoilRainfallMap
              meshes={allMeshes}
              selectedTime={selectedTime}
              selectedPrefecture={selectedPrefecture}
              prefectureData={data.prefectures}
              isLoading={isTimeChanging}
              swiInitialTime={swiInitialTime}
              guidanceInitialTime={guidanceInitialTime}
            />
          </div>

          {/* エリア別リスクレベル時系列 */}
          <div style={{ marginBottom: '30px' }}>
            <h2 style={{ marginBottom: '15px' }}>地域別危険度推移</h2>
            {initialTime && (
              <AreaRiskBarChart
                prefectures={Object.values(data.prefectures)}
                selectedTime={selectedTime}
                selectedPrefecture={selectedPrefecture}
                onPrefectureChange={setSelectedPrefecture}
                onTimeSelect={handleTimeChange}
                initialTime={initialTime}
              />
            )}
          </div>

          {/* 雨量調整モーダル */}
          <RainfallAdjustmentModal
            isOpen={isRainfallModalOpen}
            onClose={() => setIsRainfallModalOpen(false)}
            swiInitial={swiInitialTime}
            guidanceInitial={guidanceInitialTime}
            dataSource="test"
            existingData={data?.prefectures || null}
            onResultCalculated={handleRainfallAdjustmentResult}
          />
        </>
      )}
    </div>
  );
};

export default Production;

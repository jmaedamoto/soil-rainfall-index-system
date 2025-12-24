import React, { useState, useEffect } from 'react';
import { apiClient_ } from '../services/api';
import { sessionApiClient } from '../services/sessionApi';
import SoilRainfallMap from '../components/map/SoilRainfallMap';
import AreaRiskBarChart from '../components/charts/AreaRiskBarChart';
import CacheInfo from '../components/CacheInfo';
import RainfallAdjustmentModal from '../components/RainfallAdjustmentModal';
import { Prefecture, Mesh, LightweightCalculationResult, CalculationResult } from '../types/api';

const ProductionSession: React.FC = () => {
  // セッション情報
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionInfo, setSessionInfo] = useState<LightweightCalculationResult | null>(null);

  // 府県データ（オンデマンド読み込み）
  const [prefectureData, setPrefectureData] = useState<Record<string, Prefecture>>({});

  const [loading, setLoading] = useState(false);
  const [loadingPrefecture, setLoadingPrefecture] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState(0);
  const [selectedPrefecture, setSelectedPrefecture] = useState<string>('');
  const [_isTimeChanging, setIsTimeChanging] = useState(false);
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

      // セッションベースAPIを呼び出し（軽量レスポンス）
      const result = await apiClient_.calculateProductionSoilRainfallIndexWithUrls({
        swi_initial: swiInitialTime,
        guidance_initial: guidanceInitialTime
      });

      setSessionInfo(result);
      setSessionId(result.session_id);

      // モックモードの場合、sessionIdに"mock_session_"が含まれている
      if (result.session_id.startsWith('mock_session_')) {
        // モックモード: 全データを再取得して府県データに設定
        console.log('モックモード: 全データを読み込み中...');
        const mockFullData = await apiClient_.testFullCalculation();
        setPrefectureData(mockFullData.prefectures);

        // デフォルトで最初の都道府県を選択
        const firstPrefCode = Object.keys(mockFullData.prefectures)[0];
        setSelectedPrefecture(firstPrefCode);
      } else {
        // 本番モード: 府県データをクリア
        setPrefectureData({});

        // デフォルトで最初の都道府県を選択
        if (result.available_prefectures.length > 0) {
          const firstPrefCode = result.available_prefectures[0];
          setSelectedPrefecture(firstPrefCode);
          // 最初の府県データを読み込み
          await loadPrefectureData(result.session_id, firstPrefCode);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '予期しないエラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  const loadPrefectureData = async (session: string, prefectureCode: string) => {
    // モックモードの場合はスキップ（全データが既に読み込まれている）
    if (session.startsWith('mock_session_')) {
      return;
    }

    // 既に読み込み済みの場合はスキップ
    if (prefectureData[prefectureCode]) {
      return;
    }

    try {
      setLoadingPrefecture(prefectureCode);
      const response = await sessionApiClient.getPrefectureData(session, prefectureCode);

      if (response.status === 'success') {
        setPrefectureData(prev => ({
          ...prev,
          [prefectureCode]: response.prefecture
        }));
      }
    } catch (err) {
      console.error(`府県データ読み込みエラー (${prefectureCode}):`, err);
    } finally {
      setLoadingPrefecture(null);
    }
  };

  // 府県選択時のハンドラ
  const handlePrefectureChange = async (prefCode: string) => {
    setSelectedPrefecture(prefCode);
    if (sessionId) {
      await loadPrefectureData(sessionId, prefCode);
    }
  };

  // 雨量調整結果の処理
  const handleRainfallAdjustmentResult = (result: CalculationResult) => {
    // セッション情報を更新（調整結果を反映）
    setPrefectureData(result.prefectures);
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
    if (!sessionInfo) return;
    const maxFt = Math.max(...sessionInfo.available_times);

    if (e.key === 'ArrowLeft' && selectedTime > 0) {
      handleTimeChange(selectedTime - 3);
    } else if (e.key === 'ArrowRight' && selectedTime < maxFt) {
      handleTimeChange(selectedTime + 3);
    }
  };

  // 全メッシュデータを集約（読み込み済みの府県データから）
  const allMeshes: Mesh[] = Object.values(prefectureData).flatMap(pref =>
    pref.areas.flatMap(area => area.meshes)
  );

  const _availableTimes = sessionInfo?.available_times || [];

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '20px' }}>土壌雨量指数監視システム（本番環境 - セッションベース）</h1>

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
          <div style={{ fontSize: '18px' }}>データ計算中...</div>
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

      {/* エラー表示 */}
      {error && (
        <div style={{ backgroundColor: '#f44336', color: 'white', padding: '10px', marginBottom: '20px', borderRadius: '4px' }}>
          エラー: {error}
        </div>
      )}

      {/* データ取得コントロール */}
      <div style={{ marginBottom: '30px', backgroundColor: '#f5f5f5', padding: '20px', borderRadius: '8px' }}>
        <h2 style={{ marginTop: 0 }}>データ取得設定</h2>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
          {/* SWI初期時刻選択 */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              SWI初期時刻（土壌雨量指数）
            </label>
            <select
              value={swiInitialTime}
              onChange={(e) => setSwiInitialTime(e.target.value)}
              style={{ width: '100%', padding: '8px', fontSize: '14px' }}
            >
              {timeOptions.map(time => (
                <option key={time} value={time}>
                  {formatDateTime(time)}
                </option>
              ))}
            </select>
          </div>

          {/* ガイダンス初期時刻選択 */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              ガイダンス初期時刻（降水量予測）
            </label>
            <select
              value={guidanceInitialTime}
              onChange={(e) => setGuidanceInitialTime(e.target.value)}
              style={{ width: '100%', padding: '8px', fontSize: '14px' }}
            >
              {timeOptions.map(time => (
                <option key={time} value={time}>
                  {formatDateTime(time)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={loadData}
          disabled={loading || !swiInitialTime || !guidanceInitialTime}
          style={{
            backgroundColor: loading ? '#ccc' : '#1976D2',
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            fontSize: '16px',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            width: '100%'
          }}
        >
          {loading ? 'データ取得中...' : 'データを取得'}
        </button>

        {/* セッション情報表示 */}
        {sessionInfo && (
          <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#e3f2fd', borderRadius: '4px', fontSize: '14px' }}>
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
            <div><strong>セッションID:</strong> {sessionInfo.session_id}</div>
            <div><strong>利用可能な府県:</strong> {sessionInfo.available_prefectures.join(', ')}</div>
            <div><strong>データ転送量:</strong> 初回レスポンス ~1KB（従来比 99.9%削減）</div>
          </div>
        )}

        {/* 雨量調整ボタン */}
        {sessionInfo && (
          <button
            onClick={() => setIsRainfallModalOpen(true)}
            style={{
              marginTop: '10px',
              padding: '10px 20px',
              backgroundColor: '#FF9800',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              width: '100%',
              fontSize: '16px',
              fontWeight: 'bold'
            }}
          >
            雨量調整
          </button>
        )}
      </div>

      {/* キャッシュ情報 */}
      {sessionInfo?.cache_info && (
        <CacheInfo cacheInfo={sessionInfo.cache_info} />
      )}

      {/* データ表示エリア */}
      {sessionInfo && (
        <div style={{ marginTop: '30px' }}>
          {/* 府県選択 */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ marginRight: '10px', fontWeight: 'bold' }}>都道府県:</label>
            <select
              value={selectedPrefecture}
              onChange={(e) => handlePrefectureChange(e.target.value)}
              style={{ padding: '8px', fontSize: '14px', minWidth: '200px' }}
            >
              {sessionInfo.available_prefectures.map(code => (
                <option key={code} value={code}>
                  {code}
                  {loadingPrefecture === code && ' (読み込み中...)'}
                  {prefectureData[code] && ' ✓'}
                </option>
              ))}
            </select>
            {loadingPrefecture && (
              <span style={{ marginLeft: '10px', color: '#1976D2' }}>
                府県データ読み込み中...
              </span>
            )}
          </div>

          {/* 地図とチャート */}
          {prefectureData[selectedPrefecture] && (
            <div onKeyDown={handleKeyPress} tabIndex={0}>
              <SoilRainfallMap
                meshes={allMeshes}
                selectedTime={selectedTime}
                selectedPrefecture={selectedPrefecture}
                swiInitialTime={sessionInfo.swi_initial_time}
              />

              <div style={{ marginTop: '30px' }}>
                <AreaRiskBarChart
                  prefectures={[prefectureData[selectedPrefecture]]}
                  selectedPrefecture={selectedPrefecture}
                  selectedTime={selectedTime}
                  onPrefectureChange={handlePrefectureChange}
                  onTimeSelect={handleTimeChange}
                  initialTime={sessionInfo.swi_initial_time}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* 雨量調整モーダル */}
      {sessionInfo && (
        <RainfallAdjustmentModal
          isOpen={isRainfallModalOpen}
          onClose={() => setIsRainfallModalOpen(false)}
          swiInitial={swiInitialTime}
          guidanceInitial={guidanceInitialTime}
          dataSource="test"
          existingData={prefectureData || null}
          onResultCalculated={handleRainfallAdjustmentResult}
        />
      )}
    </div>
  );
};

export default ProductionSession;

import React, { useState, useEffect } from 'react';
import { sessionApiClient } from '../services/sessionApi';
import SoilRainfallMap from '../components/map/SoilRainfallMap';
import AreaRiskBarChart from '../components/charts/AreaRiskBarChart';
import CacheInfo from '../components/CacheInfo';
import RainfallAdjustmentModalSession from '../components/RainfallAdjustmentModalSession';
import type { Prefecture as PrefectureType } from '../types/api';
import {
  buildIsoStringFromJst,
  getDefaultJstSelection,
  getGuidanceHourOptions,
  MSM_HOUR_OPTIONS,
} from '../features/production-session/utils/dateTime';
import {
  PREFECTURE_NAME_MAP,
  useProductionSession,
} from '../features/production-session/hooks/useProductionSession';
import type { RiskRule } from '../types/api';

const ProductionSession: React.FC = () => {
  const [isRainfallModalOpen, setIsRainfallModalOpen] = useState(false);
  const [swiDate, setSwiDate] = useState<string>('');
  const [swiHour, setSwiHour] = useState<number>(0);
  const [guidanceDate, setGuidanceDate] = useState<string>('');
  const [guidanceHour, setGuidanceHour] = useState<number>(0);
  const [swiInitialTime, setSwiInitialTime] = useState<string>('');
  const [guidanceInitialTime, setGuidanceInitialTime] = useState<string>('');
  const [guidanceType, setGuidanceType] = useState<'msm' | 'gsm'>('msm');
  const [riskRule, setRiskRule] = useState<RiskRule>('legacy');

  const {
    error,
    handlePrefectureChange,
    handleTimeChange,
    isAdjustedData,
    loadAllPrefectures,
    loadData,
    loadRiskAtTime,
    loading,
    loadingPrefecture,
    meshCoords,
    meshRisksAtTime,
    prefectureRiskData,
    selectedPrefecture,
    selectedTime,
    sessionId,
    sessionInfo,
    setIsAdjustedData,
    setPrefectureRiskData,
    setSessionId,
  } = useProductionSession({
    swiInitialTime,
    guidanceInitialTime,
    guidanceType,
    riskRule,
  });

  // 日付・時刻変更時にISO文字列を更新
  useEffect(() => {
    const iso = buildIsoStringFromJst(swiDate, swiHour);
    if (iso) setSwiInitialTime(iso);
  }, [swiDate, swiHour]);

  useEffect(() => {
    const iso = buildIsoStringFromJst(guidanceDate, guidanceHour);
    if (iso) setGuidanceInitialTime(iso);
  }, [guidanceDate, guidanceHour]);

  useEffect(() => {
    const defaultSelection = getDefaultJstSelection();
    setSwiDate(defaultSelection.date);
    setSwiHour(defaultSelection.hour);
    setGuidanceDate(defaultSelection.date);
    setGuidanceHour(defaultSelection.hour);
  }, []);

  useEffect(() => {
    const guidanceOptions = getGuidanceHourOptions(guidanceType);

    if (!guidanceOptions.includes(guidanceHour)) {
      const defaultSelection = getDefaultJstSelection(guidanceType);
      setGuidanceHour(defaultSelection.hour);
      if (!guidanceDate) {
        setGuidanceDate(defaultSelection.date);
      }
    }
  }, [guidanceDate, guidanceHour, guidanceType]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (!sessionInfo) return;
    const availableTimes = sessionInfo.available_times;
    if (availableTimes.length === 0) return;

    const currentIndex = availableTimes.indexOf(selectedTime);
    if (currentIndex === -1) return;

    if (e.key === 'ArrowLeft' && currentIndex > 0) {
      handleTimeChange(availableTimes[currentIndex - 1]);
    } else if (e.key === 'ArrowRight' && currentIndex < availableTimes.length - 1) {
      handleTimeChange(availableTimes[currentIndex + 1]);
    }
  };
  const guidanceHourOptions = getGuidanceHourOptions(guidanceType);

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

        <div style={{
          backgroundColor: '#fff3cd',
          padding: '10px 15px',
          borderRadius: '4px',
          marginBottom: '15px',
          fontSize: '14px',
          border: '1px solid #ffc107'
        }}>
          <strong>注意:</strong> 気象庁データはデータ時刻から約3時間後に利用可能になります。
          最新時刻を選択するとエラーになる場合があります。
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            危険度ルール
          </label>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input
                type="radio"
                name="riskRule"
                value="legacy"
                checked={riskRule === 'legacy'}
                onChange={() => setRiskRule('legacy')}
              />
              従来ルール
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input
                type="radio"
                name="riskRule"
                value="lead_time_to_level4"
                checked={riskRule === 'lead_time_to_level4'}
                onChange={() => setRiskRule('lead_time_to_level4')}
              />
              レベル4先行ルール
            </label>
          </div>
          <div style={{ fontSize: '12px', color: '#666', marginTop: '6px' }}>
            レベル4に最初に到達する2時間前以降をレベル3、6時間前以降をレベル2として扱います。
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            ガイダンス種別
          </label>
          <div style={{ display: 'flex', gap: '12px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input
                type="radio"
                name="guidanceType"
                value="msm"
                checked={guidanceType === 'msm'}
                onChange={() => setGuidanceType('msm')}
              />
              MSM
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input
                type="radio"
                name="guidanceType"
                value="gsm"
                checked={guidanceType === 'gsm'}
                onChange={() => setGuidanceType('gsm')}
              />
              GSM
            </label>
          </div>
          <div style={{ fontSize: '12px', color: '#666', marginTop: '6px' }}>
            {guidanceType === 'gsm'
              ? 'GSM は JST では 03, 09, 15, 21 時を選択できます。'
              : 'MSM は 3 時間ごとの初期時刻を選択できます。'}
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
          {/* SWI初期時刻選択 */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              SWI初期時刻（土壌雨量指数）
            </label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input
                type="date"
                value={swiDate}
                onChange={(e) => setSwiDate(e.target.value)}
                min="2015-01-01"
                style={{ flex: 2, padding: '8px', fontSize: '14px' }}
              />
              <select
                value={swiHour}
                onChange={(e) => setSwiHour(Number(e.target.value))}
                style={{ flex: 1, padding: '8px', fontSize: '14px' }}
              >
                {MSM_HOUR_OPTIONS.map(hour => (
                  <option key={hour} value={hour}>
                    {hour.toString().padStart(2, '0')}:00
                  </option>
                ))}
              </select>
            </div>
            {swiInitialTime && (
              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                UTC: {swiInitialTime}
              </div>
            )}
          </div>

          {/* ガイダンス初期時刻選択 */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              ガイダンス初期時刻（降水量予測）
            </label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input
                type="date"
                value={guidanceDate}
                onChange={(e) => setGuidanceDate(e.target.value)}
                min="2015-01-01"
                style={{ flex: 2, padding: '8px', fontSize: '14px' }}
              />
              <select
                value={guidanceHour}
                onChange={(e) => setGuidanceHour(Number(e.target.value))}
                style={{ flex: 1, padding: '8px', fontSize: '14px' }}
              >
                {guidanceHourOptions.map(hour => (
                  <option key={hour} value={hour}>
                    {hour.toString().padStart(2, '0')}:00
                  </option>
                ))}
              </select>
            </div>
            {guidanceInitialTime && (
              <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                UTC: {guidanceInitialTime}
              </div>
            )}
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
            onClick={() => {
              // モーダルを開くだけ（データ取得はモーダル側で1回のみ行う）
              if (sessionId) {
                setIsRainfallModalOpen(true);
              }
            }}
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
                  {prefectureRiskData[code] && ' ✓'}
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
          {prefectureRiskData[selectedPrefecture] && (
            <div onKeyDown={handleKeyPress} tabIndex={0}>
              <SoilRainfallMap
                meshRisks={meshRisksAtTime}
                meshCoords={meshCoords}
                selectedTime={selectedTime}
                selectedPrefecture={selectedPrefecture}
                swiInitialTime={sessionInfo.swi_initial_time}
                guidanceInitialTime={sessionInfo.guidance_initial_time}
              />

              <div style={{ marginTop: '30px' }}>
                <AreaRiskBarChart
                  prefectures={Object.values(prefectureRiskData).filter(p => p !== undefined) as PrefectureType[]}
                  availablePrefectures={sessionInfo.available_prefectures.map(code => ({
                    code,
                    name: PREFECTURE_NAME_MAP[code] || code,
                  }))}
                  selectedPrefecture={selectedPrefecture}
                  selectedTime={selectedTime}
                  onPrefectureChange={handlePrefectureChange}
                  onTimeSelect={handleTimeChange}
                  onViewModeChange={(mode) => {
                    if (mode === 'prefecture-all') {
                      loadAllPrefectures();
                    }
                  }}
                  initialTime={sessionInfo.swi_initial_time}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* 雨量調整モーダル（セッションベース） */}
      {sessionInfo && sessionId && (
        <RainfallAdjustmentModalSession
          isOpen={isRainfallModalOpen}
          onClose={() => setIsRainfallModalOpen(false)}
          sessionId={sessionId}
          swiInitial={swiInitialTime}
          guidanceInitial={guidanceInitialTime}
          guidanceType={sessionInfo.guidance_type ?? guidanceType}
          dataSource="production"
          onSessionRecalculated={async (newSessionId, _meshRisks, _newMeshCoords) => {
            // フォークセッションIDに切り替え（以降の時刻変更で編集済みデータを取得するため）
            setSessionId(newSessionId);
            setIsAdjustedData(true);
            // 府県リスクデータキャッシュをクリア（ベースセッションのデータが古いため）
            setPrefectureRiskData({});

            // 現在選択中の時刻のリスクデータをフォークセッションから読み込み
            // （FT=0は初期状態で雨量変更前と同じため、選択中時刻を維持する）
            await loadRiskAtTime(newSessionId, selectedTime);

            // 選択中の府県をフォークセッションから再読み込み
            if (selectedPrefecture) {
              try {
                const response = await sessionApiClient.getPrefectureData(newSessionId, selectedPrefecture);
                if (response.status === 'success') {
                  setPrefectureRiskData(prev => ({
                    ...prev,
                    [selectedPrefecture]: response.prefecture
                  }));
                }
              } catch (err) {
                console.error('府県データ再読み込みエラー:', err);
              }
            }
          }}
        />
      )}
    </div>
  );
};

export default ProductionSession;

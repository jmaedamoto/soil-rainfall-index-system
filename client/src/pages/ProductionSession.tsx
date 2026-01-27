import React, { useState, useEffect } from 'react';
import { apiClient_, USE_MOCK_PRODUCTION_API } from '../services/api';
import { sessionApiClient } from '../services/sessionApi';
import SoilRainfallMap from '../components/map/SoilRainfallMap';
import AreaRiskBarChart from '../components/charts/AreaRiskBarChart';
import CacheInfo from '../components/CacheInfo';
import RainfallAdjustmentModalSession from '../components/RainfallAdjustmentModalSession';
import { LightweightPrefectureData, Mesh, LightweightCalculationResult, CalculationResult, Prefecture as PrefectureType } from '../types/api';

const ProductionSession: React.FC = () => {
  // セッション情報
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionInfo, setSessionInfo] = useState<LightweightCalculationResult | null>(null);

  // 府県データ（危険度時系列のみ、オンデマンド読み込み）
  const [prefectureRiskData, setPrefectureRiskData] = useState<Record<string, LightweightPrefectureData>>({});

  // 地図表示用の時刻別リスク値（全メッシュ）
  const [meshRisksAtTime, setMeshRisksAtTime] = useState<Record<string, number>>({});
  const [meshCoords, setMeshCoords] = useState<Record<string, { lat: number; lon: number }>>({});

  // モックモード用: 全データをキャッシュ
  const [cachedFullData, setCachedFullData] = useState<CalculationResult | null>(null);

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
  const [rainfallData, setRainfallData] = useState<Record<string, any> | null>(null);

  // 時刻オプション（3時間刻み: 0, 3, 6, 9, 12, 15, 18, 21時）
  const timeHourOptions = [0, 3, 6, 9, 12, 15, 18, 21];

  // 日付と時刻を個別に管理（JST）
  const [swiDate, setSwiDate] = useState<string>('');
  const [swiHour, setSwiHour] = useState<number>(0);
  const [guidanceDate, setGuidanceDate] = useState<string>('');
  const [guidanceHour, setGuidanceHour] = useState<number>(0);

  // 日付と時刻からISO文字列（UTC）を生成
  const buildIsoString = (date: string, hour: number): string => {
    if (!date) return '';
    // 入力はJSTなので、UTCに変換（-9時間）
    const jstDate = new Date(`${date}T${hour.toString().padStart(2, '0')}:00:00+09:00`);
    return jstDate.toISOString();
  };

  // 日付・時刻変更時にISO文字列を更新
  useEffect(() => {
    const iso = buildIsoString(swiDate, swiHour);
    if (iso) setSwiInitialTime(iso);
  }, [swiDate, swiHour]);

  useEffect(() => {
    const iso = buildIsoString(guidanceDate, guidanceHour);
    if (iso) setGuidanceInitialTime(iso);
  }, [guidanceDate, guidanceHour]);

  useEffect(() => {
    // デフォルトの日付・時刻を設定（現在時刻から最新の3時間刻み）
    const now = new Date();
    // JSTに変換
    const jstNow = new Date(now.getTime() + 9 * 60 * 60 * 1000);
    const year = jstNow.getUTCFullYear();
    const month = (jstNow.getUTCMonth() + 1).toString().padStart(2, '0');
    const day = jstNow.getUTCDate().toString().padStart(2, '0');
    const hour = Math.floor(jstNow.getUTCHours() / 3) * 3;

    const defaultDate = `${year}-${month}-${day}`;
    setSwiDate(defaultDate);
    setSwiHour(hour);
    setGuidanceDate(defaultDate);
    setGuidanceHour(hour);
  }, []);

  // meshRisksAtTime監視用
  useEffect(() => {
    console.log(`[meshRisksAtTime変更検知] メッシュ数: ${Object.keys(meshRisksAtTime).length}`);
    if (Object.keys(meshRisksAtTime).length > 0) {
      console.log(`[meshRisksAtTime変更検知] サンプル値:`, Object.entries(meshRisksAtTime).slice(0, 5));
    }
  }, [meshRisksAtTime]);

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

      // セッションAPIを使用してデータを読み込み
      // デフォルトで最初の都道府県を選択
      if (result.available_prefectures.length > 0) {
        const firstPrefCode = result.available_prefectures[0];
        setSelectedPrefecture(firstPrefCode);
        // 最初の府県データを読み込み
        await loadPrefectureData(result.session_id, firstPrefCode);
      }

      // 初期時刻のメッシュリスク値を読み込み
      if (result.available_times.length > 0) {
        const initialTime = result.available_times[0];
        setSelectedTime(initialTime);
        await loadRiskAtTime(result.session_id, initialTime);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '予期しないエラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  const loadRiskAtTime = async (session: string, ft: number) => {
    // セッションAPIを使用して指定時刻のリスク値を取得
    try {
      console.log(`[loadRiskAtTime] セッションID: ${session}, FT: ${ft}`);
      const response = await sessionApiClient.getRiskAtTime(session, ft);
      console.log(`[loadRiskAtTime] APIレスポンス:`, response);

      if (response.status === 'success') {
        console.log(`[loadRiskAtTime] メッシュリスク数: ${Object.keys(response.mesh_risks).length}`);
        console.log(`[loadRiskAtTime] メッシュ座標数: ${Object.keys(response.mesh_coords).length}`);
        console.log(`[loadRiskAtTime] サンプルリスク値:`, Object.entries(response.mesh_risks).slice(0, 3));

        setMeshRisksAtTime(response.mesh_risks);
        setMeshCoords(response.mesh_coords);
      }
    } catch (err) {
      console.error(`メッシュリスク値読み込みエラー (FT=${ft}):`, err);
    }
  };

  const loadPrefectureData = async (session: string, prefectureCode: string) => {
    // 既に読み込み済みの場合はスキップ
    if (prefectureRiskData[prefectureCode]) {
      return;
    }

    try {
      setLoadingPrefecture(prefectureCode);
      const response = await sessionApiClient.getPrefectureData(session, prefectureCode);

      if (response.status === 'success') {
        setPrefectureRiskData(prev => ({
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

  // 全府県データを読み込む（全府県一覧モード用）
  const loadAllPrefectures = async () => {
    if (!sessionId || !sessionInfo) return;

    // 未読み込みの府県を特定
    const unloadedPrefectures = sessionInfo.available_prefectures.filter(
      code => !prefectureRiskData[code]
    );

    if (unloadedPrefectures.length === 0) {
      return; // すべて読み込み済み
    }

    // 並列で読み込み
    try {
      const promises = unloadedPrefectures.map(prefCode =>
        sessionApiClient.getPrefectureData(sessionId, prefCode)
      );

      const results = await Promise.all(promises);

      // 結果を統合
      const newData: Record<string, LightweightPrefectureData> = { ...prefectureRiskData };
      results.forEach((response, index) => {
        if (response.status === 'success') {
          newData[unloadedPrefectures[index]] = response.prefecture;
        }
      });

      setPrefectureRiskData(newData);
    } catch (err) {
      console.error('全府県データ読み込みエラー:', err);
    }
  };

  // 日時フォーマット関数（JST表示）
  const formatDateTime = (isoString: string) => {
    const date = new Date(isoString);
    const jstDate = new Date(date.getTime() + 9 * 60 * 60 * 1000);
    return `${jstDate.getUTCFullYear()}年${jstDate.getUTCMonth() + 1}月${jstDate.getUTCDate()}日 ${jstDate.getUTCHours()}時 (JST)`;
  };

  const handleTimeChange = async (newTime: number) => {
    console.log(`[handleTimeChange] 時刻変更: ${selectedTime} -> ${newTime}`);

    // 同じ時刻が選択された場合は何もしない
    if (newTime === selectedTime) {
      console.log(`[handleTimeChange] 同じ時刻のためスキップ`);
      return;
    }

    // ローディング状態を即座に設定
    setIsTimeChanging(true);

    try {
      // 状態更新
      setSelectedTime(newTime);
      console.log(`[handleTimeChange] selectedTime更新: ${newTime}`);

      // セッションIDがあれば、新しい時刻のメッシュリスク値を読み込み
      if (sessionId) {
        console.log(`[handleTimeChange] loadRiskAtTime呼び出し開始`);
        await loadRiskAtTime(sessionId, newTime);
        console.log(`[handleTimeChange] loadRiskAtTime呼び出し完了`);
      } else {
        console.warn(`[handleTimeChange] sessionIDが未設定`);
      }
    } finally {
      // ローディング解除
      requestAnimationFrame(() => {
        setTimeout(() => setIsTimeChanging(false), 50);
      });
    }
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
                {timeHourOptions.map(hour => (
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
                {timeHourOptions.map(hour => (
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
            onClick={async () => {
              // セッションベース雨量調整を開く
              if (sessionId) {
                // セッションから雨量データを取得
                try {
                  const data = await sessionApiClient.getRainfallData(sessionId);
                  // Prefecture型の形式に変換
                  const prefectureData: Record<string, any> = {};

                  // 府県別にグループ化
                  const prefGroups: Record<string, any> = {};

                  // 市町村データから府県を初期化
                  Object.keys(data.area_rainfall).forEach(key => {
                    const [prefName] = key.split('_');
                    if (!prefGroups[prefName]) {
                      prefGroups[prefName] = {
                        name: prefName,
                        code: prefName.toLowerCase(),
                        areas: [],
                        secondary_subdivisions: []
                      };
                    }
                  });

                  // 市町村データを追加
                  Object.entries(data.area_rainfall).forEach(([key, timeline]) => {
                    const [prefName, areaName] = key.split('_');
                    if (prefGroups[prefName]) {
                      prefGroups[prefName].areas.push({
                        name: areaName,
                        meshes: [{
                          rain_timeline: timeline
                        }]
                      });
                    }
                  });

                  // 二次細分データを追加
                  Object.entries(data.subdivision_rainfall).forEach(([key, timeline]) => {
                    const [prefName, subdivName] = key.split('_');
                    if (prefGroups[prefName]) {
                      prefGroups[prefName].secondary_subdivisions.push({
                        name: subdivName,
                        rain_3hour_timeline: timeline
                      });
                    }
                  });

                  Object.assign(prefectureData, prefGroups);
                  setRainfallData(prefectureData);
                  setIsRainfallModalOpen(true);
                } catch (err) {
                  console.error('雨量データ取得エラー:', err);
                  setError('雨量データの取得に失敗しました');
                }
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
                  availablePrefectures={sessionInfo.available_prefectures.map(code => {
                    const nameMap: Record<string, string> = {
                      'shiga': '滋賀県',
                      'kyoto': '京都府',
                      'osaka': '大阪府',
                      'hyogo': '兵庫県',
                      'nara': '奈良県',
                      'wakayama': '和歌山県'
                    };
                    return { code, name: nameMap[code] || code };
                  })}
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
          dataSource="test"
          onSessionRecalculated={(meshRisks, meshCoords) => {
            // セッションが更新されたので、メッシュリスクと座標を更新
            setMeshRisksAtTime(meshRisks);
            setMeshCoords(meshCoords);
            setIsAdjustedData(true);
            setSelectedTime(0); // FT=0に戻す
          }}
        />
      )}
    </div>
  );
};

export default ProductionSession;

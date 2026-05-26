import { useEffect, useRef, useState } from 'react';
import { apiClient_ } from '../../../services/api';
import { sessionApiClient } from '../../../services/sessionApi';
import type {
  LightweightCalculationResult,
  LightweightPrefectureData,
} from '../../../types/session';

interface UseProductionSessionParams {
  swiInitialTime: string;
  guidanceInitialTime: string;
  guidanceType?: 'msm' | 'gsm';
  riskRule?: 'legacy' | 'lead_time_to_level4';
}

export const useProductionSession = ({
  swiInitialTime,
  guidanceInitialTime,
  guidanceType = 'msm',
  riskRule = 'legacy',
}: UseProductionSessionParams) => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionInfo, setSessionInfo] = useState<LightweightCalculationResult | null>(null);
  const [prefectureRiskData, setPrefectureRiskData] = useState<Record<string, LightweightPrefectureData>>({});
  const [meshRisksAtTime, setMeshRisksAtTime] = useState<Record<string, number>>({});
  const [meshCoords, setMeshCoords] = useState<Record<string, { lat: number; lon: number }>>({});
  const [loading, setLoading] = useState(false);
  const [loadingPrefecture, setLoadingPrefecture] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState(0);
  const [selectedPrefecture, setSelectedPrefecture] = useState('');
  const [isTimeChanging, setIsTimeChanging] = useState(false);
  const [isAdjustedData, setIsAdjustedData] = useState(false);
  const activeLoadRequestIdRef = useRef(0);

  const logFrontendError = (context: string, err: unknown, detail?: Record<string, unknown>) => {
    const errorLike = err as {
      message?: string;
      code?: string;
      response?: { status?: number; statusText?: string; data?: unknown };
    };
    console.error(`[useProductionSession] ${context}`, {
      at: new Date().toISOString(),
      message: errorLike?.message ?? String(err),
      code: errorLike?.code,
      status: errorLike?.response?.status,
      status_text: errorLike?.response?.statusText,
      response_data: errorLike?.response?.data,
      ...detail,
    });
  };

  useEffect(() => {
    if (Object.keys(meshRisksAtTime).length > 0) {
      console.log('[meshRisksAtTime変更検知] サンプル値:', Object.entries(meshRisksAtTime).slice(0, 5));
    }
  }, [meshRisksAtTime]);

  const isLatestLoadRequest = (requestId?: number) => (
    requestId === undefined || requestId === activeLoadRequestIdRef.current
  );

  const loadRiskAtTime = async (targetSessionId: string, ft: number, requestId?: number) => {
    try {
      console.info('[useProductionSession] risk load start', {
        at: new Date().toISOString(),
        session_id: targetSessionId,
        ft,
        request_id: requestId,
      });
      const response = await sessionApiClient.getRiskAtTime(targetSessionId, ft);

      if (!isLatestLoadRequest(requestId)) {
        console.info('[useProductionSession] risk load ignored by stale request id', {
          at: new Date().toISOString(),
          session_id: targetSessionId,
          ft,
          request_id: requestId,
          active_request_id: activeLoadRequestIdRef.current,
        });
        return;
      }

      if (response.status === 'success') {
        console.info('[useProductionSession] risk load success', {
          at: new Date().toISOString(),
          session_id: targetSessionId,
          ft,
          mesh_count: Object.keys(response.mesh_risks).length,
        });
        setMeshRisksAtTime(response.mesh_risks);
        setMeshCoords(response.mesh_coords);
      }
    } catch (err) {
      logFrontendError('メッシュリスク値読み込みエラー', err, {
        session_id: targetSessionId,
        ft,
        request_id: requestId,
      });
    }
  };

  const loadPrefectureData = async (
    targetSessionId: string,
    prefectureCode: string,
    requestId?: number
  ) => {
    if (targetSessionId === sessionId && prefectureRiskData[prefectureCode]) {
      return;
    }

    try {
      setLoadingPrefecture(prefectureCode);
      console.info('[useProductionSession] prefecture load start', {
        at: new Date().toISOString(),
        session_id: targetSessionId,
        prefecture_code: prefectureCode,
        request_id: requestId,
      });
      const response = await sessionApiClient.getPrefectureData(targetSessionId, prefectureCode);
      if (!isLatestLoadRequest(requestId)) {
        console.info('[useProductionSession] prefecture load ignored by stale request id', {
          at: new Date().toISOString(),
          session_id: targetSessionId,
          prefecture_code: prefectureCode,
          request_id: requestId,
          active_request_id: activeLoadRequestIdRef.current,
        });
        return;
      }
      if (response.status === 'success') {
        console.info('[useProductionSession] prefecture load success', {
          at: new Date().toISOString(),
          session_id: targetSessionId,
          prefecture_code: prefectureCode,
          area_count: response.prefecture.areas.length,
        });
        setPrefectureRiskData((prev) => ({
          ...prev,
          [prefectureCode]: response.prefecture,
        }));
      }
    } catch (err) {
      logFrontendError('府県データ読み込みエラー', err, {
        session_id: targetSessionId,
        prefecture_code: prefectureCode,
        request_id: requestId,
      });
    } finally {
      if (isLatestLoadRequest(requestId)) {
        setLoadingPrefecture(null);
      }
    }
  };

  const loadAllPrefectures = async () => {
    if (!sessionId || !sessionInfo) return;

    const unloadedPrefectures = sessionInfo.available_prefectures.filter(
      (code) => !prefectureRiskData[code]
    );

    if (unloadedPrefectures.length === 0) return;

    try {
      const results = await Promise.all(
        unloadedPrefectures.map((prefCode) => sessionApiClient.getPrefectureData(sessionId, prefCode))
      );

      setPrefectureRiskData((prev) => {
        const nextData = { ...prev };
        results.forEach((response, index) => {
          if (response.status === 'success') {
            nextData[unloadedPrefectures[index]] = response.prefecture;
          }
        });
        return nextData;
      });
    } catch (err) {
      console.error('全府県データ読み込みエラー:', err);
    }
  };

  const loadData = async () => {
    if (!swiInitialTime || !guidanceInitialTime) {
      setError('初期時刻を選択してください');
      return;
    }

    const requestId = activeLoadRequestIdRef.current + 1;
    activeLoadRequestIdRef.current = requestId;

    try {
      setLoading(true);
      setError(null);
      setIsAdjustedData(false);
      setMeshRisksAtTime({});
      setMeshCoords({});
      const startedAt = performance.now();
      console.info('[useProductionSession] production load start', {
        at: new Date().toISOString(),
        request_id: requestId,
        swi_initial: swiInitialTime,
        guidance_initial: guidanceInitialTime,
        guidance_type: guidanceType,
        risk_rule: riskRule,
      });

      const result = await apiClient_.calculateProductionSoilRainfallIndexWithUrls({
        swi_initial: swiInitialTime,
        guidance_initial: guidanceInitialTime,
        guidance_type: guidanceType,
        risk_rule: riskRule,
      });

      console.info('[useProductionSession] production load response received', {
        at: new Date().toISOString(),
        request_id: requestId,
        elapsed_ms: Math.round(performance.now() - startedAt),
        session_id: result.session_id,
        prefecture_count: result.available_prefectures.length,
        available_times: result.available_times.length,
      });

      if (!isLatestLoadRequest(requestId)) {
        console.info('[useProductionSession] production load ignored by stale request id', {
          at: new Date().toISOString(),
          request_id: requestId,
          active_request_id: activeLoadRequestIdRef.current,
          session_id: result.session_id,
        });
        return;
      }

      setSessionInfo(result);
      setSessionId(result.session_id);
      setPrefectureRiskData({});

      if (result.available_prefectures.length > 0) {
        const firstPrefCode = result.available_prefectures[0];
        setSelectedPrefecture(firstPrefCode);
        console.info('[useProductionSession] first prefecture load scheduled', {
          at: new Date().toISOString(),
          session_id: result.session_id,
          prefecture_code: firstPrefCode,
          request_id: requestId,
        });
        await loadPrefectureData(result.session_id, firstPrefCode, requestId);
      }

      if (result.available_times.length > 0) {
        const initialTime = result.available_times[0];
        setSelectedTime(initialTime);
        console.info('[useProductionSession] initial risk load scheduled', {
          at: new Date().toISOString(),
          session_id: result.session_id,
          ft: initialTime,
          request_id: requestId,
        });
        await loadRiskAtTime(result.session_id, initialTime, requestId);
      }
    } catch (err) {
      if (isLatestLoadRequest(requestId)) {
        logFrontendError('production load error', err, {
          request_id: requestId,
          swi_initial: swiInitialTime,
          guidance_initial: guidanceInitialTime,
          guidance_type: guidanceType,
          risk_rule: riskRule,
        });
        setError(err instanceof Error ? err.message : '予期しないエラーが発生しました');
      }
    } finally {
      if (isLatestLoadRequest(requestId)) {
        console.info('[useProductionSession] production load finished', {
          at: new Date().toISOString(),
          request_id: requestId,
        });
        setLoading(false);
      }
    }
  };

  const handlePrefectureChange = async (prefCode: string) => {
    setSelectedPrefecture(prefCode);
    if (sessionId) {
      await loadPrefectureData(sessionId, prefCode);
    }
  };

  const handleTimeChange = async (newTime: number) => {
    if (newTime === selectedTime) {
      return;
    }

    setIsTimeChanging(true);

    try {
      setSelectedTime(newTime);
      if (sessionId) {
        await loadRiskAtTime(sessionId, newTime);
      }
    } finally {
      requestAnimationFrame(() => {
        setTimeout(() => setIsTimeChanging(false), 50);
      });
    }
  };

  return {
    error,
    handlePrefectureChange,
    handleTimeChange,
    isAdjustedData,
    isTimeChanging,
    loadAllPrefectures,
    loadData,
    loadPrefectureData,
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
    setError,
    setIsAdjustedData,
    setPrefectureRiskData,
    setSelectedPrefecture,
    setSelectedTime,
    setSessionId,
    setSessionInfo,
  };
};

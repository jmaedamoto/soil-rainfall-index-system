import { useEffect, useState } from 'react';
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

  useEffect(() => {
    if (Object.keys(meshRisksAtTime).length > 0) {
      console.log('[meshRisksAtTime変更検知] サンプル値:', Object.entries(meshRisksAtTime).slice(0, 5));
    }
  }, [meshRisksAtTime]);

  const loadRiskAtTime = async (targetSessionId: string, ft: number) => {
    try {
      const needCoords = Object.keys(meshCoords).length === 0;
      const response = await sessionApiClient.getRiskAtTime(targetSessionId, ft, {
        includeCoords: needCoords,
      });

      if (response.status === 'success') {
        setMeshRisksAtTime(response.mesh_risks);

        if (needCoords && response.mesh_coords) {
          setMeshCoords(response.mesh_coords);
        }
      }
    } catch (err) {
      console.error(`メッシュリスク値読み込みエラー (FT=${ft}):`, err);
    }
  };

  const loadPrefectureData = async (targetSessionId: string, prefectureCode: string) => {
    if (prefectureRiskData[prefectureCode]) {
      return;
    }

    try {
      setLoadingPrefecture(prefectureCode);
      const response = await sessionApiClient.getPrefectureData(targetSessionId, prefectureCode);
      if (response.status === 'success') {
        setPrefectureRiskData((prev) => ({
          ...prev,
          [prefectureCode]: response.prefecture,
        }));
      }
    } catch (err) {
      console.error(`府県データ読み込みエラー (${prefectureCode}):`, err);
    } finally {
      setLoadingPrefecture(null);
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

    try {
      setLoading(true);
      setError(null);
      setIsAdjustedData(false);
      setMeshCoords({});

      const result = await apiClient_.calculateProductionSoilRainfallIndexWithUrls({
        swi_initial: swiInitialTime,
        guidance_initial: guidanceInitialTime,
        guidance_type: guidanceType,
        risk_rule: riskRule,
      });

      setSessionInfo(result);
      setSessionId(result.session_id);
      setPrefectureRiskData({});

      if (result.available_prefectures.length > 0) {
        const firstPrefCode = result.available_prefectures[0];
        setSelectedPrefecture(firstPrefCode);
        await loadPrefectureData(result.session_id, firstPrefCode);
      }

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
  };
};

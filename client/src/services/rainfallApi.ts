import axios from 'axios';
import type { AreaRainfallForecast, RainfallAdjustmentRequest, CalculationResult } from '../types/api';

// APIのベースURL（環境に応じて自動設定）
const getApiBaseUrl = (): string => {
  // 本番環境では同一オリジンの相対パス
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return '';
  }
  // 開発環境ではローカルホスト
  return 'http://localhost:5000';
};

const API_BASE_URL = getApiBaseUrl();

/**
 * 市町村ごとの雨量予想時系列を取得
 */
export const getRainfallForecast = async (
  swiInitial: string,
  guidanceInitial: string
): Promise<AreaRainfallForecast> => {
  const response = await axios.get<AreaRainfallForecast>(
    `${API_BASE_URL}/api/rainfall-forecast`,
    {
      params: {
        swi_initial: swiInitial,
        guidance_initial: guidanceInitial
      },
      timeout: 300000 // 5分タイムアウト
    }
  );
  return response.data;
};

/**
 * 調整後雨量でSWI・危険度を再計算
 */
export const calculateWithAdjustedRainfall = async (
  request: RainfallAdjustmentRequest
): Promise<CalculationResult> => {
  const response = await axios.post<CalculationResult>(
    `${API_BASE_URL}/api/rainfall-adjustment`,
    request,
    {
      timeout: 300000 // 5分タイムアウト
    }
  );
  return response.data;
};

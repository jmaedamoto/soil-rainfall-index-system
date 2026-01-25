import axios from 'axios';
import type { AreaRainfallForecast, RainfallAdjustmentRequest, CalculationResult } from '../types/api';
import { API_BASE_URL } from '../config/apiConfig';

/**
 * 市町村ごとの雨量予想時系列を取得
 */
export const getRainfallForecast = async (
  swiInitial: string,
  guidanceInitial: string
): Promise<AreaRainfallForecast> => {
  const response = await axios.get<AreaRainfallForecast>(
    `${API_BASE_URL}/rainfall-forecast`,
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
    `${API_BASE_URL}/rainfall-adjustment`,
    request,
    {
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 300000 // 5分タイムアウト
    }
  );
  return response.data;
};

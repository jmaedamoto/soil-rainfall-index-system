import axios from 'axios';
import { HealthStatus } from '../types/api';
import type { LightweightCalculationResult } from '../types/session';
import { API_BASE_URL } from '../config/apiConfig';

// Axiosインスタンスの作成
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 300秒（5分）タイムアウト
  headers: {
    'Content-Type': 'application/json',
  },
});

// レスポンスインターセプター（エラーハンドリング）
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // サーバーエラーレスポンス
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      // ネットワークエラー
      console.error('Network Error:', error.request);
    } else {
      // その他のエラー
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export class SoilRainfallAPIClient {
  /**
   * ヘルスチェック
   */
  async getHealthStatus(): Promise<HealthStatus> {
    try {
      const response = await apiClient.get('/health');
      const data = response.data;

      // サーバーレスポンスをそのまま返す
      return {
        status: data.status,
        message: data.message,
        architecture: data.architecture,
        version: data.version
      };
    } catch (error) {
      return { status: 'error', message: 'APIサーバーに接続できません' };
    }
  }

  /**
   * 本番用土壌雨量指数計算（SWIとガイダンスの初期時刻を個別指定）
   * セッションベースAPIを使用し、軽量レスポンスを返す
   * ローカルbin使用の有無はサーバー設定で制御される
   */
  async calculateProductionSoilRainfallIndexWithUrls(params: {
    swi_initial: string;
    guidance_initial: string;
    guidance_type?: 'msm' | 'gsm';
    risk_rule?: 'legacy' | 'lead_time_to_level4';
  }): Promise<LightweightCalculationResult> {
    const response = await apiClient.post<LightweightCalculationResult>(
      '/production-soil-rainfall-index-with-urls',
      params
    );
    return response.data;
  }
}

// シングルトンインスタンス
export const apiClient_ = new SoilRainfallAPIClient();

import axios from 'axios';
import { HealthStatus } from '../types/api';
import type { LightweightCalculationResult } from '../types/session';
import { API_BASE_URL } from '../config/apiConfig';
import type { RegionCode } from '../features/production-session/regions';

type ProductionCalculationParams = {
  swi_initial: string;
  guidance_initial: string;
  guidance_type?: 'msm' | 'gsm';
  risk_rule?: 'legacy' | 'lead_time_to_level4';
  region?: RegionCode;
};

// Axiosインスタンスの作成
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 600秒（10分）タイムアウト
  headers: {
    'Content-Type': 'application/json',
  },
});

// レスポンスインターセプター（エラーハンドリング）
apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
);

const isCalculationRequestTimeout = (error: unknown): boolean => (
  axios.isAxiosError(error)
  && (error.response?.status === 504 || error.code === 'ECONNABORTED')
);

const CALCULATION_POLL_INTERVAL_MS = 2000;
const CALCULATION_POLL_TIMEOUT_MS = 10 * 60 * 1000;

const wait = (milliseconds: number): Promise<void> => (
  new Promise((resolve) => setTimeout(resolve, milliseconds))
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
  async calculateProductionSoilRainfallIndexWithUrls(
    params: ProductionCalculationParams
  ): Promise<LightweightCalculationResult> {
    const startedAt = Date.now();

    while (Date.now() - startedAt < CALCULATION_POLL_TIMEOUT_MS) {
      try {
        const response = await this.postProductionCalculation(params);
        if (response.status === 200 && response.data.status === 'success') {
          return response.data;
        }
        if (response.status !== 202) {
          throw new Error(response.data.message || '計算結果の取得に失敗しました');
        }
      } catch (error) {
        if (!isCalculationRequestTimeout(error)) {
          throw error;
        }
        console.warn('Calculation request timed out. Polling the cache.');
      }

      await wait(CALCULATION_POLL_INTERVAL_MS);
    }

    throw new Error('計算が10分以内に完了しませんでした。しばらくして再実行してください。');
  }

  private postProductionCalculation(params: ProductionCalculationParams) {
    return apiClient.post<LightweightCalculationResult & {
      message?: string;
      retry_after?: number;
    }>(
      '/production-soil-rainfall-index-with-urls',
      params
    );
  }
}

// シングルトンインスタンス
export const apiClient_ = new SoilRainfallAPIClient();

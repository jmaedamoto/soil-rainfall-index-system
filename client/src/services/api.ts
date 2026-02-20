import axios from 'axios';
import { HealthStatus, LightweightCalculationResult } from '../types/api';
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
  (error) => Promise.reject(error)
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
   * リモートダウンロード失敗時はサーバー側でローカルbinファイルにフォールバック
   */
  async calculateProductionSoilRainfallIndexWithUrls(params: {
    swi_initial: string;
    guidance_initial: string;
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

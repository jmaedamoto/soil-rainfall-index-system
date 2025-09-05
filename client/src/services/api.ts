import axios from 'axios';
import { CalculationParams, CalculationResult, HealthStatus } from '../types/api';

// APIベースURL（開発環境用）
const API_BASE_URL = 'http://localhost:5000/api';

// Axiosインスタンスの作成
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120秒（2分）タイムアウト
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
      
      // サーバーレスポンス形式に合わせて変換
      if (data.status === 'healthy') {
        return { status: 'ok' };
      } else {
        return { status: 'error', message: data.message || 'サーバーエラー' };
      }
    } catch (error) {
      return { status: 'error', message: 'APIサーバーに接続できません' };
    }
  }

  /**
   * 土壌雨量指数計算の実行
   */
  async calculateSoilRainfallIndex(params: CalculationParams): Promise<CalculationResult> {
    const response = await apiClient.post<CalculationResult>('/soil-rainfall-index', params);
    return response.data;
  }

  /**
   * テスト用フル計算（開発用）
   */
  async testFullCalculation(): Promise<CalculationResult> {
    const response = await apiClient.get<CalculationResult>('/test-full-soil-rainfall-index');
    return response.data;
  }

  /**
   * テスト用計算（時刻指定対応版）
   */
  async testCalculationWithTime(params: CalculationParams): Promise<CalculationResult> {
    // テスト用エンドポイントでは時刻指定は無視し、固定データを返す
    console.log('テスト環境での時刻指定パラメータ:', params);
    const response = await apiClient.get<CalculationResult>('/test-full-soil-rainfall-index');
    
    // レスポンスに時刻情報を追加
    const result = response.data;
    if (params.swi_initial) {
      result.swi_initial_time = params.swi_initial;
    }
    if (params.guid_initial) {
      result.guid_initial_time = params.guid_initial;
    }
    
    return result;
  }

  /**
   * 本番用土壌雨量指数計算（時刻指定対応）
   */
  async calculateProductionSoilRainfallIndex(params?: { initial?: string }): Promise<CalculationResult> {
    const queryParams = params?.initial ? `?initial=${encodeURIComponent(params.initial)}` : '';
    const response = await apiClient.get<CalculationResult>(`/production-soil-rainfall-index${queryParams}`);
    return response.data;
  }

  /**
   * パフォーマンス分析（デバッグ用）
   */
  async getPerformanceAnalysis(): Promise<any> {
    try {
      const response = await apiClient.get('/test-performance-analysis');
      return response.data;
    } catch (error) {
      console.log('パフォーマンス分析エンドポイントが利用できません');
      return null;
    }
  }

  /**
   * CSV最適化テスト（デバッグ用）
   */
  async getCSVOptimizationTest(): Promise<any> {
    try {
      const response = await apiClient.get('/test-csv-optimization');
      return response.data;
    } catch (error) {
      console.log('CSV最適化テストエンドポイントが利用できません');
      return null;
    }
  }

  /**
   * データチェック
   */
  async getDataCheck(): Promise<any> {
    try {
      const response = await apiClient.get('/data-check');
      return response.data;
    } catch (error) {
      console.log('データチェックエンドポイントが利用できません');
      return null;
    }
  }
}

// シングルトンインスタンス
export const apiClient_ = new SoilRainfallAPIClient();
import axios from 'axios';
import { CalculationParams, CalculationResult, HealthStatus } from '../types/api';
import { mockProductionApi } from './mockProductionApi';

// APIベースURL（環境に応じて自動設定）
const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? '/api'  // 本番環境：同一オリジンの相対パス
  : 'http://localhost:5000/api';  // 開発環境：localhost指定

// モックモードフラグ（開発環境でのみ有効）
const USE_MOCK_PRODUCTION_API = process.env.NODE_ENV !== 'production' && true;

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
    return response.data;
  }

  /**
   * 本番用土壌雨量指数計算（時刻指定対応）
   */
  async calculateProductionSoilRainfallIndex(params?: { initial?: string }): Promise<CalculationResult> {
    // モックモードの場合はテストデータを返す
    if (USE_MOCK_PRODUCTION_API) {
      return mockProductionApi.calculateProductionSoilRainfallIndex(params);
    }

    // 通常モード: 実際のAPIを呼び出す
    const queryParams = params?.initial ? `?initial=${encodeURIComponent(params.initial)}` : '';
    const response = await apiClient.get<CalculationResult>(`/production-soil-rainfall-index${queryParams}`);
    return response.data;
  }

  /**
   * 本番用土壌雨量指数計算（SWIとガイダンスの初期時刻を個別指定）
   */
  async calculateProductionSoilRainfallIndexWithUrls(params: {
    swi_initial: string;
    guidance_initial: string;
  }): Promise<CalculationResult> {
    // モックモードの場合はテストデータを返す
    if (USE_MOCK_PRODUCTION_API) {
      return mockProductionApi.calculateProductionSoilRainfallIndexWithUrls(params);
    }

    // 通常モード: 実際のAPIを呼び出す
    const response = await apiClient.post<CalculationResult>('/production-soil-rainfall-index-with-urls', params);
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
import axios from 'axios';
import { CalculationParams, CalculationResult, HealthStatus, LightweightCalculationResult } from '../types/api';
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
   * セッションベースAPIを使用し、軽量レスポンスを返す
   */
  async calculateProductionSoilRainfallIndexWithUrls(params: {
    swi_initial: string;
    guidance_initial: string;
  }): Promise<LightweightCalculationResult> {
    // モックモードの場合はテストデータを返す（互換性のため従来形式）
    if (USE_MOCK_PRODUCTION_API) {
      const mockResult = await mockProductionApi.calculateProductionSoilRainfallIndexWithUrls(params);
      // モックデータをLightweightCalculationResultに変換
      return {
        status: mockResult.status,
        session_id: 'mock_session_' + Date.now(),
        swi_initial_time: mockResult.swi_initial_time || mockResult.initial_time,
        guidance_initial_time: mockResult.guid_initial_time || mockResult.initial_time,
        available_prefectures: Object.keys(mockResult.prefectures),
        available_times: this.extractAvailableTimes(mockResult),
        cache_info: mockResult.cache_info,
        used_urls: mockResult.used_urls
      };
    }

    // 通常モード: セッションベースAPIを呼び出す
    const response = await apiClient.post<LightweightCalculationResult>(
      '/production-soil-rainfall-index-with-urls',
      params
    );
    return response.data;
  }

  /**
   * 利用可能な時刻を抽出（ヘルパー関数）
   */
  private extractAvailableTimes(result: CalculationResult): number[] {
    const firstPref = Object.values(result.prefectures)[0];
    if (!firstPref?.areas?.[0]?.meshes?.[0]) return [];

    const firstMesh = firstPref.areas[0].meshes[0];
    const times = new Set<number>();

    firstMesh.risk_3hour_max_timeline?.forEach(point => times.add(point.ft));

    return Array.from(times).sort((a, b) => a - b);
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
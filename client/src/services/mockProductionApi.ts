import axios from 'axios';
import { CalculationResult } from '../types/api';

/**
 * 本番環境APIのモック（開発環境用）
 *
 * 日時指定に関わらず、server/dataのテストGRIB2ファイルを使用してサーバーから計算結果を取得
 * テストデータ: Z__C_RJTD_20230602000000_*.bin (2023年6月2日)
 */
export class MockProductionAPI {
  private apiBaseUrl: string;

  constructor() {
    // 開発環境のサーバーURL
    this.apiBaseUrl = 'http://localhost:5000/api';
  }

  /**
   * 本番用土壌雨量指数計算のモック（SWIとガイダンスの初期時刻を個別指定）
   *
   * @param params - 初期時刻パラメータ（モックでは無視され、server/dataのテストファイルを使用）
   * @returns server/dataのテストGRIB2ファイルを使った計算結果
   */
  async calculateProductionSoilRainfallIndexWithUrls(params: {
    swi_initial: string;
    guidance_initial: string;
  }): Promise<CalculationResult> {
    console.log('🎭 [モック] サーバーのテストデータで本番環境をエミュレート中...');
    console.log('  指定されたSWI初期時刻:', params.swi_initial);
    console.log('  指定されたガイダンス初期時刻:', params.guidance_initial);
    console.log('  実際に使用: server/data/Z__C_RJTD_20230602000000_*.bin');

    try {
      // サーバーのテストエンドポイントを呼び出し（日時指定は無視される）
      const response = await axios.get<CalculationResult>(
        `${this.apiBaseUrl}/test-full-soil-rainfall-index`,
        { timeout: 300000 }  // 5分タイムアウト
      );

      console.log('  ✅ サーバーからテストデータを取得完了');

      return response.data;
    } catch (error) {
      console.error('  ❌ サーバーからのテストデータ取得エラー:', error);
      throw new Error('テストデータの取得に失敗しました。サーバーが起動しているか確認してください。');
    }
  }

  /**
   * 本番用土壌雨量指数計算のモック（初期時刻指定版）
   *
   * @param params - 初期時刻パラメータ（モックでは無視され、server/dataのテストファイルを使用）
   * @returns server/dataのテストGRIB2ファイルを使った計算結果
   */
  async calculateProductionSoilRainfallIndex(params?: { initial?: string }): Promise<CalculationResult> {
    console.log('🎭 [モック] サーバーのテストデータで本番環境をエミュレート中...');
    console.log('  指定された初期時刻:', params?.initial || '自動設定');
    console.log('  実際に使用: server/data/Z__C_RJTD_20230602000000_*.bin');

    try {
      // サーバーのテストエンドポイントを呼び出し（日時指定は無視される）
      const response = await axios.get<CalculationResult>(
        `${this.apiBaseUrl}/test-full-soil-rainfall-index`,
        { timeout: 300000 }  // 5分タイムアウト
      );

      console.log('  ✅ サーバーからテストデータを取得完了');

      return response.data;
    } catch (error) {
      console.error('  ❌ サーバーからのテストデータ取得エラー:', error);
      throw new Error('テストデータの取得に失敗しました。サーバーが起動しているか確認してください。');
    }
  }
}

// シングルトンインスタンス
export const mockProductionApi = new MockProductionAPI();

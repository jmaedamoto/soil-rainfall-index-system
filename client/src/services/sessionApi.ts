import axios from 'axios';
import type {
  SessionInfo,
  PrefectureDataResponse,
  RiskAtTimeResponse,
  MeshDetailResponse
} from '../types/api';
import { API_BASE_URL } from '../config/apiConfig';

class SessionAPIClient {
  private apiBaseUrl: string;

  constructor() {
    this.apiBaseUrl = API_BASE_URL;
  }

  /**
   * セッション情報取得
   */
  async getSessionInfo(sessionId: string): Promise<SessionInfo> {
    const response = await axios.get<{ status: string; session: SessionInfo }>(
      `${this.apiBaseUrl}/session/${sessionId}`
    );
    return response.data.session;
  }

  /**
   * 府県データ取得
   */
  async getPrefectureData(sessionId: string, prefectureCode: string): Promise<PrefectureDataResponse> {
    const response = await axios.get<PrefectureDataResponse>(
      `${this.apiBaseUrl}/session/${sessionId}/prefecture/${prefectureCode}`
    );
    return response.data;
  }

  /**
   * 指定時刻の全メッシュリスク値取得
   * @param sessionId セッションID
   * @param ft 予報時刻
   * @param options.includeCoords 座標を含めるか（省略時true、初回のみtrueで2回目以降はfalse推奨）
   */
  async getRiskAtTime(
    sessionId: string,
    ft: number,
    options?: { includeCoords?: boolean }
  ): Promise<RiskAtTimeResponse> {
    const includeCoords = options?.includeCoords ?? true;
    const response = await axios.get<RiskAtTimeResponse>(
      `${this.apiBaseUrl}/session/${sessionId}/risk-at-time`,
      { params: { ft, include_coords: includeCoords } }
    );
    return response.data;
  }

  /**
   * メッシュ詳細データ取得
   */
  async getMeshDetail(sessionId: string, meshCode: string): Promise<MeshDetailResponse> {
    const response = await axios.get<MeshDetailResponse>(
      `${this.apiBaseUrl}/session/${sessionId}/mesh/${meshCode}`
    );
    return response.data;
  }

  /**
   * セッション削除
   */
  async deleteSession(sessionId: string): Promise<void> {
    await axios.delete(`${this.apiBaseUrl}/session/${sessionId}`);
  }

  /**
   * セッション一覧取得（デバッグ用）
   */
  async listSessions(): Promise<SessionInfo[]> {
    const response = await axios.get<{ status: string; sessions: SessionInfo[] }>(
      `${this.apiBaseUrl}/sessions`
    );
    return response.data.sessions;
  }

  /**
   * セッション統計情報取得
   */
  async getSessionStats(): Promise<any> {
    const response = await axios.get<{ status: string; stats: any }>(
      `${this.apiBaseUrl}/sessions/stats`
    );
    return response.data.stats;
  }

  /**
   * 期限切れセッションクリーンアップ
   */
  async cleanupSessions(): Promise<number> {
    const response = await axios.post<{ status: string; deleted_count: number }>(
      `${this.apiBaseUrl}/sessions/cleanup`
    );
    return response.data.deleted_count;
  }

  /**
   * 雨量調整用の雨量データ取得
   */
  async getRainfallData(sessionId: string): Promise<{
    area_rainfall: Record<string, Array<{ ft: number; value: number }>>;
    subdivision_rainfall: Record<string, Array<{ ft: number; value: number }>>;
  }> {
    const response = await axios.get<{
      status: string;
      area_rainfall: Record<string, Array<{ ft: number; value: number }>>;
      subdivision_rainfall: Record<string, Array<{ ft: number; value: number }>>;
    }>(
      `${this.apiBaseUrl}/session/${sessionId}/rainfall-data`
    );
    return {
      area_rainfall: response.data.area_rainfall,
      subdivision_rainfall: response.data.subdivision_rainfall
    };
  }

  /**
   * 雨量調整後の再計算（セッションベース）
   */
  async recalculateWithAdjustedRainfall(
    sessionId: string,
    adjustments: Record<string, Array<{ ft: number; value: number }>>,
    swiInitial: string,
    guidanceInitial: string,
    dataSource: string
  ): Promise<{
    session_id: string;
    adjusted: boolean;
    ft: number;
    mesh_risks: Record<string, number>;
    mesh_coords: Record<string, { lat: number; lon: number }>;
  }> {
    const response = await axios.post<{
      status: string;
      session_id: string;
      adjusted: boolean;
      ft: number;
      mesh_risks: Record<string, number>;
      mesh_coords: Record<string, { lat: number; lon: number }>;
    }>(
      `${this.apiBaseUrl}/session/${sessionId}/recalculate`,
      {
        adjustments,
        swi_initial: swiInitial,
        guidance_initial: guidanceInitial,
        data_source: dataSource
      },
      { timeout: 300000 }
    );
    return {
      session_id: response.data.session_id,
      adjusted: response.data.adjusted,
      ft: response.data.ft,
      mesh_risks: response.data.mesh_risks,
      mesh_coords: response.data.mesh_coords,
    };
  }
}

export const sessionApiClient = new SessionAPIClient();

import axios from 'axios';
import type {
  SessionInfo,
  PrefectureDataResponse,
  RiskAtTimeResponse,
  MeshDetailResponse
} from '../types/api';

// API Base URL
const getApiBaseUrl = () => {
  if (process.env.NODE_ENV === 'production') {
    return '/api';
  }
  return 'http://localhost:5000/api';
};

class SessionAPIClient {
  private apiBaseUrl: string;

  constructor() {
    this.apiBaseUrl = getApiBaseUrl();
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
   */
  async getRiskAtTime(sessionId: string, ft: number): Promise<RiskAtTimeResponse> {
    const response = await axios.get<RiskAtTimeResponse>(
      `${this.apiBaseUrl}/session/${sessionId}/risk-at-time`,
      { params: { ft } }
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
}

export const sessionApiClient = new SessionAPIClient();

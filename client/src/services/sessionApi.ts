import axios from 'axios';
import type {
  SessionInfo,
  PrefectureDataResponse,
  RiskAtTimeResponse,
  MeshDetailResponse,
  RainfallDataResponse,
  RecalculateRequest,
  RecalculateResponse,
} from '../types/session';
import { API_BASE_URL } from '../config/apiConfig';

class SessionAPIClient {
  private apiBaseUrl: string;

  constructor() {
    this.apiBaseUrl = API_BASE_URL;
  }

  private logRequestStart(endpoint: string, detail?: Record<string, unknown>): number {
    const startedAt = performance.now();
    console.info('[sessionApi] request start', {
      endpoint,
      started_at: new Date().toISOString(),
      ...detail,
    });
    return startedAt;
  }

  private logRequestSuccess(endpoint: string, startedAt: number, detail?: Record<string, unknown>) {
    console.info('[sessionApi] request success', {
      endpoint,
      elapsed_ms: Math.round(performance.now() - startedAt),
      completed_at: new Date().toISOString(),
      ...detail,
    });
  }

  private logRequestError(endpoint: string, startedAt: number, error: unknown, detail?: Record<string, unknown>) {
    const axiosError = axios.isAxiosError(error) ? error : null;
    console.error('[sessionApi] request error', {
      endpoint,
      elapsed_ms: Math.round(performance.now() - startedAt),
      completed_at: new Date().toISOString(),
      status: axiosError?.response?.status,
      status_text: axiosError?.response?.statusText,
      response_data: axiosError?.response?.data,
      message: axiosError?.message ?? String(error),
      code: axiosError?.code,
      ...detail,
    });
  }

  /**
   * セッション情報取得
   */
  async getSessionInfo(sessionId: string): Promise<SessionInfo> {
    const endpoint = 'getSessionInfo';
    const startedAt = this.logRequestStart(endpoint, { session_id: sessionId });
    try {
      const response = await axios.get<{ status: string; session: SessionInfo }>(
        `${this.apiBaseUrl}/session/${sessionId}`
      );
      this.logRequestSuccess(endpoint, startedAt, { session_id: sessionId });
      return response.data.session;
    } catch (error) {
      this.logRequestError(endpoint, startedAt, error, { session_id: sessionId });
      throw error;
    }
  }

  /**
   * 府県データ取得
   */
  async getPrefectureData(sessionId: string, prefectureCode: string): Promise<PrefectureDataResponse> {
    const endpoint = 'getPrefectureData';
    const startedAt = this.logRequestStart(endpoint, {
      session_id: sessionId,
      prefecture_code: prefectureCode,
    });
    try {
      const response = await axios.get<PrefectureDataResponse>(
        `${this.apiBaseUrl}/session/${sessionId}/prefecture/${prefectureCode}`
      );
      this.logRequestSuccess(endpoint, startedAt, {
        session_id: sessionId,
        prefecture_code: prefectureCode,
        status: response.data.status,
      });
      return response.data;
    } catch (error) {
      this.logRequestError(endpoint, startedAt, error, {
        session_id: sessionId,
        prefecture_code: prefectureCode,
      });
      throw error;
    }
  }

  /**
   * 指定時刻の全メッシュリスク値取得
   * @param sessionId セッションID
   * @param ft 予報時刻
   * @param options.includeCoords 互換用パラメータ（現在は常に座標付きで返却される）
   */
  async getRiskAtTime(
    sessionId: string,
    ft: number,
    options?: { includeCoords?: boolean }
  ): Promise<RiskAtTimeResponse> {
    const includeCoords = options?.includeCoords ?? true;
    const endpoint = 'getRiskAtTime';
    const startedAt = this.logRequestStart(endpoint, {
      session_id: sessionId,
      ft,
      include_coords: includeCoords,
    });
    try {
      const response = await axios.get<RiskAtTimeResponse>(
        `${this.apiBaseUrl}/session/${sessionId}/risk-at-time`,
        { params: { ft, include_coords: includeCoords } }
      );
      this.logRequestSuccess(endpoint, startedAt, {
        session_id: sessionId,
        ft,
        status: response.data.status,
      });
      return response.data;
    } catch (error) {
      this.logRequestError(endpoint, startedAt, error, {
        session_id: sessionId,
        ft,
        include_coords: includeCoords,
      });
      throw error;
    }
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
  async getRainfallData(sessionId: string): Promise<RainfallDataResponse> {
    const endpoint = 'getRainfallData';
    const startedAt = this.logRequestStart(endpoint, { session_id: sessionId });
    try {
      const response = await axios.get<{
        status: string;
        area_rainfall: RainfallDataResponse['area_rainfall'];
        subdivision_rainfall: RainfallDataResponse['subdivision_rainfall'];
        area_orders?: RainfallDataResponse['area_orders'];
        subdivision_orders?: RainfallDataResponse['subdivision_orders'];
        area_rainfall_24hour?: RainfallDataResponse['area_rainfall_24hour'];
        subdivision_rainfall_24hour?: RainfallDataResponse['subdivision_rainfall_24hour'];
        guidance_type?: RainfallDataResponse['guidance_type'];
        risk_rule?: RainfallDataResponse['risk_rule'];
        input_mode?: RainfallDataResponse['input_mode'];
        adjustment_mode?: RainfallDataResponse['adjustment_mode'];
      }>(
        `${this.apiBaseUrl}/session/${sessionId}/rainfall-data`
      );
      this.logRequestSuccess(endpoint, startedAt, { session_id: sessionId });
      return {
        area_rainfall: response.data.area_rainfall,
        subdivision_rainfall: response.data.subdivision_rainfall,
        area_orders: response.data.area_orders,
        subdivision_orders: response.data.subdivision_orders,
        area_rainfall_24hour: response.data.area_rainfall_24hour,
        subdivision_rainfall_24hour: response.data.subdivision_rainfall_24hour,
        guidance_type: response.data.guidance_type,
        risk_rule: response.data.risk_rule,
        input_mode: response.data.input_mode,
        adjustment_mode: response.data.adjustment_mode
      };
    } catch (error) {
      this.logRequestError(endpoint, startedAt, error, { session_id: sessionId });
      throw error;
    }
  }

  /**
   * 雨量調整後の再計算（セッションベース）
   */
  async recalculateWithAdjustedRainfall(
    sessionId: string,
    adjustments: Record<string, Array<{ ft: number; value: number }>>,
    aggregateAdjustments: RecalculateRequest['aggregate_adjustments'],
    inputMode: RecalculateRequest['input_mode'],
    adjustmentMode: RecalculateRequest['adjustment_mode'],
    swiInitial: string,
    guidanceInitial: string,
    dataSource: string,
    guidanceType?: RecalculateRequest['guidance_type'],
    riskRule?: RecalculateRequest['risk_rule']
  ): Promise<RecalculateResponse> {
    const response = await axios.post<{
      status: string;
      session_id: RecalculateResponse['session_id'];
      adjusted: RecalculateResponse['adjusted'];
      ft: RecalculateResponse['ft'];
      guidance_type?: RecalculateResponse['guidance_type'];
      risk_rule?: RecalculateResponse['risk_rule'];
      mesh_risks: RecalculateResponse['mesh_risks'];
      mesh_coords: RecalculateResponse['mesh_coords'];
    }>(
      `${this.apiBaseUrl}/session/${sessionId}/recalculate`,
      {
        adjustments,
        aggregate_adjustments: aggregateAdjustments,
        input_mode: inputMode,
        adjustment_mode: adjustmentMode,
        swi_initial: swiInitial,
        guidance_initial: guidanceInitial,
        data_source: dataSource,
        guidance_type: guidanceType,
        risk_rule: riskRule
      },
      { timeout: 600000 }
    );
    return {
      session_id: response.data.session_id,
      adjusted: response.data.adjusted,
      ft: response.data.ft,
      guidance_type: response.data.guidance_type,
      risk_rule: response.data.risk_rule,
      mesh_risks: response.data.mesh_risks,
      mesh_coords: response.data.mesh_coords,
    };
  }
}

export const sessionApiClient = new SessionAPIClient();

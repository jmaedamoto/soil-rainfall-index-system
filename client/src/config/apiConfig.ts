/**
 * API設定（一元管理）
 *
 * 本番環境: /dosya/api
 * staging環境: /staging/dosya/api
 * 開発環境: http://localhost:5000
 */

/**
 * APIベースURLを取得
 * - 本番/staging環境: Viteのベースパス + 'api' (例: /dosya/api, /staging/dosya/api)
 * - 開発環境: localhost:5000
 */
export const getApiBaseUrl = (): string => {
  // 本番環境判定
  const isProduction = import.meta.env.PROD;

  if (isProduction) {
    // Viteのベースパス（/dosya/ など）からAPIパスを構築
    const basePath = import.meta.env.BASE_URL || '/';
    return `${basePath.replace(/\/$/, '')}/api`;
  }

  // 開発環境: localhost（サーバー側で/apiプレフィックスなし）
  return 'http://localhost:5000';
};

/**
 * APIベースURL（シングルトン）
 */
export const API_BASE_URL = getApiBaseUrl();

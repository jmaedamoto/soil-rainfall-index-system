/**
 * API設定（一元管理）
 *
 * staging環境: /staging/dosya/api
 * 開発環境: http://localhost:5000
 */

/**
 * APIベースURLを取得
 * - staging環境: Viteのベースパス + 'api' (例: /staging/dosya/api)
 * - 開発環境: localhost:5000
 */
export const getApiBaseUrl = (): string => {
  // 本番環境判定
  const isProduction = import.meta.env.PROD;

  if (isProduction) {
    // staging環境: Viteのベースパス（/staging/dosya/）からAPIパスを構築
    const basePath = import.meta.env.BASE_URL || '/';
    // /staging/dosya/ -> /staging/dosya/api
    return `${basePath.replace(/\/$/, '')}/api`;
  }

  // 開発環境: localhost（サーバー側で/apiプレフィックスなし）
  return 'http://localhost:5000';
};

/**
 * APIベースURL（シングルトン）
 */
export const API_BASE_URL = getApiBaseUrl();

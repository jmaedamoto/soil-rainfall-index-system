import React from 'react';
import { CacheInfo as CacheInfoType } from '../types/api';

interface CacheInfoProps {
  cacheInfo: CacheInfoType;
}

const CacheInfo: React.FC<CacheInfoProps> = ({ cacheInfo }) => {
  const {
    cache_hit,
    cache_metadata,
    served_from_existing_session,
    served_after_cache_wait,
    waited_for_calculation,
    cache_materializing,
  } = cacheInfo;

  const statusLabel = cache_hit
    ? 'ファイルキャッシュヒット'
    : served_from_existing_session
      ? '既存セッション再利用'
      : served_after_cache_wait
        ? 'キャッシュ確定待機後に取得'
        : waited_for_calculation
          ? '他ユーザーの計算完了待ち'
          : 'キャッシュミス（新規計算）';

  const statusColor = cache_hit
    ? '#4CAF50'
    : (served_from_existing_session || served_after_cache_wait || waited_for_calculation)
      ? '#1976D2'
      : '#FF9800';

  const statusIcon = cache_hit
    ? '✅'
    : (served_from_existing_session || served_after_cache_wait || waited_for_calculation)
      ? 'ℹ️'
      : '🔄';

  return (
    <div
      style={{
        position: 'fixed',
        top: '80px',
        right: '20px',
        backgroundColor: 'white',
        border: '2px solid #2196F3',
        borderRadius: '8px',
        padding: '16px',
        boxShadow: '0 4px 8px rgba(0,0,0,0.1)',
        zIndex: 1000,
        minWidth: '280px',
        fontSize: '14px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          marginBottom: '12px',
          paddingBottom: '12px',
          borderBottom: '1px solid #e0e0e0',
        }}
      >
        <span
          style={{
            fontSize: '18px',
            marginRight: '8px',
          }}
        >
          💾
        </span>
        <span
          style={{
            fontWeight: 'bold',
            fontSize: '16px',
            color: '#333',
          }}
        >
          キャッシュ情報
        </span>
      </div>

      {/* キャッシュヒット状態 */}
      <div style={{ marginBottom: '12px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span
            style={{
              fontSize: '20px',
            }}
          >
            {statusIcon}
          </span>
          <span
            style={{
              fontWeight: 'bold',
              color: statusColor,
            }}
          >
            {statusLabel}
          </span>
        </div>
        {cache_materializing && (
          <div style={{ marginTop: '6px', fontSize: '12px', color: '#666' }}>
            キャッシュ保存の完了待ち中
          </div>
        )}
      </div>

      {/* キャッシュキー */}
      <div style={{ marginBottom: '8px' }}>
        <div
          style={{
            fontSize: '12px',
            color: '#666',
            marginBottom: '4px',
          }}
        >
          キャッシュキー:
        </div>
        <div
          style={{
            fontSize: '11px',
            fontFamily: 'monospace',
            backgroundColor: '#f5f5f5',
            padding: '6px',
            borderRadius: '4px',
            wordBreak: 'break-all',
            color: '#333',
          }}
        >
          {cacheInfo.cache_key}
        </div>
      </div>

      {/* メタデータ（キャッシュヒット時のみ） */}
      {cache_hit && cache_metadata && (
        <>
          <div
            style={{
              marginTop: '12px',
              paddingTop: '12px',
              borderTop: '1px solid #e0e0e0',
            }}
          >
            <div style={{ marginBottom: '6px' }}>
              <span style={{ color: '#666', fontSize: '12px' }}>
                ファイルサイズ:
              </span>
              <span
                style={{
                  marginLeft: '8px',
                  fontWeight: 'bold',
                  color: '#2196F3',
                }}
              >
                {cache_metadata.file_size_mb.toFixed(2)} MB
              </span>
            </div>

            <div style={{ marginBottom: '6px' }}>
              <span style={{ color: '#666', fontSize: '12px' }}>
                メッシュ数:
              </span>
              <span
                style={{
                  marginLeft: '8px',
                  fontWeight: 'bold',
                  color: '#2196F3',
                }}
              >
                {cache_metadata.mesh_count.toLocaleString()}
              </span>
            </div>

            <div style={{ marginBottom: '6px' }}>
              <span style={{ color: '#666', fontSize: '12px' }}>圧縮:</span>
              <span
                style={{
                  marginLeft: '8px',
                  fontWeight: 'bold',
                  color: cache_metadata.compressed ? '#4CAF50' : '#666',
                }}
              >
                {cache_metadata.compressed
                  ? `${cache_metadata.compression_format} 圧縮済み`
                  : '非圧縮'}
              </span>
            </div>

            <div style={{ marginBottom: '6px' }}>
              <span style={{ color: '#666', fontSize: '12px' }}>
                作成日時:
              </span>
              <span
                style={{
                  marginLeft: '8px',
                  fontSize: '11px',
                  color: '#666',
                }}
              >
                {new Date(cache_metadata.created_at).toLocaleString('ja-JP')}
              </span>
            </div>
          </div>
        </>
      )}

      {/* パフォーマンス情報（キャッシュヒット時） */}
      {(cache_hit || served_from_existing_session || served_after_cache_wait || waited_for_calculation) && (
        <div
          style={{
            marginTop: '12px',
            paddingTop: '12px',
            borderTop: '1px solid #e0e0e0',
            backgroundColor: cache_hit ? '#E8F5E9' : '#E3F2FD',
            padding: '8px',
            borderRadius: '4px',
          }}
        >
          <div
            style={{
              fontSize: '12px',
              color: cache_hit ? '#2E7D32' : '#1565C0',
              textAlign: 'center',
              fontWeight: 'bold',
            }}
          >
            {cache_hit ? '⚡ 高速レスポンス（ファイルキャッシュ利用）' : '↺ 再計算を避けて応答'}
          </div>
        </div>
      )}
    </div>
  );
};

export default CacheInfo;

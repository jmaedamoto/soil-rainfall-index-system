import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import { LatLngBounds } from 'leaflet';
import { Mesh, RISK_COLORS, RiskLevel, TimeSeriesPoint } from '../../types/api';
import MapLegend from './MapLegend';
import SimpleCanvasLayer from './SimpleCanvasLayer';
import './LeafletIcons'; // アイコン修正をインポート
import 'leaflet/dist/leaflet.css';

// Canvas描画に移行したため、MemoizedRectangleは不要

interface SoilRainfallMapProps {
  meshes: Mesh[];
  selectedTime: number; // 選択された時刻（ft値）
  selectedPrefecture?: string; // 選択された都道府県
  prefectureData?: { [prefCode: string]: { areas: { meshes: Mesh[] }[] } }; // 都道府県データ
  onMeshClick?: (mesh: Mesh) => void;
  isLoading?: boolean; // ローディング状態
  swiInitialTime?: string; // SWI初期時刻（ISO8601形式）
  guidanceInitialTime?: string; // ガイダンス初期時刻（ISO8601形式）
}

const SoilRainfallMap: React.FC<SoilRainfallMapProps> = React.memo(({
  meshes,
  selectedTime,
  selectedPrefecture,
  prefectureData,
  onMeshClick,
  isLoading = false,
  swiInitialTime,
  guidanceInitialTime
}) => {
  const [bounds, setBounds] = useState<LatLngBounds | null>(null);
  const [showLandCondition, setShowLandCondition] = useState(false);
  const [showStandard, setShowStandard] = useState(false);
  const [showRelief, setShowRelief] = useState(false);
  const [showSlope, setShowSlope] = useState(false);
  const [showFlood, setShowFlood] = useState(false);

  // メッシュから都道府県のマッピングを作成（prefectureDataを使用）
  const meshToPrefecture = useMemo(() => {
    const mapping: { [meshCode: string]: string } = {};
    
    if (!prefectureData) return mapping;
    
    // prefectureDataから正確なメッシュと都道府県の対応を取得
    Object.entries(prefectureData).forEach(([prefCode, prefData]) => {
      prefData.areas.forEach(area => {
        area.meshes.forEach(mesh => {
          mapping[mesh.code] = prefCode;
        });
      });
    });
    
    return mapping;
  }, [prefectureData]);

  // メッシュコードから都道府県を判定する関数
  const getPrefectureFromMesh = (meshCode: string): string => {
    return meshToPrefecture[meshCode] || 'unknown';
  };


  // 関西地方の初期表示範囲
  const kansaiCenter: [number, number] = [34.7, 135.5];
  const defaultZoom = 8;

  // メッシュデータから地図の境界を計算
  useEffect(() => {
    if (meshes.length > 0) {
      const lats = meshes.map(m => m.lat);
      const lons = meshes.map(m => m.lon);
      const minLat = Math.min(...lats);
      const maxLat = Math.max(...lats);
      const minLon = Math.min(...lons);
      const maxLon = Math.max(...lons);
      
      const mapBounds = new LatLngBounds(
        [minLat, minLon],
        [maxLat, maxLon]
      );
      setBounds(mapBounds);
    }
  }, [meshes]);

  // メッシュ間隔を動的に計算
  const meshIntervals = useMemo(() => {
    if (meshes.length < 2) return { latInterval: 0.008, lonInterval: 0.008 };

    const lats = meshes.map(m => m.lat);
    const lons = meshes.map(m => m.lon);
    
    const sortedLats = [...new Set(lats)].sort((a, b) => a - b);
    const sortedLons = [...new Set(lons)].sort((a, b) => a - b);
    
    let latInterval = 0.008;  // デフォルト値
    let lonInterval = 0.008;  // デフォルト値
    
    if (sortedLats.length > 1) {
      const latDiffs = [];
      for (let i = 1; i < sortedLats.length; i++) {
        const diff = sortedLats[i] - sortedLats[i-1];
        if (diff > 0.0001) { // 非常に小さい差を除外
          latDiffs.push(diff);
        }
      }
      if (latDiffs.length > 0) {
        // 最頻値を計算（最も一般的な間隔）
        const diffCounts = latDiffs.reduce((acc, diff) => {
          const rounded = Math.round(diff * 1000000) / 1000000; // 小数点以下6桁で丸め
          acc[rounded] = (acc[rounded] || 0) + 1;
          return acc;
        }, {} as Record<number, number>);
        
        const mostCommonDiff = Object.keys(diffCounts).reduce((a, b) => 
          diffCounts[Number(a)] > diffCounts[Number(b)] ? a : b
        );
        latInterval = Number(mostCommonDiff);
      }
    }
    
    if (sortedLons.length > 1) {
      const lonDiffs = [];
      for (let i = 1; i < sortedLons.length; i++) {
        const diff = sortedLons[i] - sortedLons[i-1];
        if (diff > 0.0001) { // 非常に小さい差を除外
          lonDiffs.push(diff);
        }
      }
      if (lonDiffs.length > 0) {
        // 最頻値を計算（最も一般的な間隔）
        const diffCounts = lonDiffs.reduce((acc, diff) => {
          const rounded = Math.round(diff * 1000000) / 1000000; // 小数点以下6桁で丸め
          acc[rounded] = (acc[rounded] || 0) + 1;
          return acc;
        }, {} as Record<number, number>);
        
        const mostCommonDiff = Object.keys(diffCounts).reduce((a, b) => 
          diffCounts[Number(a)] > diffCounts[Number(b)] ? a : b
        );
        lonInterval = Number(mostCommonDiff);
      }
    }
    
    return { latInterval, lonInterval };
  }, [meshes]);

  // 全メッシュを常に表示（フィルタリングを無効化）
  const filteredMeshes = useMemo(() => {
    return meshes;  // 常に全メッシュを返す
  }, [meshes]);

  // 時刻インデックスマップを事前作成（最適化）
  const timeIndexMap = useMemo(() => {
    const map = new Map<string, number>();
    if (meshes.length > 0) {
      // 最初のメッシュの時系列から時刻インデックスを作成
      meshes[0].swi_timeline.forEach((point, index) => {
        map.set(`${point.ft}`, index);
      });
    }
    return map;
  }, [meshes]);

  // Canvas描画では個別計算はCanvasGridLayer内で実行

  // 日時フォーマット関数（JST表示）
  const formatDateTime = (isoString?: string) => {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    const jstDate = new Date(date.getTime() + 9 * 60 * 60 * 1000);
    return `${jstDate.getUTCFullYear()}/${jstDate.getUTCMonth() + 1}/${jstDate.getUTCDate()} ${String(jstDate.getUTCHours()).padStart(2, '0')}:${String(jstDate.getUTCMinutes()).padStart(2, '0')}`;
  };

  // 現在選択されている時刻を計算
  const getCurrentTime = () => {
    if (!swiInitialTime) return 'N/A';
    const swiDate = new Date(swiInitialTime);
    const jstDate = new Date(swiDate.getTime() + 9 * 60 * 60 * 1000);
    const currentDate = new Date(jstDate.getTime() + selectedTime * 60 * 60 * 1000);
    return `${currentDate.getUTCFullYear()}/${currentDate.getUTCMonth() + 1}/${currentDate.getUTCDate()} ${String(currentDate.getUTCHours()).padStart(2, '0')}:${String(currentDate.getUTCMinutes()).padStart(2, '0')}`;
  };

  return (
    <div style={{ height: '600px', width: '100%', position: 'relative' }}>
      {/* 時刻情報表示（地図の左上） */}
      {(swiInitialTime || guidanceInitialTime) && (
        <div style={{
          position: 'absolute',
          top: '10px',
          left: '10px',
          zIndex: 1000,
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          padding: '12px 16px',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
          fontSize: '13px',
          lineHeight: '1.6',
          fontFamily: 'monospace',
          border: '2px solid #1976D2'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#1976D2', fontSize: '14px' }}>
            📅 時刻情報
          </div>
          <div style={{ marginBottom: '4px' }}>
            <span style={{ color: '#666', fontWeight: 'bold' }}>SWI初期時刻:</span>{' '}
            <span style={{ color: '#000' }}>{formatDateTime(swiInitialTime)}</span>
          </div>
          <div style={{ marginBottom: '4px' }}>
            <span style={{ color: '#666', fontWeight: 'bold' }}>ガイダンス初期時刻:</span>{' '}
            <span style={{ color: '#000' }}>{formatDateTime(guidanceInitialTime)}</span>
          </div>
          <div style={{
            marginTop: '8px',
            paddingTop: '8px',
            borderTop: '1px solid #ddd'
          }}>
            <span style={{ color: '#666', fontWeight: 'bold' }}>現在表示時刻:</span>{' '}
            <span style={{ color: '#D32F2F', fontWeight: 'bold' }}>{getCurrentTime()}</span>
            <span style={{ color: '#666', marginLeft: '8px' }}>(FT+{selectedTime}h)</span>
          </div>
        </div>
      )}

      <MapContainer
        center={kansaiCenter}
        zoom={defaultZoom}
        style={{ height: '100%', width: '100%' }}
        bounds={bounds || undefined}
        keyboard={false}
        minZoom={6}
        maxZoom={14}
      >
        {/* 純白地図ベース */}
        <TileLayer
          url="https://cyberjapandata.gsi.go.jp/xyz/blank/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>'
        />
        
        {/* 県境・海岸線のみ表示 */}
        <TileLayer
          url="https://cyberjapandata.gsi.go.jp/xyz/boundary01/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>'
          opacity={0.8}
        />

        {/* Canvas描画によるメッシュ表示（高速化・安定版） */}
        <SimpleCanvasLayer
          meshes={meshes}
          selectedTime={selectedTime}
          meshIntervals={meshIntervals}
          onMeshClick={onMeshClick}
        />

        {/* 土地条件図レイヤー */}
        {showLandCondition && (
          <TileLayer
            url="https://cyberjapandata.gsi.go.jp/xyz/lcmfc2/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>'
            opacity={0.6}
            zIndex={600}
          />
        )}

        {/* 標準地図レイヤー */}
        {showStandard && (
          <TileLayer
            url="https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>'
            opacity={0.5}
            zIndex={500}
          />
        )}

        {/* 色別標高図レイヤー */}
        {showRelief && (
          <TileLayer
            url="https://cyberjapandata.gsi.go.jp/xyz/relief/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>'
            opacity={0.6}
            zIndex={400}
          />
        )}

        {/* 傾斜量図レイヤー */}
        {showSlope && (
          <TileLayer
            url="https://cyberjapandata.gsi.go.jp/xyz/slopemap/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>'
            opacity={0.6}
            zIndex={450}
          />
        )}

        {/* 洪水浸水想定区域レイヤー */}
        {showFlood && (
          <TileLayer
            url="https://disaportaldata.gsi.go.jp/raster/01_flood_l2_shinsuishin_data/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://disaportal.gsi.go.jp/">ハザードマップポータルサイト</a>'
            opacity={0.6}
            zIndex={550}
          />
        )}

      </MapContainer>

      {/* レイヤー切り替えコントロール */}
      <div style={{
        position: 'absolute',
        top: '10px',
        right: '10px',
        backgroundColor: 'white',
        padding: '12px',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '14px' }}>
          <input
            type="checkbox"
            checked={showLandCondition}
            onChange={(e) => setShowLandCondition(e.target.checked)}
            style={{ marginRight: '8px', cursor: 'pointer' }}
          />
          土地条件図
        </label>
        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '14px' }}>
          <input
            type="checkbox"
            checked={showStandard}
            onChange={(e) => setShowStandard(e.target.checked)}
            style={{ marginRight: '8px', cursor: 'pointer' }}
          />
          標準地図
        </label>
        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '14px' }}>
          <input
            type="checkbox"
            checked={showRelief}
            onChange={(e) => setShowRelief(e.target.checked)}
            style={{ marginRight: '8px', cursor: 'pointer' }}
          />
          色別標高図
        </label>
        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '14px' }}>
          <input
            type="checkbox"
            checked={showSlope}
            onChange={(e) => setShowSlope(e.target.checked)}
            style={{ marginRight: '8px', cursor: 'pointer' }}
          />
          傾斜量図
        </label>
        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '14px' }}>
          <input
            type="checkbox"
            checked={showFlood}
            onChange={(e) => setShowFlood(e.target.checked)}
            style={{ marginRight: '8px', cursor: 'pointer' }}
          />
          洪水浸水想定区域
        </label>
      </div>

      {/* 凡例を地図の右下に表示 */}
      <MapLegend position="bottom-right" />
      
      {/* ローディングオーバーレイ */}
      {isLoading && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
          borderRadius: '8px'
        }}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '15px',
            padding: '20px',
            backgroundColor: 'white',
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            border: '1px solid #ddd'
          }}>
            {/* スピナーアニメーション */}
            <div style={{
              width: '40px',
              height: '40px',
              border: '4px solid #f3f3f3',
              borderTop: '4px solid #1976D2',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }} />
            
            {/* ローディングメッセージ */}
            <div style={{
              fontSize: '16px',
              fontWeight: 'bold',
              color: '#333',
              textAlign: 'center'
            }}>
              時刻データを更新中...
            </div>
          </div>
          
          {/* CSS アニメーション */}
          <style>
            {`
              @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
              }
            `}
          </style>
        </div>
      )}
    </div>
  );
});

export default SoilRainfallMap;
import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Rectangle, Popup } from 'react-leaflet';
import { LatLngBounds } from 'leaflet';
import { Mesh, RISK_COLORS, RiskLevel, TimeSeriesPoint } from '../../types/api';
import MapLegend from './MapLegend';
import './LeafletIcons'; // アイコン修正をインポート
import 'leaflet/dist/leaflet.css';

interface SoilRainfallMapProps {
  meshes: Mesh[];
  selectedTime: number; // 選択された時刻（ft値）
  selectedPrefecture?: string; // 選択された都道府県
  prefectureData?: { [prefCode: string]: { areas: { meshes: Mesh[] }[] } }; // 都道府県データ
  onMeshClick?: (mesh: Mesh) => void;
  isLoading?: boolean; // ローディング状態
}

const SoilRainfallMap: React.FC<SoilRainfallMapProps> = React.memo(({
  meshes,
  selectedTime,
  selectedPrefecture,
  prefectureData,
  onMeshClick,
  isLoading = false
}) => {
  const [bounds, setBounds] = useState<LatLngBounds | null>(null);

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

  // 選択都道府県のメッシュのみをフィルタリング（最適化）
  const filteredMeshes = useMemo(() => {
    if (!selectedPrefecture) return meshes;
    
    const selectedMeshes: Mesh[] = [];
    for (const mesh of meshes) {
      if (meshToPrefecture[mesh.code] === selectedPrefecture) {
        selectedMeshes.push(mesh);
      }
    }
    return selectedMeshes;
  }, [meshes, meshToPrefecture, selectedPrefecture]);

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

  // 各メッシュの表示データを計算（最適化版）
  const meshDisplayData = useMemo(() => {
    const displayMeshes = selectedPrefecture ? filteredMeshes : meshes;
    const timeIndex = timeIndexMap.get(`${selectedTime}`);
    
    return displayMeshes.map(mesh => {
      // 時刻インデックスを使用して高速アクセス
      const swiValue = timeIndex !== undefined && mesh.swi_timeline[timeIndex] 
        ? mesh.swi_timeline[timeIndex].value 
        : 0;

      // リスクレベルを判定
      let riskLevel = RiskLevel.NORMAL;
      if (swiValue >= mesh.dosyakei_bound) {
        riskLevel = RiskLevel.DISASTER;
      } else if (swiValue >= mesh.warning_bound) {
        riskLevel = RiskLevel.WARNING;
      } else if (swiValue >= mesh.advisary_bound) {
        riskLevel = RiskLevel.CAUTION;
      }


      // 実際のメッシュ間隔に基づいて格子サイズを計算
      const latHalfSize = meshIntervals.latInterval / 2;
      const lonHalfSize = meshIntervals.lonInterval / 2;
      
      // 格子の境界を計算（メッシュ中心を基準に四方に拡張）
      const bounds: [[number, number], [number, number]] = [
        [mesh.lat - latHalfSize, mesh.lon - lonHalfSize], // 南西角
        [mesh.lat + latHalfSize, mesh.lon + lonHalfSize]  // 北東角
      ];


      return {
        mesh,
        swiValue,
        riskLevel,
        bounds,
        color: RISK_COLORS[riskLevel]
      };
    }).filter(item => item !== null); // nullを除外
  }, [filteredMeshes, meshes, selectedTime, meshIntervals, selectedPrefecture, timeIndexMap]);

  return (
    <div style={{ height: '600px', width: '100%', position: 'relative' }}>
      <MapContainer
        center={kansaiCenter}
        zoom={defaultZoom}
        style={{ height: '100%', width: '100%' }}
        bounds={bounds || undefined}
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
        
        {meshDisplayData.map(({ mesh, swiValue, riskLevel, bounds, color }) => {
          // 都道府県が選択されている場合、表示されるのは選択都道府県のメッシュのみ
          const isSelectedPrefecture = selectedPrefecture ? true : false;
          
          return (
          <Rectangle
            key={mesh.code}
            bounds={bounds}
            pathOptions={{
              color: isSelectedPrefecture ? '#ff6b35' : 'rgba(255, 255, 255, 0.2)',
              fillColor: color,
              fillOpacity: isSelectedPrefecture ? 0.9 : 0.4,
              weight: isSelectedPrefecture ? 1 : 0.1,
              opacity: isSelectedPrefecture ? 1 : 0.6
            }}
            eventHandlers={{
              click: () => onMeshClick?.(mesh)
            }}
          >
            <Popup>
              <div style={{ minWidth: '200px' }}>
                <h4>メッシュ詳細</h4>
                <p><strong>コード:</strong> {mesh.code}</p>
                <p><strong>緯度:</strong> {mesh.lat.toFixed(4)}</p>
                <p><strong>経度:</strong> {mesh.lon.toFixed(4)}</p>
                <p><strong>時刻 FT{selectedTime}の土壌雨量指数:</strong> {swiValue.toFixed(1)}</p>
                <p><strong>リスクレベル:</strong> 
                  <span style={{ 
                    color: color, 
                    fontWeight: 'bold',
                    marginLeft: '5px'
                  }}>
                    {riskLevel === RiskLevel.NORMAL && '正常'}
                    {riskLevel === RiskLevel.CAUTION && '注意'}
                    {riskLevel === RiskLevel.WARNING && '警報'}
                    {riskLevel === RiskLevel.DISASTER && '土砂災害'}
                  </span>
                </p>
                <hr />
                <p><strong>基準値:</strong></p>
                <p>注意報: {mesh.advisary_bound}</p>
                <p>警報: {mesh.warning_bound}</p>
                <p>土砂災害: {mesh.dosyakei_bound}</p>
              </div>
            </Popup>
          </Rectangle>
          );
        })}

      </MapContainer>
      
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
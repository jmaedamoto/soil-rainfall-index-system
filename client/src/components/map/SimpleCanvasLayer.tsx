import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { useMap } from 'react-leaflet';
import { Mesh, RISK_COLORS, RiskLevel } from '../../types/api';

interface SimpleCanvasLayerProps {
  meshes: Mesh[];
  selectedTime: number;
  meshIntervals: { latInterval: number; lonInterval: number };
  onMeshClick?: (mesh: Mesh) => void;
}

const SimpleCanvasLayer: React.FC<SimpleCanvasLayerProps> = ({
  meshes,
  selectedTime,
  meshIntervals,
  onMeshClick
}) => {
  const map = useMap();
  const layerRef = useRef<L.Renderer | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const drawFunctionRef = useRef<(() => void) | null>(null);

  // 最新の値を参照するためのref
  const propsRef = useRef({ meshes, selectedTime, meshIntervals });

  // propsRefを常に最新の値で更新
  useEffect(() => {
    propsRef.current = { meshes, selectedTime, meshIntervals };
  });

  useEffect(() => {
    if (!map) return;

    // Leaflet標準のCanvas Rendererを使用
    const canvasRenderer = L.canvas({ padding: 0.5 });

    // レイヤーグループを作成
    const meshLayerGroup = L.layerGroup();

    const drawMeshes = () => {
      const { meshes: currentMeshes, selectedTime: currentSelectedTime, meshIntervals: currentMeshIntervals } = propsRef.current;

      // 既存のレイヤーをクリア
      meshLayerGroup.clearLayers();

      // 時刻インデックス取得
      let timeIndex = 0;
      if (currentMeshes.length > 0) {
        timeIndex = currentMeshes[0].swi_timeline.findIndex(point => point.ft === currentSelectedTime);
        if (timeIndex === -1) timeIndex = 0;
      }

      const latHalfSize = currentMeshIntervals.latInterval / 2;
      const lonHalfSize = currentMeshIntervals.lonInterval / 2;

      currentMeshes.forEach(mesh => {
        // SWI値とリスクレベル計算
        const swiValue = mesh.swi_timeline[timeIndex]?.value || 0;

        let riskLevel = RiskLevel.NORMAL;
        if (swiValue >= mesh.dosyakei_bound) {
          riskLevel = RiskLevel.DISASTER;
        } else if (swiValue >= mesh.warning_bound) {
          riskLevel = RiskLevel.WARNING;
        } else if (swiValue >= mesh.advisary_bound) {
          riskLevel = RiskLevel.CAUTION;
        }

        // 危険度0は描画しない
        if (riskLevel === RiskLevel.NORMAL) return;

        // メッシュ矩形を作成
        const bounds = L.latLngBounds(
          [mesh.lat - latHalfSize, mesh.lon - lonHalfSize],
          [mesh.lat + latHalfSize, mesh.lon + lonHalfSize]
        );

        const rectangle = L.rectangle(bounds, {
          color: RISK_COLORS[riskLevel],
          fillColor: RISK_COLORS[riskLevel],
          fillOpacity: 0.7,
          weight: 0.5,
          opacity: 0.8,
          renderer: canvasRenderer
        });

        if (onMeshClick) {
          rectangle.on('click', () => onMeshClick(mesh));
        }

        meshLayerGroup.addLayer(rectangle);
      });
    };

    // 初回描画
    drawMeshes();

    // レイヤーをマップに追加
    meshLayerGroup.addTo(map);
    layerRef.current = canvasRenderer;
    layerGroupRef.current = meshLayerGroup;
    drawFunctionRef.current = drawMeshes;

    // マップイベントのリスニング
    const handleViewChange = () => {
      // ビュー変更時は再描画不要（Leafletが自動処理）
    };

    map.on('zoomend', handleViewChange);
    map.on('moveend', handleViewChange);

    return () => {
      if (layerGroupRef.current) {
        map.removeLayer(layerGroupRef.current);
        layerGroupRef.current = null;
      }
      layerRef.current = null;
      drawFunctionRef.current = null;
      map.off('zoomend', handleViewChange);
      map.off('moveend', handleViewChange);
    };
  }, [map, onMeshClick]);

  // データ更新時の再描画
  useEffect(() => {
    console.log('Data changed - redrawing meshes. selectedTime:', selectedTime, 'meshes count:', meshes.length);

    if (drawFunctionRef.current) {
      drawFunctionRef.current();
    }
  }, [selectedTime, meshes, meshIntervals]);

  return null;
};

export default SimpleCanvasLayer;
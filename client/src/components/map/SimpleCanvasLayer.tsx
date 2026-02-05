import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { useMap } from 'react-leaflet';
import { Mesh, RISK_COLORS, RiskLevel } from '../../types/api';

interface SimpleCanvasLayerProps {
  meshes?: Mesh[]; // 通常モード: 全メッシュデータ
  meshRisks?: Record<string, number>; // セッションモード: メッシュコード→リスク値
  meshCoords?: Record<string, { lat: number; lon: number }>; // セッションモード: メッシュ座標
  selectedTime: number;
  meshIntervals: { latInterval: number; lonInterval: number };
  onMeshClick?: (mesh: Mesh) => void;
}

const SimpleCanvasLayer: React.FC<SimpleCanvasLayerProps> = ({
  meshes,
  meshRisks,
  meshCoords,
  selectedTime,
  meshIntervals,
  onMeshClick
}) => {
  const map = useMap();
  const layerRef = useRef<L.Renderer | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const drawFunctionRef = useRef<(() => void) | null>(null);

  // 最新の値を参照するためのref
  const propsRef = useRef({ meshes, meshRisks, meshCoords, selectedTime, meshIntervals });

  // propsRefを常に最新の値で更新
  useEffect(() => {
    propsRef.current = { meshes, meshRisks, meshCoords, selectedTime, meshIntervals };
  });

  useEffect(() => {
    if (!map) return;

    // Leaflet標準のCanvas Rendererを使用
    // padding: 画面外のオブジェクトも描画する範囲（0.5 = 画面の50%分余分に描画）
    // tolerance: ピクセル許容誤差（低ズームレベルでも確実に描画）
    const canvasRenderer = L.canvas({
      padding: 1.0,  // 画面外も多めに描画
      tolerance: 0    // ピクセル許容誤差を0にして確実に描画
    });

    // レイヤーグループを作成
    const meshLayerGroup = L.layerGroup();

    const drawMeshes = () => {
      const {
        meshes: currentMeshes,
        meshRisks: currentMeshRisks,
        meshCoords: currentMeshCoords,
        selectedTime: currentSelectedTime,
        meshIntervals: currentMeshIntervals
      } = propsRef.current;

      // 既存のレイヤーをクリア
      meshLayerGroup.clearLayers();

      const latHalfSize = currentMeshIntervals.latInterval / 2;
      const lonHalfSize = currentMeshIntervals.lonInterval / 2;

      // セッションモード: meshRisks + meshCoordsを使用
      if (currentMeshRisks && currentMeshCoords) {
        console.log(`[SimpleCanvasLayer.drawMeshes] セッションモード - meshRisks: ${Object.keys(currentMeshRisks).length}, meshCoords: ${Object.keys(currentMeshCoords).length}`);

        let drawnCount = 0;
        let skippedNormalCount = 0;
        let skippedNoCoordCount = 0;

        Object.entries(currentMeshRisks).forEach(([meshCode, riskValue]) => {
          // 危険度0は描画しない
          if (riskValue === RiskLevel.NORMAL) {
            skippedNormalCount++;
            return;
          }

          const coords = currentMeshCoords[meshCode];
          if (!coords) {
            skippedNoCoordCount++;
            return;
          }

          // メッシュ矩形を作成
          const bounds = L.latLngBounds(
            [coords.lat - latHalfSize, coords.lon - lonHalfSize],
            [coords.lat + latHalfSize, coords.lon + lonHalfSize]
          );

          const rectangle = L.rectangle(bounds, {
            color: RISK_COLORS[riskValue as keyof typeof RISK_COLORS],
            fillColor: RISK_COLORS[riskValue as keyof typeof RISK_COLORS],
            fillOpacity: 0.7,
            weight: 0,
            renderer: canvasRenderer
          });

          meshLayerGroup.addLayer(rectangle);
          drawnCount++;
        });

        console.log(`[SimpleCanvasLayer.drawMeshes] 描画完了 - 描画: ${drawnCount}, スキップ(通常): ${skippedNormalCount}, スキップ(座標なし): ${skippedNoCoordCount}`);
      }
      // 通常モード: meshesを使用
      else if (currentMeshes && currentMeshes.length > 0) {
        // 時刻インデックス取得
        let timeIndex = 0;
        timeIndex = currentMeshes[0].swi_timeline.findIndex(point => point.ft === currentSelectedTime);
        if (timeIndex === -1) timeIndex = 0;

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
            color: RISK_COLORS[riskLevel as keyof typeof RISK_COLORS],
            fillColor: RISK_COLORS[riskLevel as keyof typeof RISK_COLORS],
            fillOpacity: 0.7,
            weight: 0,
            renderer: canvasRenderer
          });

          if (onMeshClick) {
            rectangle.on('click', () => onMeshClick(mesh));
          }

          meshLayerGroup.addLayer(rectangle);
        });
      }
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
    console.log(`[SimpleCanvasLayer] 再描画トリガー - selectedTime: ${selectedTime}, meshRisks数: ${meshRisks ? Object.keys(meshRisks).length : 0}, meshes数: ${meshes?.length || 0}`);

    if (drawFunctionRef.current) {
      console.log(`[SimpleCanvasLayer] drawMeshes実行`);
      drawFunctionRef.current();
      console.log(`[SimpleCanvasLayer] 描画完了`);
    } else {
      console.warn(`[SimpleCanvasLayer] drawFunctionRefが未初期化`);
    }
  }, [selectedTime, meshes, meshRisks, meshCoords, meshIntervals]);

  return null;
};

export default SimpleCanvasLayer;
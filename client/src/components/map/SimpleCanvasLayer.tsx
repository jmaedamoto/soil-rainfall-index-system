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
  onMeshSelect?: (mesh: { code: string; lat: number; lon: number }) => void;
}

const SimpleCanvasLayer: React.FC<SimpleCanvasLayerProps> = ({
  meshes,
  meshRisks,
  meshCoords,
  selectedTime,
  meshIntervals,
  onMeshClick,
  onMeshSelect
}) => {
  const map = useMap();
  const layerRef = useRef<L.Renderer | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const drawFunctionRef = useRef<(() => void) | null>(null);

  // 最新の値を参照するためのref
  const propsRef = useRef({ meshes, meshRisks, meshCoords, selectedTime, meshIntervals, onMeshSelect });

  // propsRefを常に最新の値で更新
  useEffect(() => {
    propsRef.current = { meshes, meshRisks, meshCoords, selectedTime, meshIntervals, onMeshSelect };
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
        timeIndex = currentMeshes[0].risk_3hour_max_timeline.findIndex(point => point.ft === currentSelectedTime);
        if (timeIndex === -1) timeIndex = 0;

        currentMeshes.forEach(mesh => {
          const riskLevel = mesh.risk_3hour_max_timeline[timeIndex]?.value || RiskLevel.NORMAL;

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

    // Map clicks are used instead of per-cell hit layers so normal-risk (white)
    // meshes remain identifiable without creating tens of thousands of Leaflet layers.
    const handleMapClick = (event: L.LeafletMouseEvent) => {
      const {
        meshes: currentMeshes,
        meshCoords: currentMeshCoords,
        meshIntervals: currentMeshIntervals,
        onMeshSelect: currentOnMeshSelect,
      } = propsRef.current;

      const candidates = currentMeshCoords
        ? Object.entries(currentMeshCoords).map(([code, coords]) => ({
            code,
            lat: coords.lat,
            lon: coords.lon,
          }))
        : (currentMeshes || []).map(mesh => ({
            code: mesh.code,
            lat: mesh.lat,
            lon: mesh.lon,
          }));

      const latInterval = currentMeshIntervals.latInterval;
      const lonInterval = currentMeshIntervals.lonInterval;
      let nearest: { code: string; lat: number; lon: number; distance: number } | null = null;

      for (const candidate of candidates) {
        const latDistance = Math.abs(event.latlng.lat - candidate.lat) / latInterval;
        const lonDistance = Math.abs(event.latlng.lng - candidate.lon) / lonInterval;
        // Ignore clicks outside the bounds of any known mesh cell.
        if (latDistance > 0.5 || lonDistance > 0.5) continue;

        const distance = latDistance * latDistance + lonDistance * lonDistance;
        if (nearest === null || distance < nearest.distance) {
          nearest = { ...candidate, distance };
        }
      }

      if (nearest === null) {
        map.closePopup();
        return;
      }

      if (currentOnMeshSelect) {
        map.closePopup();
        currentOnMeshSelect({ code: nearest.code, lat: nearest.lat, lon: nearest.lon });
        return;
      }

      const content = document.createElement('div');
      const label = document.createElement('div');
      label.textContent = '格子番号';
      const code = document.createElement('strong');
      code.textContent = nearest.code;
      code.style.userSelect = 'text';
      code.style.fontSize = '16px';
      const coordinates = document.createElement('div');
      coordinates.textContent = `緯度 ${nearest.lat.toFixed(6)} / 経度 ${nearest.lon.toFixed(6)}`;
      coordinates.style.marginTop = '4px';
      coordinates.style.color = '#666';
      coordinates.style.fontSize = '12px';
      content.append(label, code, coordinates);

      L.popup({ autoPan: false })
        .setLatLng(event.latlng)
        .setContent(content)
        .openOn(map);
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
    map.on('click', handleMapClick);

    return () => {
      if (layerGroupRef.current) {
        map.removeLayer(layerGroupRef.current);
        layerGroupRef.current = null;
      }
      layerRef.current = null;
      drawFunctionRef.current = null;
      map.off('zoomend', handleViewChange);
      map.off('moveend', handleViewChange);
      map.off('click', handleMapClick);
    };
  }, [map, onMeshClick, onMeshSelect]);

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

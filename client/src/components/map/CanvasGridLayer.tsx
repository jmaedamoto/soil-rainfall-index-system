import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { useMap } from 'react-leaflet';
import { Mesh, RISK_COLORS, RiskLevel } from '../../types/api';

interface CanvasGridLayerProps {
  meshes: Mesh[];
  selectedTime: number;
  meshIntervals: { latInterval: number; lonInterval: number };
  onMeshClick?: (mesh: Mesh) => void;
}

// Canvas描画でメッシュを高速レンダリング
class MeshCanvasLayer extends L.GridLayer {
  private meshes: Mesh[];
  private selectedTime: number;
  private meshIntervals: { latInterval: number; lonInterval: number };
  private onMeshClick?: (mesh: Mesh) => void;
  private timeIndexMap: Map<string, number>;

  constructor(options: any) {
    super(options);
    this.meshes = options.meshes || [];
    this.selectedTime = options.selectedTime || 0;
    this.meshIntervals = options.meshIntervals || { latInterval: 0.008, lonInterval: 0.008 };
    this.onMeshClick = options.onMeshClick;
    this.timeIndexMap = new Map();

    // 時刻インデックスマップ構築
    if (this.meshes.length > 0) {
      this.meshes[0].swi_timeline.forEach((point, index) => {
        this.timeIndexMap.set(`${point.ft}`, index);
      });
    }
  }

  updateData(meshes: Mesh[], selectedTime: number, meshIntervals: { latInterval: number; lonInterval: number }) {
    this.meshes = meshes;
    this.selectedTime = selectedTime;
    this.meshIntervals = meshIntervals;
    this.redraw();
  }

  createTile(coords: any, done: Function) {
    const canvas = document.createElement('canvas');
    const size = this.getTileSize();
    canvas.width = size.x;
    canvas.height = size.y;
    const ctx = canvas.getContext('2d')!;

    // タイル境界を計算
    const tileBounds = this.getTileBounds(coords);

    this.drawMeshesOnTile(ctx, tileBounds, size, coords);

    done(null, canvas);
    return canvas;
  }

  private getTileBounds(coords: any): L.LatLngBounds {
    const zoom = this._map!.getZoom();
    const tileSize = this.getTileSize();
    const crs = this._map!.options.crs!;

    const nwPoint = L.point(coords.x * tileSize.x, coords.y * tileSize.y);
    const sePoint = L.point((coords.x + 1) * tileSize.x, (coords.y + 1) * tileSize.y);

    const nw = crs.pointToLatLng(nwPoint, zoom);
    const se = crs.pointToLatLng(sePoint, zoom);

    return L.latLngBounds(nw, se);
  }

  private _tilePoint(coords: any, latLng: [number, number]) {
    const zoom = this._map!.getZoom();
    const tileSize = this.getTileSize();
    const projection = this._map!.options.crs!;

    const worldPoint = projection.latLngToPoint(L.latLng(latLng[0], latLng[1]), zoom);
    const tileOrigin = L.point(coords.x * tileSize.x, coords.y * tileSize.y);

    return worldPoint.subtract(tileOrigin);
  }

  private drawMeshesOnTile(ctx: CanvasRenderingContext2D, tileBounds: L.LatLngBounds, size: { x: number; y: number }, coords: any) {
    const timeIndex = this.timeIndexMap.get(`${this.selectedTime}`);
    const latHalfSize = this.meshIntervals.latInterval / 2;
    const lonHalfSize = this.meshIntervals.lonInterval / 2;

    this.meshes.forEach(mesh => {
      // メッシュがタイル範囲内にあるかチェック
      const meshBounds = L.latLngBounds(
        [mesh.lat - latHalfSize, mesh.lon - lonHalfSize],
        [mesh.lat + latHalfSize, mesh.lon + lonHalfSize]
      );

      if (!tileBounds.intersects(meshBounds)) return;

      // SWI値とリスクレベル計算
      const swiValue = timeIndex !== undefined && mesh.swi_timeline[timeIndex]
        ? mesh.swi_timeline[timeIndex].value
        : 0;

      let riskLevel = RiskLevel.NORMAL;
      if (swiValue >= mesh.dosyakei_bound) {
        riskLevel = RiskLevel.DISASTER;
      } else if (swiValue >= mesh.warning_bound) {
        riskLevel = RiskLevel.WARNING;
      } else if (swiValue >= mesh.advisary_bound) {
        riskLevel = RiskLevel.CAUTION;
      }

      // 危険度0は描画しない（透明）
      if (riskLevel === RiskLevel.NORMAL) return;

      // タイル座標系での位置計算
      const nw = this._tilePoint(coords, [mesh.lat + latHalfSize, mesh.lon - lonHalfSize]);
      const se = this._tilePoint(coords, [mesh.lat - latHalfSize, mesh.lon + lonHalfSize]);

      const x = Math.min(nw.x, se.x);
      const y = Math.min(nw.y, se.y);
      const width = Math.abs(se.x - nw.x);
      const height = Math.abs(se.y - nw.y);

      // 矩形描画
      ctx.fillStyle = RISK_COLORS[riskLevel];
      ctx.globalAlpha = 0.7;
      ctx.fillRect(x, y, width, height);

      // 境界線描画
      ctx.strokeStyle = 'rgba(200, 200, 200, 0.8)';
      ctx.lineWidth = 0.5;
      ctx.globalAlpha = 1;
      ctx.strokeRect(x, y, width, height);
    });
  }
}

const CanvasGridLayer: React.FC<CanvasGridLayerProps> = ({
  meshes,
  selectedTime,
  meshIntervals,
  onMeshClick
}) => {
  const map = useMap();
  const layerRef = useRef<MeshCanvasLayer | null>(null);

  useEffect(() => {
    if (!map) return;

    // カスタムレイヤー作成
    const layer = new MeshCanvasLayer({
      meshes,
      selectedTime,
      meshIntervals,
      onMeshClick,
      tileSize: 512,  // タイルサイズを大きくして描画効率向上
      opacity: 1,
      zIndex: 200
    });

    layerRef.current = layer;
    layer.addTo(map);

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [map]);

  // データ更新
  useEffect(() => {
    if (layerRef.current) {
      layerRef.current.updateData(meshes, selectedTime, meshIntervals);
    }
  }, [meshes, selectedTime, meshIntervals]);

  return null;
};

export default CanvasGridLayer;
import React, { useEffect, useMemo, useRef } from 'react';
import L from 'leaflet';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import type { AdjustedRainfallPreviewMesh } from '../../types/session';
import { getRainPreviewColor } from '../../features/rainfall-adjustment/previewPalette';
import 'leaflet/dist/leaflet.css';
import './LeafletIcons';

interface AdjustedRainfallPreviewMapProps {
  meshes: Record<string, AdjustedRainfallPreviewMesh>;
  values: Record<string, number | null>;
  metric: 'rain_3hour' | 'rain_1hour_max';
}

const RainfallMeshLayer: React.FC<AdjustedRainfallPreviewMapProps> = ({ meshes, values, metric }) => {
  const map = useMap();
  const layerRef = useRef<L.LayerGroup | null>(null);
  const rendererRef = useRef<L.Renderer | null>(null);

  useEffect(() => {
    rendererRef.current = L.canvas({ padding: 0.75 });
    layerRef.current = L.layerGroup().addTo(map);
    const resizeTimer = window.setTimeout(() => map.invalidateSize(), 50);
    return () => {
      window.clearTimeout(resizeTimer);
      layerRef.current?.remove();
      layerRef.current = null;
      rendererRef.current = null;
    };
  }, [map]);

  useEffect(() => {
    const layer = layerRef.current;
    if (!layer) return;
    layer.clearLayers();

    const latHalf = (30 / 3600) / 2;
    const lonHalf = (45 / 3600) / 2;
    Object.entries(meshes).forEach(([meshCode, mesh]) => {
      const value = values[meshCode];
      if (value === null || value === undefined || !Number.isFinite(value)) return;
      const color = getRainPreviewColor(value);
      const rectangle = L.rectangle(
        [
          [mesh.lat - latHalf, mesh.lon - lonHalf],
          [mesh.lat + latHalf, mesh.lon + lonHalf],
        ],
        {
          color,
          fillColor: color,
          fillOpacity: value <= 0 ? 0 : 0.76,
          weight: 0,
          renderer: rendererRef.current ?? undefined,
        }
      );
      layer.addLayer(rectangle);
    });
  }, [map, meshes, metric, values]);

  return null;
};

const AdjustedRainfallPreviewMap: React.FC<AdjustedRainfallPreviewMapProps> = ({ meshes, values, metric }) => {
  const bounds = useMemo(() => {
    const coordinates = Object.values(meshes);
    if (coordinates.length === 0) return undefined;
    const latitudes = coordinates.map(mesh => mesh.lat);
    const longitudes = coordinates.map(mesh => mesh.lon);
    return L.latLngBounds(
      [Math.min(...latitudes), Math.min(...longitudes)],
      [Math.max(...latitudes), Math.max(...longitudes)]
    );
  }, [meshes]);

  if (!bounds) {
    return <div style={{ height: '100%', display: 'grid', placeItems: 'center', color: '#667085' }}>表示できるメッシュがありません。</div>;
  }

  return (
    <MapContainer
      bounds={bounds}
      boundsOptions={{ padding: [18, 18] }}
      minZoom={6}
      maxZoom={14}
      style={{ height: '100%', width: '100%', background: '#eaf3f8' }}
      scrollWheelZoom
    >
      <TileLayer
        url="https://cyberjapandata.gsi.go.jp/xyz/blank/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>'
      />
      <TileLayer
        url="https://cyberjapandata.gsi.go.jp/xyz/boundary01/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://maps.gsi.go.jp/development/ichiran.html">国土地理院</a>'
        opacity={0.8}
      />
      <RainfallMeshLayer meshes={meshes} values={values} metric={metric} />
    </MapContainer>
  );
};

export default AdjustedRainfallPreviewMap;

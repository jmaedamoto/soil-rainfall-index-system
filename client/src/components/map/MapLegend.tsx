import React from 'react';
import { RISK_COLORS, RISK_LABELS, RiskLevel } from '../../types/api';

interface MapLegendProps {
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
}

const MapLegend: React.FC<MapLegendProps> = ({ position = 'bottom-right' }) => {
  const getPositionStyle = () => {
    const baseStyle = {
      position: 'absolute' as const,
      zIndex: 1000,
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      border: '2px solid rgba(0, 0, 0, 0.2)',
      borderRadius: '8px',
      padding: '12px',
      fontSize: '14px',
      fontFamily: 'Arial, sans-serif',
      boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
      minWidth: '200px'
    };

    switch (position) {
      case 'top-right':
        return { ...baseStyle, top: '10px', right: '10px' };
      case 'top-left':
        return { ...baseStyle, top: '10px', left: '10px' };
      case 'bottom-left':
        return { ...baseStyle, bottom: '10px', left: '10px' };
      case 'bottom-right':
      default:
        return { ...baseStyle, bottom: '10px', right: '10px' };
    }
  };

  const riskLevels = [
    RiskLevel.CAUTION,
    RiskLevel.WARNING,
    RiskLevel.DISASTER
  ];

  return (
    <div style={getPositionStyle()}>
      <div style={{ 
        fontWeight: 'bold', 
        marginBottom: '8px',
        borderBottom: '1px solid #ccc',
        paddingBottom: '4px',
        color: '#333'
      }}>
        ⚠️ 警戒レベル凡例
      </div>
      
      {riskLevels.map((level) => (
        <div
          key={level}
          style={{
            display: 'flex',
            alignItems: 'center',
            marginBottom: '4px',
            gap: '8px'
          }}
        >
          <div
            style={{
              width: '16px',
              height: '16px',
              borderRadius: '2px',
              backgroundColor: RISK_COLORS[level],
              border: '1px solid #333',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.2)',
              flexShrink: 0
            }}
          />
          <span style={{
            color: '#333',
            fontWeight: level >= RiskLevel.WARNING ? 'bold' : 'normal'
          }}>
            レベル{level}: {RISK_LABELS[level]}
          </span>
        </div>
      ))}
      
      <div style={{ 
        marginTop: '8px',
        paddingTop: '8px',
        borderTop: '1px solid #eee',
        fontSize: '12px',
        color: '#666'
      }}>
        <div style={{ marginBottom: '2px' }}>
          🟩 格子: 1km×1kmメッシュ
        </div>
        <div style={{ marginBottom: '2px' }}>
          🎨 色: 警戒レベルのみ表示
        </div>
        <div>
          ※ 正常レベルは非表示
        </div>
      </div>
    </div>
  );
};

export default MapLegend;
import React, { useMemo, useState } from 'react';
import { Area, Prefecture, RISK_COLORS, RiskLevel, RISK_LABELS } from '../../types/api';

interface AreaRiskBarChartProps {
  prefectures: Prefecture[];
  selectedTime: number;
  selectedPrefecture: string;
  onPrefectureChange: (prefectureCode: string) => void;
  title?: string;
  height?: number;
}

const AreaRiskBarChart: React.FC<AreaRiskBarChartProps> = ({
  prefectures,
  selectedTime,
  selectedPrefecture,
  onPrefectureChange,
  title = 'エリア別リスクレベル時系列',
  height = 800
}) => {
  const [hoveredCell, setHoveredCell] = useState<{area: string, time: string, risk: number} | null>(null);

  // 選択された都道府県のエリアを取得
  const areas = useMemo(() => {
    const selectedPref = prefectures.find(p => p.code === selectedPrefecture);
    return selectedPref ? selectedPref.areas : [];
  }, [prefectures, selectedPrefecture]);

  // ヒートマップ用データを準備
  const { timeLabels, allAreas, heatmapMatrix, requiredHeight } = useMemo(() => {
    if (areas.length === 0) return { timeLabels: [], allAreas: [], heatmapMatrix: [], requiredHeight: 0 };

    // 全ての利用可能な時刻を取得
    const timeSet = new Set<number>();
    areas.forEach(area => {
      area.risk_timeline.forEach(point => {
        timeSet.add(point.ft);
      });
    });
    const sortedTimes = Array.from(timeSet).sort((a, b) => a - b);

    // 時刻ラベルを作成（FT0h, FT3h...FT78h）
    const timeLabels = sortedTimes.map(t => t === 0 ? '現在' : `FT${t}h`);

    // 全エリアを表示（制限なし）
    const allAreas = areas
      .map(area => {
        const currentRisk = area.risk_timeline.find(r => r.ft === selectedTime)?.value || 0;
        return { area, currentRisk };
      })
      .sort((a, b) => b.currentRisk - a.currentRisk)
      .map(item => item.area);

    // 必要な高さを計算（全エリアを表示するため）
    const rowHeight = 12; // 1行あたりの高さを縮小
    const headerHeight = 40; // ヘッダー高さを縮小
    const requiredHeight = headerHeight + (allAreas.length * rowHeight);

    // ヒートマップマトリックスを作成
    const heatmapMatrix = allAreas.map(area => {
      return timeLabels.map(timeLabel => {
        const timeValue = timeLabel === '現在' ? 0 : 
          parseInt(timeLabel.replace('FT', '').replace('h', ''));
        const riskPoint = area.risk_timeline.find(r => r.ft === timeValue);
        return {
          areaName: area.name,
          timeLabel: timeLabel,
          timeValue: timeValue,
          riskLevel: riskPoint ? riskPoint.value : 0,
          color: RISK_COLORS[riskPoint ? riskPoint.value as RiskLevel : 0]
        };
      });
    });

    return { timeLabels, allAreas, heatmapMatrix, requiredHeight };
  }, [areas, selectedTime]);

  return (
    <div style={{ marginBottom: '30px' }}>
      {/* タイトル */}
      <h3 style={{ 
        textAlign: 'center', 
        marginBottom: '20px',
        fontSize: '16px',
        fontWeight: 'bold'
      }}>
        {title}
      </h3>

      {/* 都道府県選択 */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        marginBottom: '20px',
        gap: '10px',
        alignItems: 'center'
      }}>
        <label htmlFor="prefecture-select" style={{ fontWeight: 'bold' }}>都道府県:</label>
        <select
          id="prefecture-select"
          value={selectedPrefecture}
          onChange={(e) => onPrefectureChange(e.target.value)}
          style={{
            padding: '8px 12px',
            borderRadius: '4px',
            border: '1px solid #ddd',
            fontSize: '14px',
            minWidth: '120px'
          }}
        >
          {prefectures.map(prefecture => (
            <option key={prefecture.code} value={prefecture.code}>
              {prefecture.name}
            </option>
          ))}
        </select>
      </div>

      {/* ヒートマップ表 */}
      <div style={{ 
        overflowX: 'auto', 
        overflowY: 'hidden', // 縦スクロール完全無効
        height: `${requiredHeight}px`, // 必要な高さを動的設定
        width: '100%',
        border: '1px solid #ddd',
        borderRadius: '8px',
        backgroundColor: '#fff'
      }}>
        <table style={{ 
          borderCollapse: 'collapse',
          minWidth: `${timeLabels.length * 28 + 100}px`, // セル幅を拡大
          fontSize: '8px',
          tableLayout: 'fixed',
          height: '100%'
        }}>
          {/* ヘッダー行（時刻） */}
          <thead>
            <tr>
              <th style={{
                position: 'sticky',
                left: 0,
                top: 0,
                backgroundColor: '#f8f9fa',
                border: '1px solid #ddd',
                padding: '1px 2px',
                minWidth: '100px',
                width: '100px',
                textAlign: 'left',
                fontWeight: 'bold',
                fontSize: '9px',
                zIndex: 3
              }}>
                エリア名
              </th>
              {timeLabels.map((timeLabel, index) => {
                const timeValue = timeLabel === '現在' ? 0 : parseInt(timeLabel.replace('FT', '').replace('h', ''));
                const isSelectedTime = timeValue === selectedTime;
                return (
                  <th key={index} style={{
                    position: 'sticky',
                    top: 0,
                    backgroundColor: isSelectedTime ? '#ffd700' : '#f8f9fa',
                    border: isSelectedTime ? '2px solid #ff6b35' : '1px solid #ddd',
                    padding: '2px',
                    width: '28px',
                    minWidth: '28px',
                    maxWidth: '28px',
                    textAlign: 'center',
                    fontWeight: 'bold',
                    fontSize: '7px',
                    writingMode: 'vertical-rl',
                    textOrientation: 'mixed',
                    height: '40px',
                    zIndex: 2,
                    boxShadow: isSelectedTime ? '0 0 4px rgba(255, 107, 53, 0.5)' : 'none'
                  }}>
                    <div style={{ 
                      transform: 'rotate(180deg)',
                      whiteSpace: 'nowrap'
                    }}>
                      {timeLabel}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          
          {/* データ行（各エリア） */}
          <tbody>
            {heatmapMatrix.map((areaRow, areaIndex) => (
              <tr key={areaIndex}>
                {/* エリア名（左側固定列） */}
                <td style={{
                  position: 'sticky',
                  left: 0,
                  backgroundColor: '#f8f9fa',
                  border: '1px solid #ddd',
                  padding: '1px 2px',
                  fontWeight: 'bold',
                  fontSize: '8px',
                  width: '100px',
                  maxWidth: '100px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  height: '12px', // 固定行高さを縮小
                  lineHeight: '12px',
                  zIndex: 1
                }}>
                  {allAreas[areaIndex].name}
                </td>
                
                {/* 各時刻のセル */}
                {areaRow.map((cell, timeIndex) => {
                  const isSelectedTime = cell.timeValue === selectedTime;
                  return (
                  <td 
                    key={timeIndex}
                    style={{
                      backgroundColor: cell.color,
                      border: isSelectedTime ? '2px solid #ff6b35' : '1px solid #fff',
                      padding: '0',
                      width: '28px',
                      minWidth: '28px',
                      maxWidth: '28px',
                      height: '12px', // 固定行高さを縮小
                      textAlign: 'center',
                      verticalAlign: 'middle',
                      cursor: 'pointer',
                      position: 'relative',
                      boxShadow: isSelectedTime ? '0 0 4px rgba(255, 107, 53, 0.7)' : 'none'
                    }}
                    onMouseEnter={() => setHoveredCell({
                      area: cell.areaName,
                      time: cell.timeLabel,
                      risk: cell.riskLevel
                    })}
                    onMouseLeave={() => setHoveredCell(null)}
                  >
                    {/* リスクレベルを小さく表示 */}
                    <span style={{ 
                      fontSize: '8px', 
                      color: cell.riskLevel >= 2 ? 'white' : '#333',
                      fontWeight: 'bold',
                      lineHeight: '1'
                    }}>
                      {cell.riskLevel || ''}
                    </span>
                  </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ホバー時の詳細情報 */}
      {hoveredCell && (
        <div style={{
          position: 'fixed',
          top: '10px',
          right: '10px',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          color: 'white',
          padding: '8px 12px',
          borderRadius: '4px',
          fontSize: '12px',
          zIndex: 1000,
          pointerEvents: 'none'
        }}>
          <div>エリア: {hoveredCell.area}</div>
          <div>時刻: {hoveredCell.time}</div>
          <div>リスク: {hoveredCell.risk} ({RISK_LABELS[hoveredCell.risk as RiskLevel]})</div>
        </div>
      )}

      {/* 統計情報と凡例 */}
      <div style={{ 
        marginTop: '15px',
        padding: '15px',
        backgroundColor: '#f5f5f5',
        borderRadius: '8px',
        fontSize: '14px'
      }}>
        <div style={{ marginBottom: '15px', fontWeight: 'bold' }}>
          表示中のエリア: {prefectures.find(p => p.code === selectedPrefecture)?.name || '選択中の都道府県'} - 全{allAreas.length}エリア（現在のリスクレベル順）
        </div>

        {/* リスクレベル凡例 */}
        <div>
          <div style={{ fontWeight: 'bold', marginBottom: '10px' }}>リスクレベル凡例:</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
            {Object.entries(RISK_LABELS).map(([level, label]) => {
              const color = RISK_COLORS[parseInt(level) as RiskLevel];
              return (
                <div key={level} style={{ display: 'flex', alignItems: 'center' }}>
                  <div 
                    style={{
                      width: '20px',
                      height: '20px',
                      backgroundColor: color,
                      marginRight: '8px',
                      borderRadius: '3px',
                      border: '1px solid #ddd'
                    }}
                  />
                  <span>{label} (レベル{level})</span>
                </div>
              );
            })}
          </div>
        </div>
        
        <div style={{ marginTop: '15px', fontSize: '12px', color: '#666' }}>
          ※ 縦軸: エリア名、横軸: 時刻（現在からFT78hまで）、各セルの色: リスクレベル
        </div>
        <div style={{ fontSize: '12px', color: '#666' }}>
          ※ 表形式で各エリア・各時刻でのリスクレベルを色で表現
        </div>
      </div>
    </div>
  );
};

export default AreaRiskBarChart;
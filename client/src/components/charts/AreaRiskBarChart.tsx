import React, { useMemo, useState } from 'react';
import { Area, Prefecture, SecondarySubdivision, RISK_COLORS, RiskLevel, RISK_LABELS, RiskTimelineViewMode } from '../../types/api';

interface AreaRiskBarChartProps {
  prefectures: Prefecture[];
  selectedTime: number;
  selectedPrefecture: string;
  onPrefectureChange: (prefectureCode: string) => void;
  onTimeSelect?: (ft: number) => void; // 時刻選択コールバック
  initialTime: string; // UTC時刻（ISO8601形式）
  title?: string;
  height?: number;
}

const AreaRiskBarChart: React.FC<AreaRiskBarChartProps> = ({
  prefectures,
  selectedTime,
  selectedPrefecture,
  onPrefectureChange,
  onTimeSelect,
  initialTime,
  title = 'エリア別リスクレベル時系列',
  height = 800
}) => {
  const [hoveredCell, setHoveredCell] = useState<{area: string, time: number, risk: number} | null>(null);
  const [viewMode, setViewMode] = useState<RiskTimelineViewMode>('municipality');

  // viewModeに応じた表示データの準備
  type DisplayRow = {
    name: string;
    risk_timeline: Array<{ ft: number; value: number }>;
  };

  const displayData = useMemo((): { rows: DisplayRow[], dateGroups: Array<{ date: string; hours: Array<{ ft: number; hour: number }> }> } => {
    // UTC時刻をJST時刻に変換（+9時間）
    const initialTimeUTC = new Date(initialTime);
    const JST_OFFSET = 9 * 60 * 60 * 1000;
    const initialTimeJST = new Date(initialTimeUTC.getTime() + JST_OFFSET);

    let rows: DisplayRow[] = [];
    let timeSet = new Set<number>();

    if (viewMode === 'municipality') {
      // 市町村別表示
      const selectedPref = prefectures.find(p => p.code === selectedPrefecture);
      if (selectedPref) {
        rows = selectedPref.areas.map(area => ({
          name: area.name,
          risk_timeline: area.risk_timeline
        }));
        selectedPref.areas.forEach(area => {
          area.risk_timeline.forEach(point => timeSet.add(point.ft));
        });
      }
    } else if (viewMode === 'subdivision') {
      // 二次細分別表示
      const selectedPref = prefectures.find(p => p.code === selectedPrefecture);
      if (selectedPref && selectedPref.secondary_subdivisions) {
        rows = selectedPref.secondary_subdivisions.map(subdiv => ({
          name: subdiv.name,
          risk_timeline: subdiv.risk_timeline
        }));
        selectedPref.secondary_subdivisions.forEach(subdiv => {
          subdiv.risk_timeline.forEach(point => timeSet.add(point.ft));
        });
      }
    } else if (viewMode === 'prefecture-all') {
      // 全府県一覧表示
      rows = prefectures.map(pref => ({
        name: pref.name,
        risk_timeline: pref.prefecture_risk_timeline || []
      }));
      prefectures.forEach(pref => {
        if (pref.prefecture_risk_timeline) {
          pref.prefecture_risk_timeline.forEach(point => timeSet.add(point.ft));
        }
      });
    }

    const sortedTimes = Array.from(timeSet).sort((a, b) => a - b);

    // 時刻を日付ごとにグループ化
    const dateGroups: Array<{
      date: string;
      hours: Array<{ ft: number; hour: number }>;
    }> = [];

    sortedTimes.forEach(ft => {
      const ftTimeJST = new Date(initialTimeJST.getTime() + ft * 60 * 60 * 1000);
      const ftHour = ftTimeJST.getHours();
      const periodStartTime = new Date(ftTimeJST.getTime() - 3 * 60 * 60 * 1000);
      const dateStr = `${periodStartTime.getMonth() + 1}月${periodStartTime.getDate()}日`;

      let dateGroup = dateGroups.find(g => g.date === dateStr);
      if (!dateGroup) {
        dateGroup = { date: dateStr, hours: [] };
        dateGroups.push(dateGroup);
      }
      dateGroup.hours.push({ ft, hour: ftHour });
    });

    return { rows, dateGroups };
  }, [prefectures, selectedPrefecture, viewMode, initialTime]);

  return (
    <div style={{ marginBottom: '30px' }}>
      {/* タイトル */}
      <h3 style={{
        textAlign: 'center',
        marginBottom: '20px',
        fontSize: '18px',
        fontWeight: 'bold'
      }}>
        {title}
      </h3>

      {/* 都道府県選択と表示モード切り替え */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        marginBottom: '20px',
        gap: '20px',
        alignItems: 'center',
        flexWrap: 'wrap'
      }}>
        {/* 都道府県選択 */}
        {viewMode !== 'prefecture-all' && (
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
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
        )}

        {/* 表示モード切り替え */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label style={{ fontWeight: 'bold' }}>表示:</label>
          <button
            onClick={() => setViewMode('municipality')}
            style={{
              padding: '8px 12px',
              borderRadius: '4px',
              border: viewMode === 'municipality' ? '2px solid #1976d2' : '1px solid #ddd',
              backgroundColor: viewMode === 'municipality' ? '#e3f2fd' : '#fff',
              fontSize: '14px',
              cursor: 'pointer',
              fontWeight: viewMode === 'municipality' ? 'bold' : 'normal'
            }}
          >
            市町村別
          </button>
          <button
            onClick={() => setViewMode('subdivision')}
            style={{
              padding: '8px 12px',
              borderRadius: '4px',
              border: viewMode === 'subdivision' ? '2px solid #1976d2' : '1px solid #ddd',
              backgroundColor: viewMode === 'subdivision' ? '#e3f2fd' : '#fff',
              fontSize: '14px',
              cursor: 'pointer',
              fontWeight: viewMode === 'subdivision' ? 'bold' : 'normal'
            }}
          >
            二次細分別
          </button>
          <button
            onClick={() => setViewMode('prefecture-all')}
            style={{
              padding: '8px 12px',
              borderRadius: '4px',
              border: viewMode === 'prefecture-all' ? '2px solid #1976d2' : '1px solid #ddd',
              backgroundColor: viewMode === 'prefecture-all' ? '#e3f2fd' : '#fff',
              fontSize: '14px',
              cursor: 'pointer',
              fontWeight: viewMode === 'prefecture-all' ? 'bold' : 'normal'
            }}
          >
            全府県一覧
          </button>
        </div>
      </div>

      {/* タイムライン表 */}
      <div style={{
        border: '2px solid #000',
        backgroundColor: '#fff',
        width: '100%'
      }}>
        <table style={{
          borderCollapse: 'collapse',
          width: '100%',
          fontSize: '12px',
          tableLayout: 'fixed'
        }}>
          {/* ヘッダー: 日付行 */}
          <thead>
            <tr style={{ borderBottom: '2px solid #000' }}>
              <th style={{
                backgroundColor: '#fff',
                border: '2px solid #000',
                borderRight: '2px solid #000',
                padding: '4px',
                width: '100px',
                textAlign: 'left',
                fontWeight: 'bold'
              }}>
                {/* 空欄 */}
              </th>
              {dateGroups.map((dateGroup, index) => (
                <th
                  key={index}
                  colSpan={dateGroup.hours.length}
                  style={{
                    backgroundColor: '#fff',
                    border: '2px solid #000',
                    padding: '4px',
                    textAlign: 'center',
                    fontWeight: 'bold',
                    fontSize: '14px'
                  }}
                >
                  {dateGroup.date}
                </th>
              ))}
            </tr>

            {/* ヘッダー: 時刻行 */}
            <tr style={{ borderBottom: '2px solid #000' }}>
              <th style={{
                backgroundColor: '#fff',
                border: '2px solid #000',
                borderRight: '2px solid #000',
                padding: '4px',
                textAlign: 'left',
                fontWeight: 'bold'
              }}>
                {/* 空欄 */}
              </th>
              {displayData.dateGroups.map(dateGroup =>
                dateGroup.hours.map((hourInfo, hourIndex) => {
                  const isSelected = hourInfo.ft === selectedTime;
                  return (
                    <th
                      key={`${dateGroup.date}-${hourIndex}`}
                      style={{
                        backgroundColor: '#fff',
                        borderTop: isSelected ? '3px solid #FF0000' : '2px solid #000',
                        borderLeft: isSelected ? '3px solid #FF0000' : '1px solid #000',
                        borderRight: isSelected ? '3px solid #FF0000' : '1px solid #000',
                        borderBottom: '1px solid #000',
                        padding: '2px',
                        textAlign: 'center',
                        fontWeight: 'normal',
                        fontSize: '11px'
                      }}
                    >
                      {hourInfo.hour}
                    </th>
                  );
                })
              )}
            </tr>
          </thead>

          {/* データ行（各行） */}
          <tbody>
            {displayData.rows.map((row, rowIndex) => (
              <tr key={rowIndex} style={{ borderBottom: '1px solid #000' }}>
                {/* 行名（左側固定列） */}
                <td style={{
                  backgroundColor: '#fff',
                  border: '2px solid #000',
                  borderRight: '2px solid #000',
                  padding: '4px',
                  fontWeight: 'bold',
                  fontSize: '12px',
                  width: '100px',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  {row.name}
                </td>

                {/* 各時刻のセル */}
                {displayData.dateGroups.map(dateGroup =>
                  dateGroup.hours.map((hourInfo, hourIndex) => {
                    const riskPoint = row.risk_timeline.find(r => r.ft === hourInfo.ft);
                    const riskLevel = riskPoint ? riskPoint.value : 0;
                    const color = RISK_COLORS[riskLevel as RiskLevel];
                    const isSelected = hourInfo.ft === selectedTime;
                    const isLastRow = rowIndex === displayData.rows.length - 1;

                    return (
                      <td
                        key={`${dateGroup.date}-${hourIndex}`}
                        style={{
                          backgroundColor: color,
                          borderTop: '1px solid #000',
                          borderLeft: isSelected ? '3px solid #FF0000' : '1px solid #000',
                          borderRight: isSelected ? '3px solid #FF0000' : '1px solid #000',
                          borderBottom: isSelected && isLastRow ? '3px solid #FF0000' : '1px solid #000',
                          padding: '0',
                          height: '24px',
                          cursor: 'pointer',
                          position: 'relative'
                        }}
                        onClick={() => {
                          if (onTimeSelect) {
                            onTimeSelect(hourInfo.ft);
                          }
                        }}
                        onMouseEnter={() => setHoveredCell({
                          area: row.name,
                          time: hourInfo.ft,
                          risk: riskLevel
                        })}
                        onMouseLeave={() => setHoveredCell(null)}
                      >
                        {/* 空セル（色のみで表現） */}
                      </td>
                    );
                  })
                )}
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
          backgroundColor: 'rgba(0, 0, 0, 0.9)',
          color: 'white',
          padding: '12px 16px',
          borderRadius: '6px',
          fontSize: '14px',
          zIndex: 1000,
          pointerEvents: 'none',
          boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
        }}>
          <div><strong>エリア:</strong> {hoveredCell.area}</div>
          <div><strong>予測時刻:</strong> FT{hoveredCell.time}h</div>
          <div><strong>リスクレベル:</strong> {hoveredCell.risk} ({RISK_LABELS[hoveredCell.risk as RiskLevel]})</div>
        </div>
      )}

      {/* 凡例 */}
      <div style={{
        marginTop: '20px',
        padding: '15px',
        backgroundColor: '#f5f5f5',
        borderRadius: '8px',
        border: '1px solid #ddd'
      }}>
        <div style={{ marginBottom: '15px', fontWeight: 'bold', fontSize: '16px' }}>
          リスクレベル凡例
        </div>
        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
          {Object.entries(RISK_LABELS).map(([level, label]) => {
            const color = RISK_COLORS[parseInt(level) as RiskLevel];
            return (
              <div key={level} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div
                  style={{
                    width: '40px',
                    height: '24px',
                    backgroundColor: color,
                    border: '1px solid #000',
                    borderRadius: '3px'
                  }}
                />
                <span style={{ fontSize: '14px' }}>
                  レベル{level}: {label}
                </span>
              </div>
            );
          })}
        </div>

        <div style={{ marginTop: '15px', fontSize: '13px', color: '#666' }}>
          ※ 表示中: {prefectures.find(p => p.code === selectedPrefecture)?.name || ''} - 全{allAreas.length}エリア
        </div>
      </div>
    </div>
  );
};

export default AreaRiskBarChart;

import React, { useMemo, useState } from 'react';
import { Area, Prefecture, RISK_COLORS, RiskLevel, RISK_LABELS } from '../../types/api';

interface AreaRiskBarChartProps {
  prefectures: Prefecture[];
  selectedTime: number;
  selectedPrefecture: string;
  onPrefectureChange: (prefectureCode: string) => void;
  initialTime: string; // UTC時刻（ISO8601形式）
  title?: string;
  height?: number;
}

const AreaRiskBarChart: React.FC<AreaRiskBarChartProps> = ({
  prefectures,
  selectedTime,
  selectedPrefecture,
  onPrefectureChange,
  initialTime,
  title = 'エリア別リスクレベル時系列',
  height = 800
}) => {
  const [hoveredCell, setHoveredCell] = useState<{area: string, time: number, risk: number} | null>(null);

  // 選択された都道府県のエリアを取得
  const areas = useMemo(() => {
    const selectedPref = prefectures.find(p => p.code === selectedPrefecture);
    return selectedPref ? selectedPref.areas : [];
  }, [prefectures, selectedPrefecture]);

  // タイムライン構造を準備（日付と時刻のグループ化）
  const { dateGroups, allAreas } = useMemo(() => {
    if (areas.length === 0) return { dateGroups: [], allAreas: [] };

    // UTC時刻をJST時刻に変換（+9時間）
    const initialTimeUTC = new Date(initialTime);
    const JST_OFFSET = 9 * 60 * 60 * 1000; // 9時間をミリ秒に変換
    const initialTimeJST = new Date(initialTimeUTC.getTime() + JST_OFFSET);

    // 全ての利用可能な時刻を取得
    const timeSet = new Set<number>();
    areas.forEach(area => {
      area.risk_timeline.forEach(point => {
        timeSet.add(point.ft);
      });
    });
    const sortedTimes = Array.from(timeSet).sort((a, b) => a - b);

    // 時刻を日付ごとにグループ化
    // FTは3時間期間の終了時刻を表す（FT0=21-24時、FT3=0-3時、FT6=3-6時...）
    const dateGroups: Array<{
      date: string;
      hours: Array<{ ft: number; hour: number }>;
    }> = [];

    sortedTimes.forEach(ft => {
      // FT時刻（期間の終了時刻）をJSTで計算
      const ftTimeJST = new Date(initialTimeJST.getTime() + ft * 60 * 60 * 1000);
      const ftHour = ftTimeJST.getHours();

      // FTが表す3時間期間の開始時刻を計算（FT - 3時間）
      const periodStartTime = new Date(ftTimeJST.getTime() - 3 * 60 * 60 * 1000);

      // 期間の日付は開始時刻の日付を使用
      const dateStr = `${periodStartTime.getMonth() + 1}月${periodStartTime.getDate()}日`;

      let dateGroup = dateGroups.find(g => g.date === dateStr);
      if (!dateGroup) {
        dateGroup = { date: dateStr, hours: [] };
        dateGroups.push(dateGroup);
      }
      dateGroup.hours.push({ ft, hour: ftHour });
    });

    // 全エリアを現在のリスクレベル順にソート
    const allAreas = areas
      .map(area => {
        const currentRisk = area.risk_timeline.find(r => r.ft === selectedTime)?.value || 0;
        return { area, currentRisk };
      })
      .sort((a, b) => b.currentRisk - a.currentRisk)
      .map(item => item.area);

    return { dateGroups, allAreas };
  }, [areas, selectedTime, initialTime]);

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
              {dateGroups.map(dateGroup =>
                dateGroup.hours.map((hourInfo, hourIndex) => (
                  <th
                    key={`${dateGroup.date}-${hourIndex}`}
                    style={{
                      backgroundColor: '#fff',
                      border: '1px solid #000',
                      borderTop: '2px solid #000',
                      padding: '2px',
                      textAlign: 'center',
                      fontWeight: 'normal',
                      fontSize: '11px'
                    }}
                  >
                    {hourInfo.hour}
                  </th>
                ))
              )}
            </tr>
          </thead>

          {/* データ行（各エリア） */}
          <tbody>
            {allAreas.map((area, areaIndex) => (
              <tr key={areaIndex} style={{ borderBottom: '1px solid #000' }}>
                {/* エリア名（左側固定列） */}
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
                  {area.name}
                </td>

                {/* 各時刻のセル */}
                {dateGroups.map(dateGroup =>
                  dateGroup.hours.map((hourInfo, hourIndex) => {
                    const riskPoint = area.risk_timeline.find(r => r.ft === hourInfo.ft);
                    const riskLevel = riskPoint ? riskPoint.value : 0;
                    const color = RISK_COLORS[riskLevel as RiskLevel];

                    return (
                      <td
                        key={`${dateGroup.date}-${hourIndex}`}
                        style={{
                          backgroundColor: color,
                          border: '1px solid #000',
                          padding: '0',
                          height: '24px',
                          cursor: 'pointer',
                          position: 'relative'
                        }}
                        onMouseEnter={() => setHoveredCell({
                          area: area.name,
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

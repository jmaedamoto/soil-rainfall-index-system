import React, { useState, useEffect } from 'react';
import { apiClient_ } from '../services/api';
import SoilRainfallMap from '../components/map/SoilRainfallMap';
import AreaRiskBarChart from '../components/charts/AreaRiskBarChart';
import { SoilRainfallData, Mesh } from '../types/api';

const Production: React.FC = () => {
  const [data, setData] = useState<SoilRainfallData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState(0);
  const [selectedPrefecture, setSelectedPrefecture] = useState<string>('');
  const [isTimeChanging, setIsTimeChanging] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const result = await apiClient_.testFullCalculation();
        setData(result);

        // デフォルトで最初の都道府県を選択
        const firstPrefCode = Object.keys(result.prefectures)[0];
        setSelectedPrefecture(firstPrefCode);

        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : '予期しないエラーが発生しました');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleTimeChange = (newTime: number) => {
    setIsTimeChanging(true);
    setSelectedTime(newTime);
    setTimeout(() => setIsTimeChanging(false), 100);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (!data) return;
    const maxFt = Math.max(...data.prefectures[Object.keys(data.prefectures)[0]].areas[0].meshes[0].swi_timeline.map(t => t.ft));

    if (e.key === 'ArrowLeft' && selectedTime > 0) {
      handleTimeChange(selectedTime - 3);
    } else if (e.key === 'ArrowRight' && selectedTime < maxFt) {
      handleTimeChange(selectedTime + 3);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column', gap: '20px' }}>
        <div style={{
          width: '50px',
          height: '50px',
          border: '5px solid #f3f3f3',
          borderTop: '5px solid #1976D2',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }} />
        <div style={{ fontSize: '18px' }}>データ読み込み中...</div>
        <div style={{ fontSize: '14px', color: '#666' }}>26,000メッシュのデータを処理しています（2〜3分かかります）</div>
        <style>
          {`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}
        </style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div style={{ color: 'red' }}>エラー: {error}</div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const allMeshes: Mesh[] = Object.values(data.prefectures).flatMap(pref =>
    pref.areas.flatMap(area => area.meshes)
  );

  const availableTimes = allMeshes.length > 0
    ? allMeshes[0].swi_timeline.map(t => t.ft)
    : [];

  const prefectureOptions = Object.entries(data.prefectures).map(([code, pref]) => ({
    value: code,
    label: pref.name
  }));

  const initialTime = data.initial_time || data.prefectures[Object.keys(data.prefectures)[0]]?.areas[0]?.meshes[0]?.swi_timeline[0]?.initial_time;

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '20px' }}>土壌雨量指数監視システム</h1>

      {/* 時刻選択 */}
      <div style={{
        marginBottom: '20px',
        padding: '15px',
        backgroundColor: '#f5f5f5',
        borderRadius: '8px'
      }}>
        <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>
          予測時刻 (FT): {selectedTime}時間後
        </label>
        <input
          type="range"
          min={0}
          max={availableTimes.length > 0 ? Math.max(...availableTimes) : 0}
          step={3}
          value={selectedTime}
          onChange={(e) => handleTimeChange(Number(e.target.value))}
          onKeyDown={handleKeyPress}
          style={{ width: '100%' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '5px', fontSize: '12px' }}>
          {availableTimes.map(ft => (
            <span key={ft}>FT{ft}</span>
          ))}
        </div>
      </div>

      {/* 地図表示 */}
      <div style={{ marginBottom: '30px' }}>
        <h2 style={{ marginBottom: '15px' }}>危険度分布図</h2>
        <SoilRainfallMap
          meshes={allMeshes}
          selectedTime={selectedTime}
          selectedPrefecture={selectedPrefecture}
          prefectureData={data.prefectures}
          isLoading={isTimeChanging}
        />
      </div>

      {/* エリア別リスクレベル時系列 */}
      <div style={{ marginBottom: '30px' }}>
        <h2 style={{ marginBottom: '15px' }}>地域別危険度推移</h2>
        <AreaRiskBarChart
          prefectures={Object.values(data.prefectures)}
          selectedTime={selectedTime}
          selectedPrefecture={selectedPrefecture}
          onPrefectureChange={setSelectedPrefecture}
          initialTime={initialTime}
        />
      </div>

      {/* 凡例 */}
      <div style={{
        marginTop: '20px',
        padding: '15px',
        backgroundColor: '#f9f9f9',
        borderRadius: '8px'
      }}>
        <h3 style={{ marginBottom: '10px' }}>危険度レベル</h3>
        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '30px', height: '20px', backgroundColor: '#90EE90', border: '1px solid #ddd' }}></div>
            <span>レベル1: 注意</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '30px', height: '20px', backgroundColor: '#FFD700', border: '1px solid #ddd' }}></div>
            <span>レベル2: 警報</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '30px', height: '20px', backgroundColor: '#FF6347', border: '1px solid #ddd' }}></div>
            <span>レベル3: 土砂災害警戒</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Production;

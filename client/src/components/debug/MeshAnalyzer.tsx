import React from 'react';
import { Mesh, RiskLevel } from '../../types/api';

interface MeshAnalyzerProps {
  meshes: Mesh[];
  selectedTime?: number;
}

const MeshAnalyzer: React.FC<MeshAnalyzerProps> = ({ meshes, selectedTime = 0 }) => {
  if (meshes.length === 0) {
    return <div>メッシュデータがありません</div>;
  }

  // 座標の分析
  const lats = meshes.map(m => m.lat);
  const lons = meshes.map(m => m.lon);
  
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  
  // メッシュ間隔の分析
  const sortedLats = [...new Set(lats)].sort((a, b) => a - b);
  const sortedLons = [...new Set(lons)].sort((a, b) => a - b);
  
  const latIntervals = [];
  const lonIntervals = [];
  
  for (let i = 1; i < sortedLats.length; i++) {
    const diff = sortedLats[i] - sortedLats[i-1];
    if (diff > 0.0001) { // 非常に小さい差を除外
      latIntervals.push(diff);
    }
  }
  
  for (let i = 1; i < sortedLons.length; i++) {
    const diff = sortedLons[i] - sortedLons[i-1];
    if (diff > 0.0001) { // 非常に小さい差を除外
      lonIntervals.push(diff);
    }
  }
  
  const avgLatInterval = latIntervals.length > 0 ? latIntervals.reduce((a, b) => a + b, 0) / latIntervals.length : 0;
  const avgLonInterval = lonIntervals.length > 0 ? lonIntervals.reduce((a, b) => a + b, 0) / lonIntervals.length : 0;
  
  const minLatInterval = latIntervals.length > 0 ? Math.min(...latIntervals) : 0;
  const minLonInterval = lonIntervals.length > 0 ? Math.min(...lonIntervals) : 0;

  // 最頻値（最も一般的な間隔）を計算
  let mostCommonLatInterval = 0;
  let mostCommonLonInterval = 0;
  
  if (latIntervals.length > 0) {
    const latCounts = latIntervals.reduce((acc, diff) => {
      const rounded = Math.round(diff * 1000000) / 1000000;
      acc[rounded] = (acc[rounded] || 0) + 1;
      return acc;
    }, {} as Record<number, number>);
    
    mostCommonLatInterval = Number(Object.keys(latCounts).reduce((a, b) => 
      latCounts[Number(a)] > latCounts[Number(b)] ? a : b
    ));
  }
  
  if (lonIntervals.length > 0) {
    const lonCounts = lonIntervals.reduce((acc, diff) => {
      const rounded = Math.round(diff * 1000000) / 1000000;
      acc[rounded] = (acc[rounded] || 0) + 1;
      return acc;
    }, {} as Record<number, number>);
    
    mostCommonLonInterval = Number(Object.keys(lonCounts).reduce((a, b) => 
      lonCounts[Number(a)] > lonCounts[Number(b)] ? a : b
    ));
  }
  
  // 都道府県別の分析
  const prefectureCounts: Record<string, number> = {};
  meshes.forEach(mesh => {
    const prefCode = mesh.code.substring(0, 2);
    prefectureCounts[prefCode] = (prefectureCounts[prefCode] || 0) + 1;
  });

  // 警戒レベル分析（選択された時刻）
  const riskLevelCounts = { 0: 0, 1: 0, 2: 0, 3: 0 };
  const sampleValues: number[] = [];
  const sampleMeshDetails: any[] = [];
  const timelineAnalysis = {
    availableFTs: new Set<number>(),
    missingDataCount: 0,
    sampleTimelines: [] as any[]
  };
  
  const boundaryAnalysis = {
    advisaryExceeded: 0,
    warningExceeded: 0,
    dosyakeiExceeded: 0,
    totalSamples: 0,
    sampleBoundaries: [] as any[]
  };

  meshes.forEach((mesh, index) => {
    const swiData = mesh.swi_timeline.find(point => point.ft === selectedTime);
    const swiValue = swiData?.value || 0;
    
    // 時系列データの調査
    mesh.swi_timeline.forEach(point => timelineAnalysis.availableFTs.add(point.ft));
    
    if (!swiData) {
      timelineAnalysis.missingDataCount++;
    }
    
    // サンプルデータの収集
    if (sampleValues.length < 10) {
      sampleValues.push(swiValue);
      sampleMeshDetails.push({
        code: mesh.code,
        swiValue: swiValue,
        advisary: mesh.advisary_bound,
        warning: mesh.warning_bound,
        dosyakei: mesh.dosyakei_bound,
        timelineLength: mesh.swi_timeline.length
      });
    }
    
    // 最初の3個のメッシュの時系列を保存
    if (timelineAnalysis.sampleTimelines.length < 3) {
      timelineAnalysis.sampleTimelines.push({
        code: mesh.code,
        timeline: mesh.swi_timeline.slice(0, 5) // 最初の5個のポイント
      });
    }
    
    // 境界値サンプル
    if (boundaryAnalysis.sampleBoundaries.length < 5) {
      boundaryAnalysis.sampleBoundaries.push({
        code: mesh.code,
        advisary: mesh.advisary_bound,
        warning: mesh.warning_bound,
        dosyakei: mesh.dosyakei_bound
      });
    }
    
    boundaryAnalysis.totalSamples++;
    
    let riskLevel = RiskLevel.NORMAL;
    if (swiValue >= mesh.dosyakei_bound) {
      riskLevel = RiskLevel.DISASTER;
      boundaryAnalysis.dosyakeiExceeded++;
    } else if (swiValue >= mesh.warning_bound) {
      riskLevel = RiskLevel.WARNING;
      boundaryAnalysis.warningExceeded++;
    } else if (swiValue >= mesh.advisary_bound) {
      riskLevel = RiskLevel.CAUTION;
      boundaryAnalysis.advisaryExceeded++;
    }
    
    riskLevelCounts[riskLevel]++;
  });
  
  return (
    <div style={{ 
      backgroundColor: '#f5f5f5', 
      padding: '15px', 
      borderRadius: '8px',
      marginBottom: '20px',
      fontSize: '14px'
    }}>
      <h3>🔍 メッシュデータ分析</h3>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
        <div>
          <h4>基本統計</h4>
          <p><strong>総メッシュ数:</strong> {meshes.length.toLocaleString()}個</p>
          <p><strong>緯度範囲:</strong> {minLat.toFixed(4)} 〜 {maxLat.toFixed(4)}</p>
          <p><strong>経度範囲:</strong> {minLon.toFixed(4)} 〜 {maxLon.toFixed(4)}</p>
        </div>
        
        <div>
          <h4>メッシュ間隔</h4>
          <p><strong>最頻緯度間隔:</strong> {mostCommonLatInterval.toFixed(6)}度</p>
          <p><strong>最頻経度間隔:</strong> {mostCommonLonInterval.toFixed(6)}度</p>
          <p><strong>平均緯度間隔:</strong> {avgLatInterval.toFixed(6)}度</p>
          <p><strong>平均経度間隔:</strong> {avgLonInterval.toFixed(6)}度</p>
          <p><strong>最小緯度間隔:</strong> {minLatInterval.toFixed(6)}度</p>
          <p><strong>最小経度間隔:</strong> {minLonInterval.toFixed(6)}度</p>
        </div>
        
        <div>
          <h4>推定格子サイズ</h4>
          <p><strong>緯度方向:</strong> {(mostCommonLatInterval * 111).toFixed(1)}km</p>
          <p><strong>経度方向:</strong> {(mostCommonLonInterval * 91).toFixed(1)}km</p>
          <p style={{ color: '#666', fontSize: '12px' }}>
            ※ 最頻値基準、1度≈111km(緯度), ≈91km(経度/関西地方)
          </p>
        </div>
        
        <div>
          <h4>都道府県別メッシュ数</h4>
          {Object.entries(prefectureCounts).map(([code, count]) => (
            <p key={code}>
              <strong>{code}:</strong> {count.toLocaleString()}個
            </p>
          ))}
        </div>
        
        <div>
          <h4>警戒レベル分析（FT{selectedTime}h）</h4>
          <p><strong>レベル0（正常）:</strong> {riskLevelCounts[0].toLocaleString()}個 ({((riskLevelCounts[0] / meshes.length) * 100).toFixed(1)}%)</p>
          <p><strong>レベル1（注意）:</strong> {riskLevelCounts[1].toLocaleString()}個 ({((riskLevelCounts[1] / meshes.length) * 100).toFixed(1)}%)</p>
          <p><strong>レベル2（警報）:</strong> {riskLevelCounts[2].toLocaleString()}個 ({((riskLevelCounts[2] / meshes.length) * 100).toFixed(1)}%)</p>
          <p><strong>レベル3（土砂災害）:</strong> {riskLevelCounts[3].toLocaleString()}個 ({((riskLevelCounts[3] / meshes.length) * 100).toFixed(1)}%)</p>
        </div>
        
        <div>
          <h4>基準値分析</h4>
          <p><strong>サンプル土壌雨量指数:</strong> {sampleValues.slice(0, 5).map(v => v.toFixed(1)).join(', ')}...</p>
          <p><strong>注意報基準超過:</strong> {boundaryAnalysis.advisaryExceeded}個</p>
          <p><strong>警報基準超過:</strong> {boundaryAnalysis.warningExceeded}個</p>
          <p><strong>土砂災害基準超過:</strong> {boundaryAnalysis.dosyakeiExceeded}個</p>
        </div>
        
        <div>
          <h4>🔍 時系列データ調査</h4>
          <p><strong>利用可能FT:</strong> {Array.from(timelineAnalysis.availableFTs).sort((a, b) => a - b).join(', ')}</p>
          <p><strong>データ欠損:</strong> {timelineAnalysis.missingDataCount}個（FT{selectedTime}h）</p>
          <p><strong>サンプルメッシュの時系列長:</strong> {sampleMeshDetails.map(m => `${m.code}: ${m.timelineLength}個`).slice(0, 3).join(', ')}</p>
        </div>
        
        <div>
          <h4>⚠️ データ問題診断</h4>
          {timelineAnalysis.sampleTimelines.map((sample, idx) => (
            <div key={idx} style={{ marginBottom: '10px', fontSize: '12px' }}>
              <strong>メッシュ {sample.code}:</strong><br />
              {sample.timeline.map((point: any) => `FT${point.ft}: ${point.value.toFixed(1)}`).join(', ')}
            </div>
          ))}
        </div>
        
        <div>
          <h4>📊 サンプル詳細比較</h4>
          {sampleMeshDetails.slice(0, 3).map((detail, idx) => (
            <div key={idx} style={{ marginBottom: '8px', fontSize: '12px' }}>
              <strong>{detail.code}:</strong> 
              SWI={detail.swiValue.toFixed(1)}, 
              基準値(注意:{detail.advisary}/警報:{detail.warning}/土砂:{detail.dosyakei})
              {detail.swiValue >= detail.dosyakei && <span style={{ color: 'red' }}> → レベル3</span>}
              {detail.swiValue >= detail.warning && detail.swiValue < detail.dosyakei && <span style={{ color: 'orange' }}> → レベル2</span>}
              {detail.swiValue >= detail.advisary && detail.swiValue < detail.warning && <span style={{ color: 'yellow' }}> → レベル1</span>}
              {detail.swiValue < detail.advisary && <span style={{ color: 'green' }}> → レベル0</span>}
            </div>
          ))}
        </div>
        
        <div>
          <h4>🚨 異常値チェック</h4>
          <p><strong>境界値の範囲:</strong></p>
          {boundaryAnalysis.sampleBoundaries.map((boundary, idx) => (
            <p key={idx} style={{ fontSize: '12px' }}>
              {boundary.code}: 注意{boundary.advisary} / 警報{boundary.warning} / 土砂{boundary.dosyakei}
            </p>
          ))}
        </div>
      </div>
      
      <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#e3f2fd', borderRadius: '4px' }}>
        <h4>💡 格子サイズ設定状況</h4>
        <p><strong>推奨格子サイズ:</strong> 緯度 {mostCommonLatInterval.toFixed(6)}度 × 経度 {mostCommonLonInterval.toFixed(6)}度</p>
        <p><strong>現在の格子サイズ:</strong> 動的計算（最頻値使用）</p>
        <p><strong>以前の固定値:</strong> 緯度 0.008000度 × 経度 0.008000度</p>
        <div style={{ 
          color: mostCommonLatInterval > 0 ? '#4caf50' : '#f44336', 
          fontWeight: 'bold',
          marginTop: '8px'
        }}>
          {mostCommonLatInterval > 0 ? (
            <>✅ 格子サイズを実際のメッシュ間隔に動的調整済み</>
          ) : (
            <>⚠️ メッシュ間隔の計算ができません</>
          )}
        </div>
        <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
          ※ 最頻値を使用することで、最も一般的なメッシュ間隔に格子サイズを合わせています
        </div>
      </div>
    </div>
  );
};

export default MeshAnalyzer;
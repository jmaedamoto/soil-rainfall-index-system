import React from 'react';
import { CalculationResult } from '../../types/api';

interface DataDownloaderProps {
  data: CalculationResult | null;
}

const DataDownloader: React.FC<DataDownloaderProps> = ({ data }) => {
  const downloadSampleData = () => {
    if (!data) return;

    // サンプルメッシュのデータを抽出
    const sampleMeshes: any[] = [];
    Object.entries(data.prefectures).forEach(([prefCode, prefecture]) => {
      prefecture.areas.forEach(area => {
        area.meshes.slice(0, 10).forEach(mesh => { // 最初の10個のメッシュ
          sampleMeshes.push({
            prefecture: prefCode,
            area: area.name,
            code: mesh.code,
            lat: mesh.lat,
            lon: mesh.lon,
            advisary_bound: mesh.advisary_bound,
            warning_bound: mesh.warning_bound,
            dosyakei_bound: mesh.dosyakei_bound,
            swi_timeline: mesh.swi_timeline,
            rain_timeline: mesh.rain_timeline
          });
        });
      });
    });

    const jsonData = {
      metadata: {
        calculation_time: data.calculation_time,
        initial_time: data.initial_time,
        total_meshes: Object.values(data.prefectures).reduce((total, pref) => 
          total + pref.areas.reduce((areaTotal, area) => areaTotal + area.meshes.length, 0), 0
        ),
        sample_count: sampleMeshes.length
      },
      sample_meshes: sampleMeshes
    };

    const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `soil_rainfall_sample_data_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadFullData = () => {
    if (!data) return;

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `soil_rainfall_full_data_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const analyzeDataStructure = () => {
    if (!data) return;

    console.group('🔍 データ構造詳細分析');
    
    // 都道府県レベルの分析
    Object.entries(data.prefectures).forEach(([prefCode, prefecture]) => {
      console.group(`都道府県: ${prefecture.name} (${prefCode})`);
      
      prefecture.areas.forEach((area, areaIdx) => {
        if (areaIdx < 2) { // 最初の2つの地域のみ
          console.group(`地域: ${area.name}`);
          
          area.meshes.slice(0, 3).forEach(mesh => { // 最初の3つのメッシュ
            console.log(`メッシュ ${mesh.code}:`, {
              座標: { lat: mesh.lat, lon: mesh.lon },
              基準値: {
                注意報: mesh.advisary_bound,
                警報: mesh.warning_bound,
                土砂災害: mesh.dosyakei_bound
              },
              時系列データ: {
                SWI: mesh.swi_timeline,
                Rain: mesh.rain_timeline
              }
            });
          });
          
          console.groupEnd();
        }
      });
      
      console.groupEnd();
    });
    
    console.groupEnd();
  };

  if (!data) {
    return (
      <div style={{ 
        padding: '15px', 
        backgroundColor: '#f5f5f5', 
        borderRadius: '8px',
        marginBottom: '20px' 
      }}>
        <h3>🔧 データ調査ツール</h3>
        <p>データが読み込まれていません</p>
      </div>
    );
  }

  return (
    <div style={{ 
      padding: '15px', 
      backgroundColor: '#f5f5f5', 
      borderRadius: '8px',
      marginBottom: '20px' 
    }}>
      <h3>🔧 データ調査ツール</h3>
      
      <div style={{ 
        display: 'flex', 
        gap: '10px', 
        flexWrap: 'wrap',
        marginBottom: '15px'
      }}>
        <button
          onClick={downloadSampleData}
          style={{
            padding: '8px 16px',
            backgroundColor: '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          📥 サンプルデータダウンロード
        </button>
        
        <button
          onClick={downloadFullData}
          style={{
            padding: '8px 16px',
            backgroundColor: '#FF9800',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          📦 全データダウンロード
        </button>
        
        <button
          onClick={analyzeDataStructure}
          style={{
            padding: '8px 16px',
            backgroundColor: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          🔍 コンソールで詳細分析
        </button>
      </div>
      
      <div style={{ fontSize: '12px', color: '#666' }}>
        <p>• サンプルデータ: 各都道府県から最大10メッシュを抽出</p>
        <p>• 全データ: 完全なAPIレスポンス（大容量注意）</p>
        <p>• 詳細分析: ブラウザコンソール（F12）で構造を確認</p>
      </div>
    </div>
  );
};

export default DataDownloader;
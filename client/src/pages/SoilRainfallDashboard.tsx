import React, { useState, useEffect, useMemo } from 'react';
import SoilRainfallMap from '../components/map/SoilRainfallMap';
import TimeSlider from '../components/map/TimeSlider';
import RiskTimelineChart from '../components/charts/RiskTimelineChart';
import SoilRainfallTimelineChart from '../components/charts/SoilRainfallTimelineChart';
import AreaRiskBarChart from '../components/charts/AreaRiskBarChart';
import ProgressBar from '../components/common/ProgressBar';
import MeshAnalyzer from '../components/debug/MeshAnalyzer';
import DataDownloader from '../components/debug/DataDownloader';
import { apiClient_ } from '../services/api';
import { CalculationResult, Mesh, Area, Prefecture } from '../types/api';

const SoilRainfallDashboard: React.FC = () => {
  const [data, setData] = useState<CalculationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState(0);
  
  // 時刻入力フィールドの状態（テストデータに合わせて2023-06-02T00:00:00Zに修正）
  const [swiInitialTime, setSwiInitialTime] = useState('2023-06-02T00:00:00Z');
  const [guidInitialTime, setGuidInitialTime] = useState('2023-06-02T00:00:00Z');
  const [useSeparateTimes, setUseSeparateTimes] = useState(false);
  
  // データソース選択の状態
  const [dataSource, setDataSource] = useState<'test' | 'production'>('test');
  const [productionDateTime, setProductionDateTime] = useState(() => {
    // デフォルトは現在時刻の3時間前（6時間区切り）
    const now = new Date();
    const threeHoursAgo = new Date(now.getTime() - 3 * 60 * 60 * 1000);
    const hours = Math.floor(threeHoursAgo.getHours() / 6) * 6;
    threeHoursAgo.setHours(hours, 0, 0, 0);
    return threeHoursAgo.toISOString().slice(0, 19);
  });
  
  // 時刻変更ハンドラー
  const handleTimeChange = (newTime: number) => {
    setIsTimeChanging(true);
    setSelectedTime(newTime);
    
    // 少し遅延を入れて描画完了を待つ
    setTimeout(() => {
      setIsTimeChanging(false);
    }, 100);
  };
  const [selectedMesh, setSelectedMesh] = useState<Mesh | null>(null);
  const [selectedArea, setSelectedArea] = useState<Area | null>(null);
  const [selectedPrefecture, setSelectedPrefecture] = useState<string>('');
  const [isTimeChanging, setIsTimeChanging] = useState(false);

  // 全メッシュデータを平坦化
  const allMeshes = useMemo(() => {
    if (!data) return [];
    
    const meshes: Mesh[] = [];
    Object.values(data.prefectures).forEach((prefecture: Prefecture) => {
      prefecture.areas.forEach((area: Area) => {
        area.meshes.forEach((mesh: Mesh) => {
          meshes.push(mesh);
        });
      });
    });
    return meshes;
  }, [data]);

  // 全エリアデータを平坦化
  const allAreas = useMemo(() => {
    if (!data) return [];
    
    const areas: Area[] = [];
    Object.values(data.prefectures).forEach((prefecture: Prefecture) => {
      prefecture.areas.forEach((area: Area) => {
        areas.push(area);
      });
    });
    return areas;
  }, [data]);

  // 利用可能な時刻のリストを作成
  const availableTimes = useMemo(() => {
    if (allMeshes.length === 0) return [];
    
    const timeSet = new Set<number>();
    allMeshes.forEach(mesh => {
      mesh.swi_timeline.forEach(point => {
        timeSet.add(point.ft);
      });
    });
    
    return Array.from(timeSet).sort((a, b) => a - b);
  }, [allMeshes]);

  // データ読み込み完了時に最初の都道府県を選択
  useEffect(() => {
    if (data && Object.keys(data.prefectures).length > 0 && !selectedPrefecture) {
      const firstPrefCode = Object.keys(data.prefectures)[0];
      setSelectedPrefecture(firstPrefCode);
    }
  }, [data, selectedPrefecture]);

  // 都道府県リストと現在のインデックスを取得
  const prefectureList = useMemo(() => {
    if (!data) return [];
    return Object.keys(data.prefectures);
  }, [data]);

  const currentPrefectureIndex = useMemo(() => {
    return prefectureList.indexOf(selectedPrefecture);
  }, [prefectureList, selectedPrefecture]);

  // キーボードショートカット
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // テキスト入力フィールドにフォーカスがある場合はスキップ
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (event.key) {
        case 'ArrowUp':
          event.preventDefault();
          // 都道府県を上に移動（前の都道府県）
          if (currentPrefectureIndex > 0) {
            setSelectedPrefecture(prefectureList[currentPrefectureIndex - 1]);
          }
          break;
        
        case 'ArrowDown':
          event.preventDefault();
          // 都道府県を下に移動（次の都道府県）
          if (currentPrefectureIndex < prefectureList.length - 1) {
            setSelectedPrefecture(prefectureList[currentPrefectureIndex + 1]);
          }
          break;
        
        case 'ArrowLeft':
          event.preventDefault();
          // 時刻を左に移動（前の時刻）
          const currentTimeIndex = availableTimes.indexOf(selectedTime);
          if (currentTimeIndex > 0) {
            handleTimeChange(availableTimes[currentTimeIndex - 1]);
          }
          break;
        
        case 'ArrowRight':
          event.preventDefault();
          // 時刻を右に移動（次の時刻）
          const nextTimeIndex = availableTimes.indexOf(selectedTime);
          if (nextTimeIndex < availableTimes.length - 1) {
            handleTimeChange(availableTimes[nextTimeIndex + 1]);
          }
          break;
      }
    };

    // グローバルキーボードイベントリスナーを追加
    document.addEventListener('keydown', handleKeyDown);
    
    // クリーンアップ
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [currentPrefectureIndex, prefectureList, selectedTime, availableTimes]);

  // データ読み込み
  const loadData = async () => {
    setLoading(true);
    setError(null);
    setLoadingProgress(0);
    setLoadingMessage('APIサーバーに接続中...');
    
    try {
      console.log('APIサーバーへの接続を開始...');
      
      // まずヘルスチェック
      setLoadingProgress(10);
      setLoadingMessage('サーバー状態を確認中...');
      const healthStatus = await apiClient_.getHealthStatus();
      console.log('ヘルスチェック結果:', healthStatus);
      
      if (healthStatus.status !== 'success') {
        throw new Error(`APIサーバーエラー: ${healthStatus.message}`);
      }
      
      setLoadingProgress(20);
      setLoadingMessage('土壌雨量指数を計算中... (最大2分程度かかります)');
      console.log('フルデータ計算を開始...');
      
      // 進行状況をシミュレート
      const progressInterval = setInterval(() => {
        setLoadingProgress(prev => {
          if (prev < 80) {
            return prev + 5;
          }
          return prev;
        });
      }, 2000);
      
      // データソースに基づいてAPI呼び出し
      let result;
      
      if (dataSource === 'test') {
        // テストデータを使用（時刻指定対応）
        console.log('テストデータソース: ローカルテストデータを使用します');
        const params = useSeparateTimes ? 
          { swi_initial: swiInitialTime, guid_initial: guidInitialTime } :
          { swi_initial: swiInitialTime };
        result = await apiClient_.testCalculationWithTime(params);
      } else {
        // 本番データを使用：気象庁サーバーから実際のGRIB2データを取得
        console.log('本番データソース: 気象庁GRIB2データを使用します');
        const initialTime = productionDateTime + 'Z';
        result = await apiClient_.calculateProductionSoilRainfallIndex({ 
          initial: initialTime 
        });
      }
      clearInterval(progressInterval);
      
      console.log('データ取得成功:', Object.keys(result.prefectures));
      
      setLoadingProgress(90);
      setLoadingMessage('データを処理中...');
      setData(result);
      
      // データ設定後に初期時刻を設定
      setTimeout(() => {
        const meshes: Mesh[] = [];
        Object.values(result.prefectures).forEach((prefecture: Prefecture) => {
          prefecture.areas.forEach((area: Area) => {
            area.meshes.forEach((mesh: Mesh) => {
              meshes.push(mesh);
            });
          });
        });
        
        if (meshes.length > 0) {
          const timeSet = new Set<number>();
          meshes.forEach(mesh => {
            mesh.swi_timeline.forEach(point => {
              timeSet.add(point.ft);
            });
          });
          const times = Array.from(timeSet).sort((a, b) => a - b);
          if (times.length > 0) {
            setSelectedTime(times[0]);
          }
        }
        setLoadingProgress(100);
        setLoadingMessage('完了');
      }, 100);
      
    } catch (err) {
      console.error('データ読み込みエラー:', err);
      if (err instanceof Error) {
        setError(`エラー: ${err.message}`);
      } else {
        setError('不明なエラーが発生しました');
      }
    } finally {
      setTimeout(() => {
        setLoading(false);
        setLoadingMessage('');
        setLoadingProgress(0);
      }, 500);
    }
  };

  // 初回データ読み込みは削除 - ユーザーが設定後に手動で読み込み

  // 利用可能時刻が変更された時のみ実行
  useEffect(() => {
    console.log('Dashboard: availableTimes更新', { availableTimes, selectedTime });
    if (availableTimes.length > 0) {
      // 現在選択されている時刻が利用可能時刻に含まれているかチェック
      setSelectedTime(prevTime => {
        if (!availableTimes.includes(prevTime)) {
          console.log('Dashboard: 時刻をリセット', { from: prevTime, to: availableTimes[0], availableTimes });
          return availableTimes[0];
        }
        return prevTime;
      });
    }
  }, [availableTimes]);

  // メッシュクリック時の処理
  const handleMeshClick = (mesh: Mesh) => {
    setSelectedMesh(mesh);
    
    // メッシュが所属する地域を検索
    if (data) {
      Object.values(data.prefectures).forEach((prefecture: Prefecture) => {
        prefecture.areas.forEach((area: Area) => {
          if (area.meshes.some(m => m.code === mesh.code)) {
            setSelectedArea(area);
          }
        });
      });
    }
  };

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontSize: '18px',
        gap: '20px'
      }}>
        <div style={{
          width: '60px',
          height: '60px',
          border: '6px solid #f3f3f3',
          borderTop: '6px solid #1976D2',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }} />
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '10px' }}>
            {loadingMessage || 'データを読み込んでいます...'}
          </div>
          <div style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>
            26,000+のメッシュデータを処理しています
          </div>
          <ProgressBar 
            progress={loadingProgress} 
            message="" 
            showPercentage={true}
          />
          <div style={{ 
            fontSize: '12px', 
            color: '#888', 
            marginTop: '10px'
          }}>
            初回読み込みには時間がかかる場合があります
          </div>
        </div>
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
      <div style={{ 
        padding: '20px', 
        textAlign: 'center',
        color: '#f44336'
      }}>
        <h2>エラーが発生しました</h2>
        <p>{error}</p>
        <button 
          onClick={loadData}
          style={{
            padding: '10px 20px',
            backgroundColor: '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          再読み込み
        </button>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ 
        padding: '20px', 
        textAlign: 'center'
      }}>
        <h2>土壌雨量指数計算システム</h2>
        
        {/* データソース・時刻設定UI */}
        <div style={{
          backgroundColor: '#f5f5f5',
          padding: '20px',
          borderRadius: '8px',
          margin: '20px 0',
          textAlign: 'left',
          maxWidth: '800px',
          marginLeft: 'auto',
          marginRight: 'auto'
        }}>
          <h3 style={{ marginTop: 0 }}>データソース・時刻設定</h3>
          
          {/* データソース選択 */}
          <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#e3f2fd', borderRadius: '6px' }}>
            <h4 style={{ marginTop: 0, marginBottom: '10px' }}>データソース</h4>
            <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
              <label style={{ display: 'flex', alignItems: 'center' }}>
                <input
                  type="radio"
                  name="dataSource"
                  value="test"
                  checked={dataSource === 'test'}
                  onChange={(e) => setDataSource(e.target.value as 'test' | 'production')}
                  style={{ marginRight: '8px' }}
                />
                <div>
                  <strong>テストデータ</strong>
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                    ローカルのサンプルデータ（高速・開発用）
                  </div>
                </div>
              </label>
              <label style={{ display: 'flex', alignItems: 'center' }}>
                <input
                  type="radio"
                  name="dataSource"
                  value="production"
                  checked={dataSource === 'production'}
                  onChange={(e) => setDataSource(e.target.value as 'test' | 'production')}
                  style={{ marginRight: '8px' }}
                />
                <div>
                  <strong>本番データ</strong>
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                    気象庁GRIB2サーバーから取得（実データ・時間要）
                  </div>
                </div>
              </label>
            </div>
          </div>
          
          {/* 時刻設定 - データソースに応じて表示 */}
          {dataSource === 'test' ? (
            /* テストデータ用の時刻設定 */
            <>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'flex', alignItems: 'center', marginBottom: '10px' }}>
                  <input
                    type="checkbox"
                    checked={useSeparateTimes}
                    onChange={(e) => setUseSeparateTimes(e.target.checked)}
                    style={{ marginRight: '8px' }}
                  />
                  SWIとガイダンスで異なる時刻を使用する
                </label>
              </div>
              
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: useSeparateTimes ? '1fr 1fr' : '1fr',
                gap: '15px' 
              }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                    {useSeparateTimes ? 'SWI初期時刻:' : '初期時刻:'}
                  </label>
                  <input
                    type="datetime-local"
                    value={swiInitialTime.replace('Z', '').replace('+00:00', '')}
                    onChange={(e) => setSwiInitialTime(e.target.value + 'Z')}
                    style={{
                      width: '100%',
                      padding: '8px',
                      border: '1px solid #ccc',
                      borderRadius: '4px'
                    }}
                  />
                </div>
                
                {useSeparateTimes && (
                  <div>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                      ガイダンス初期時刻:
                    </label>
                    <input
                      type="datetime-local"
                      value={guidInitialTime.replace('Z', '').replace('+00:00', '')}
                      onChange={(e) => setGuidInitialTime(e.target.value + 'Z')}
                      style={{
                        width: '100%',
                        padding: '8px',
                        border: '1px solid #ccc',
                        borderRadius: '4px'
                      }}
                    />
                  </div>
                )}
              </div>
            </>
          ) : (
            /* 本番データ用の時刻設定 */
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
                本番データ取得時刻:
              </label>
              <input
                type="datetime-local"
                value={productionDateTime}
                onChange={(e) => setProductionDateTime(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ccc',
                  borderRadius: '4px'
                }}
              />
              <div style={{ 
                fontSize: '12px', 
                color: '#666', 
                marginTop: '5px',
                backgroundColor: '#fff3cd',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #ffeaa7'
              }}>
                ⚠️ 気象庁のGRIB2データは6時間間隔（00, 06, 12, 18 UTC）で提供されます。<br />
                指定した時刻に最も近い利用可能な時刻のデータが使用されます。
              </div>
            </div>
          )}
        </div>
        
        <button 
          onClick={loadData}
          style={{
            padding: '10px 20px',
            backgroundColor: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          データを読み込む
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ textAlign: 'center', margin: '0', flex: 1 }}>
          土壌雨量指数計算システム
        </h1>
        
        {/* キーボードショートカット説明 */}
        <div style={{ 
          fontSize: '12px', 
          color: '#666', 
          textAlign: 'right',
          lineHeight: '1.4',
          border: '1px solid #ddd',
          padding: '8px',
          borderRadius: '4px',
          backgroundColor: '#f9f9f9'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>キーボード操作:</div>
          <div>↑↓ 都道府県切り替え</div>
          <div>←→ 時刻切り替え</div>
        </div>
      </div>
      
      {/* データ情報と再読み込み */}
      <div style={{ 
        backgroundColor: '#f5f5f5', 
        padding: '15px', 
        borderRadius: '8px',
        marginBottom: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        gap: '20px'
      }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ marginTop: 0 }}>データ情報</h3>
          <p><strong>データソース:</strong> {dataSource === 'test' ? 'テストデータ' : '本番データ（気象庁GRIB2）'}</p>
          <p><strong>計算時刻:</strong> {new Date(data.calculation_time).toLocaleString('ja-JP')}</p>
          {data.swi_initial_time && (
            <p><strong>SWI初期時刻:</strong> {new Date(data.swi_initial_time).toLocaleString('ja-JP')}</p>
          )}
          {data.guid_initial_time && (
            <p><strong>ガイダンス初期時刻:</strong> {new Date(data.guid_initial_time).toLocaleString('ja-JP')}</p>
          )}
          <p><strong>初期時刻:</strong> {new Date(data.initial_time).toLocaleString('ja-JP')}</p>
          <p><strong>メッシュ数:</strong> {allMeshes.length.toLocaleString()}個</p>
          <p><strong>対象地域:</strong> {Object.keys(data.prefectures).join(', ')}</p>
          {data.used_urls && (
            <div style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
              <p><strong>使用URLs:</strong></p>
              <div style={{ wordBreak: 'break-all', marginLeft: '10px' }}>
                • <strong>SWI URL:</strong> {data.used_urls.swi_url}
              </div>
              <div style={{ wordBreak: 'break-all', marginLeft: '10px' }}>
                • <strong>Guidance URL:</strong> {data.used_urls.guidance_url}
              </div>
            </div>
          )}
        </div>
        <div>
          <button 
            onClick={loadData}
            style={{
              padding: '10px 20px',
              backgroundColor: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              whiteSpace: 'nowrap'
            }}
          >
            データ再読み込み
          </button>
        </div>
      </div>

      {/* データ調査ツール */}
      <DataDownloader data={data} />

      {/* メッシュ分析 */}
      <MeshAnalyzer meshes={allMeshes} selectedTime={selectedTime} />

      {/* 時間スライダー */}
      <TimeSlider
        currentTime={selectedTime}
        timeRange={availableTimes}
        onTimeChange={handleTimeChange}
      />

      {/* 地図表示 */}
      <div style={{ marginBottom: '30px' }}>
        <h2>土壌雨量指数分布図</h2>
        <div style={{ 
          backgroundColor: '#e3f2fd', 
          padding: '15px', 
          borderRadius: '8px',
          marginBottom: '15px',
          border: '1px solid #bbdefb'
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '20px',
            flexWrap: 'wrap'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ 
                width: '12px', 
                height: '12px', 
                borderRadius: '2px', 
                backgroundColor: '#FFC107',
                border: '1px solid #333'
              }}></div>
              <span style={{ fontSize: '14px' }}>注意報</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ 
                width: '12px', 
                height: '12px', 
                borderRadius: '2px', 
                backgroundColor: '#FF9800',
                border: '1px solid #333'
              }}></div>
              <span style={{ fontSize: '14px' }}>警報</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <div style={{ 
                width: '12px', 
                height: '12px', 
                borderRadius: '2px', 
                backgroundColor: '#F44336',
                border: '1px solid #333'
              }}></div>
              <span style={{ fontSize: '14px' }}>土砂災害</span>
            </div>
            <span style={{ 
              fontSize: '13px', 
              color: '#666',
              marginLeft: 'auto'
            }}>
              ⚠️ 警戒レベルのみ表示（正常は非表示）
            </span>
          </div>
        </div>
        <SoilRainfallMap
          meshes={allMeshes}
          selectedTime={selectedTime}
          selectedPrefecture={selectedPrefecture}
          prefectureData={data.prefectures}
          onMeshClick={handleMeshClick}
          isLoading={isTimeChanging}
        />
      </div>

      {/* エリア別リスクレベルバーチャート */}
      {allAreas.length > 0 && (
        <div style={{ marginBottom: '30px' }}>
          <h2>エリア別リスクレベル分析</h2>
          <AreaRiskBarChart 
            prefectures={Object.values(data.prefectures)}
            selectedTime={selectedTime}
            selectedPrefecture={selectedPrefecture}
            onPrefectureChange={setSelectedPrefecture}
          />
        </div>
      )}

      {/* 選択された地域のリスク時系列 */}
      {selectedArea && (
        <div style={{ marginBottom: '30px' }}>
          <h2>地域リスク時系列: {selectedArea.name}</h2>
          <RiskTimelineChart 
            riskTimeline={selectedArea.risk_timeline}
            title={`${selectedArea.name} - リスクレベル時系列`}
          />
        </div>
      )}

      {/* 選択されたメッシュの詳細 */}
      {selectedMesh && (
        <div style={{ marginBottom: '30px' }}>
          <h2>メッシュ詳細: {selectedMesh.code}</h2>
          <SoilRainfallTimelineChart 
            mesh={selectedMesh}
          />
        </div>
      )}

      {/* フッター */}
      <div style={{ 
        textAlign: 'center', 
        marginTop: '40px',
        padding: '20px',
        backgroundColor: '#f5f5f5',
        borderRadius: '8px',
        fontSize: '14px',
        color: '#666'
      }}>
        <p>土壌雨量指数計算システム - 関西6府県対応</p>
        <p>リスクレベル: 0=正常, 1=注意, 2=警報, 3=土砂災害</p>
      </div>
    </div>
  );
};

export default SoilRainfallDashboard;
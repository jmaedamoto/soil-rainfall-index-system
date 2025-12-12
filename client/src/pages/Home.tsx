import React from 'react'
import { Link } from 'react-router-dom'

const Home: React.FC = () => {
  return (
    <div style={{ padding: '40px', textAlign: 'center', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '30px', color: '#1976D2' }}>
        土壌雨量指数計算システム
      </h1>
      
      <div style={{ 
        backgroundColor: '#f5f5f5', 
        padding: '30px', 
        borderRadius: '8px',
        marginBottom: '30px'
      }}>
        <h2>システム概要</h2>
        <p style={{ fontSize: '16px', lineHeight: '1.6' }}>
          関西6府県（滋賀・京都・大阪・兵庫・奈良・和歌山）の
          土壌雨量指数を計算し、リアルタイムで可視化するシステムです。
        </p>
        
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '20px',
          marginTop: '20px'
        }}>
          <div style={{ 
            backgroundColor: 'white', 
            padding: '20px', 
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ color: '#4CAF50' }}>🗺️ 地図表示</h3>
            <p>土壌雨量指数を時刻ごとに地図上で可視化</p>
          </div>
          
          <div style={{ 
            backgroundColor: 'white', 
            padding: '20px', 
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ color: '#FF9800' }}>📊 時系列表示</h3>
            <p>リスクレベルと土壌雨量指数の時系列グラフ</p>
          </div>
          
          <div style={{ 
            backgroundColor: 'white', 
            padding: '20px', 
            borderRadius: '8px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ color: '#F44336' }}>⚠️ リスク判定</h3>
            <p>注意・警報・土砂災害の4段階リスクレベル</p>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', flexWrap: 'wrap' }}>
        <Link
          to="/production"
          style={{
            display: 'inline-block',
            padding: '15px 30px',
            backgroundColor: '#2E7D32',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '8px',
            fontSize: '18px',
            fontWeight: 'bold',
            transition: 'background-color 0.3s'
          }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#1B5E20'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#2E7D32'}
        >
          本番運用画面
        </Link>

        <Link
          to="/production-session"
          style={{
            display: 'inline-block',
            padding: '15px 30px',
            backgroundColor: '#00897B',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '8px',
            fontSize: '18px',
            fontWeight: 'bold',
            transition: 'background-color 0.3s'
          }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#00695C'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#00897B'}
        >
          本番運用（セッション版）⚡
        </Link>

        <Link
          to="/dashboard"
          style={{
            display: 'inline-block',
            padding: '15px 30px',
            backgroundColor: '#1976D2',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '8px',
            fontSize: '18px',
            fontWeight: 'bold',
            transition: 'background-color 0.3s'
          }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#1565C0'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#1976D2'}
        >
          開発ダッシュボード
        </Link>

        <Link
          to="/rainfall-adjustment"
          style={{
            display: 'inline-block',
            padding: '15px 30px',
            backgroundColor: '#F57C00',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '8px',
            fontSize: '18px',
            fontWeight: 'bold',
            transition: 'background-color 0.3s'
          }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#EF6C00'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#F57C00'}
        >
          雨量予想調整
        </Link>
      </div>
      
      <div style={{ 
        marginTop: '40px',
        fontSize: '14px',
        color: '#666'
      }}>
        <p>対象地域: 26,000+メッシュ</p>
        <p>更新頻度: リアルタイム</p>
      </div>
    </div>
  )
}

export default Home
import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { Mesh, TimeSeriesPoint } from '../../types/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface SoilRainfallTimelineChartProps {
  mesh: Mesh;
  title?: string;
  height?: number;
}

const SoilRainfallTimelineChart: React.FC<SoilRainfallTimelineChartProps> = ({
  mesh,
  title,
  height = 400
}) => {
  // 土壌雨量指数データを時刻順にソート
  const sortedSwiData = [...mesh.swi_timeline].sort((a, b) => a.ft - b.ft);
  // 降水量データを時刻順にソート
  const sortedRainData = [...mesh.rain_timeline].sort((a, b) => a.ft - b.ft);

  // 全時刻のリストを作成
  const allTimes = Array.from(new Set([
    ...sortedSwiData.map(d => d.ft),
    ...sortedRainData.map(d => d.ft)
  ])).sort((a, b) => a - b);

  const chartData = {
    labels: allTimes.map(ft => ft === 0 ? '現在' : `FT${ft}h`),
    datasets: [
      {
        label: '土壌雨量指数',
        data: allTimes.map(ft => {
          const point = sortedSwiData.find(d => d.ft === ft);
          return point ? point.value : null;
        }),
        borderColor: '#1976D2',
        backgroundColor: 'rgba(25, 118, 210, 0.1)',
        borderWidth: 2,
        pointRadius: 4,
        pointBackgroundColor: '#1976D2',
        tension: 0.1,
        yAxisID: 'y'
      },
      {
        label: '降水量',
        data: allTimes.map(ft => {
          const point = sortedRainData.find(d => d.ft === ft);
          return point ? point.value : null;
        }),
        borderColor: '#00BCD4',
        backgroundColor: 'rgba(0, 188, 212, 0.1)',
        borderWidth: 2,
        pointRadius: 4,
        pointBackgroundColor: '#00BCD4',
        tension: 0.1,
        yAxisID: 'y1'
      }
    ]
  };

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: title || `メッシュ ${mesh.code} - 土壌雨量指数・降水量時系列`,
        font: {
          size: 16,
          weight: 'bold'
        }
      },
      tooltip: {
        callbacks: {
          afterBody: function(context) {
            const ftValue = allTimes[context[0].dataIndex];
            const swiPoint = sortedSwiData.find(d => d.ft === ftValue);
            if (swiPoint) {
              const { advisary_bound, warning_bound, dosyakei_bound } = mesh;
              let riskInfo = '';
              if (swiPoint.value >= dosyakei_bound) {
                riskInfo = '⚠️ 土砂災害警戒';
              } else if (swiPoint.value >= warning_bound) {
                riskInfo = '⚠️ 警報レベル';
              } else if (swiPoint.value >= advisary_bound) {
                riskInfo = '⚠️ 注意報レベル';
              } else {
                riskInfo = '✅ 正常レベル';
              }
              return [`基準値: 注意${advisary_bound} / 警報${warning_bound} / 土砂災害${dosyakei_bound}`, riskInfo];
            }
            return [];
          }
        }
      }
    },
    scales: {
      x: {
        title: {
          display: true,
          text: '時刻'
        }
      },
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        title: {
          display: true,
          text: '土壌雨量指数'
        },
        grid: {
          drawOnChartArea: false,
        },
      },
      y1: {
        type: 'linear',
        display: true,
        position: 'right',
        title: {
          display: true,
          text: '降水量 (mm/h)'
        },
        grid: {
          drawOnChartArea: false,
        },
      },
    }
  };

  return (
    <div style={{ height: `${height}px`, marginBottom: '20px' }}>
      <Line data={chartData} options={options} />
      
      {/* 基準値の表示 */}
      <div style={{ 
        marginTop: '10px', 
        padding: '10px', 
        backgroundColor: '#f5f5f5', 
        borderRadius: '4px',
        fontSize: '14px'
      }}>
        <strong>警戒基準値:</strong> 
        <span style={{ marginLeft: '10px', color: '#FFC107' }}>注意報: {mesh.advisary_bound}</span>
        <span style={{ marginLeft: '10px', color: '#FF9800' }}>警報: {mesh.warning_bound}</span>
        <span style={{ marginLeft: '10px', color: '#F44336' }}>土砂災害: {mesh.dosyakei_bound}</span>
      </div>
    </div>
  );
};

export default SoilRainfallTimelineChart;
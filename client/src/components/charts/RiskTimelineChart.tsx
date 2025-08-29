import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { RiskTimePoint, RISK_COLORS, RiskLevel, RISK_LABELS } from '../../types/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface RiskTimelineChartProps {
  riskTimeline: RiskTimePoint[];
  title?: string;
  height?: number;
}

const RiskTimelineChart: React.FC<RiskTimelineChartProps> = ({
  riskTimeline,
  title = 'リスクレベル時系列',
  height = 300
}) => {
  // データを時刻順にソート
  const sortedData = [...riskTimeline].sort((a, b) => a.ft - b.ft);

  // Chart.js用のデータを準備
  const chartData = {
    labels: sortedData.map(point => {
      return point.ft === 0 ? '現在' : `FT${point.ft}h`;
    }),
    datasets: [
      {
        label: 'リスクレベル',
        data: sortedData.map(point => point.value),
        borderColor: '#2196F3',
        backgroundColor: 'rgba(33, 150, 243, 0.1)',
        borderWidth: 2,
        pointRadius: 6,
        pointBackgroundColor: sortedData.map(point => RISK_COLORS[point.value as RiskLevel]),
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        tension: 0.1
      }
    ]
  };

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: title,
        font: {
          size: 16,
          weight: 'bold'
        }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const riskLevel = context.parsed.y as RiskLevel;
            const label = RISK_LABELS[riskLevel] || '不明';
            return `リスクレベル: ${riskLevel} (${label})`;
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
        title: {
          display: true,
          text: 'リスクレベル'
        },
        min: 0,
        max: 3,
        ticks: {
          stepSize: 1,
          callback: function(value) {
            const level = value as RiskLevel;
            return `${level}: ${RISK_LABELS[level] || ''}`;
          }
        }
      }
    }
  };

  return (
    <div style={{ height: `${height}px`, marginBottom: '20px' }}>
      <Line data={chartData} options={options} />
    </div>
  );
};

export default RiskTimelineChart;
import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  type ChartData,
  type ChartOptions,
} from 'chart.js';
import { Scatter } from 'react-chartjs-2';
import type { SnakeLineResponse } from '../../types/session';

ChartJS.register(LinearScale, PointElement, LineElement, Tooltip, Legend);

interface SnakeLineChartProps {
  data: SnakeLineResponse;
  initialTime?: string;
}

type SnakePoint = { x: number; y: number; ft?: number };

const formatForecastTime = (initialTime: string | undefined, ft: number | undefined) => {
  if (!initialTime || ft === undefined) return `FT+${ft ?? '?'}`;
  const time = new Date(new Date(initialTime).getTime() + ft * 60 * 60 * 1000 + 9 * 60 * 60 * 1000);
  return `${time.getUTCFullYear()}/${String(time.getUTCMonth() + 1).padStart(2, '0')}/${String(time.getUTCDate()).padStart(2, '0')} ${String(time.getUTCHours()).padStart(2, '0')}:00`;
};

const SnakeLineChart: React.FC<SnakeLineChartProps> = ({ data, initialTime }) => {
  const chartData = useMemo<ChartData<'scatter', SnakePoint[]>>(() => {
    const rainByFt = new Map(data.rain_1hour_timeline.map((point) => [point.ft, point.value]));
    const trajectory: SnakePoint[] = data.swi_hourly_timeline
      .flatMap((point) => {
        const rainfall = rainByFt.get(point.ft);
        return rainfall === undefined ? [] : [{ x: point.value, y: rainfall, ft: point.ft }];
      })
      .sort((a, b) => (a.ft ?? 0) - (b.ft ?? 0));

    const advisoryLine: SnakePoint[] = [
      { x: data.advisory_bound, y: 0 },
      { x: data.advisory_bound, y: 150 },
    ];
    const level4Line: SnakePoint[] = data.level4_curve
      ? data.level4_curve
          .map((swiThreshold, rainfall) => ({ x: swiThreshold, y: rainfall }))
          .filter((point) => Number.isFinite(point.x) && point.x >= 0 && point.x < 999)
      : data.dosyakei_bound === null
        ? []
        : [
            { x: data.dosyakei_bound, y: 0 },
            { x: data.dosyakei_bound, y: 150 },
          ];

    return {
      datasets: [
        {
          label: '時間変化（1時間ごと）',
          data: trajectory,
          showLine: true,
          borderColor: '#4f91d8',
          backgroundColor: '#4f91d8',
          borderWidth: 1.5,
          pointRadius: 2.5,
          pointHoverRadius: 5,
          order: 1,
        },
        {
          label: '注意報基準',
          data: advisoryLine,
          showLine: true,
          borderColor: '#e5b700',
          backgroundColor: '#e5b700',
          borderWidth: 2,
          pointRadius: 0,
          order: 2,
        },
        {
          label: '土砂災害警戒情報基準',
          data: level4Line,
          showLine: true,
          borderColor: '#9c27b0',
          backgroundColor: '#9c27b0',
          borderWidth: 2,
          pointRadius: 0,
          order: 3,
        },
      ],
    };
  }, [data]);

  const options = useMemo<ChartOptions<'scatter'>>(() => ({
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    parsing: false,
    scales: {
      x: {
        type: 'linear',
        title: { display: true, text: '土壌雨量指数 (mm)' },
        min: 0,
      },
      y: {
        type: 'linear',
        title: { display: true, text: '1時間雨量 (mm)' },
        min: 0,
        max: 150,
      },
    },
    plugins: {
      legend: { position: 'top' },
      tooltip: {
        callbacks: {
          title: (items) => {
            const point = items[0]?.raw as SnakePoint | undefined;
            return point?.ft === undefined ? '' : formatForecastTime(initialTime, point.ft);
          },
          label: (item) => {
            const point = item.raw as SnakePoint;
            return `${item.dataset.label}: SWI ${point.x.toFixed(1)} mm / 雨量 ${point.y.toFixed(1)} mm`;
          },
        },
      },
    },
  }), [initialTime]);

  return <Scatter data={chartData} options={options} />;
};

export default SnakeLineChart;

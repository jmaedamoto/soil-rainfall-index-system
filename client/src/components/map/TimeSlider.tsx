import React from 'react';

interface TimeSliderProps {
  currentTime: number;
  timeRange: number[];
  onTimeChange: (time: number) => void;
  disabled?: boolean;
}

const TimeSlider: React.FC<TimeSliderProps> = React.memo(({
  currentTime,
  timeRange,
  onTimeChange,
  disabled = false
}) => {
  const formatTime = (ft: number): string => {
    if (ft === 0) return '現在';
    return `FT${ft}h`;
  };

  // 利用可能時刻のインデックスベースでスライダーを操作
  const currentIndex = timeRange.indexOf(currentTime);
  const maxIndex = timeRange.length - 1;

  const handleIndexChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newIndex = parseInt(event.target.value);
    const newTime = timeRange[newIndex];
    onTimeChange(newTime);
  };

  return (
    <div style={{ 
      padding: '20px', 
      backgroundColor: '#f5f5f5', 
      borderRadius: '8px',
      margin: '10px 0'
    }}>
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '15px',
        marginBottom: '10px'
      }}>
        <label style={{ 
          fontWeight: 'bold',
          minWidth: '60px'
        }}>
          時刻:
        </label>
        <input
          type="range"
          min={0}
          max={maxIndex}
          value={currentIndex >= 0 ? currentIndex : 0}
          onChange={handleIndexChange}
          disabled={disabled || timeRange.length === 0}
          style={{
            flex: 1,
            height: '6px',
            backgroundColor: '#ddd',
            outline: 'none',
            borderRadius: '3px'
          }}
        />
        <span style={{ 
          fontWeight: 'bold',
          minWidth: '80px',
          color: '#333'
        }}>
          {formatTime(currentTime)}
        </span>
      </div>
      
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between',
        fontSize: '12px',
        color: '#666'
      }}>
        <span>{timeRange.length > 0 ? formatTime(timeRange[0]) : ''}</span>
        <span>{timeRange.length > 0 ? formatTime(timeRange[timeRange.length - 1]) : ''}</span>
      </div>
      
      {timeRange.length > 0 && (
        <div style={{ 
          marginTop: '10px',
          fontSize: '12px',
          color: '#666'
        }}>
          利用可能な時刻: {timeRange.map(t => formatTime(t)).join(', ')}
        </div>
      )}
    </div>
  );
});

export default TimeSlider;
import React from 'react';

interface ProgressBarProps {
  progress: number; // 0-100の進行率
  message?: string;
  showPercentage?: boolean;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ 
  progress, 
  message = '', 
  showPercentage = true 
}) => {
  return (
    <div style={{ width: '100%', maxWidth: '400px' }}>
      {message && (
        <div style={{ 
          marginBottom: '8px', 
          fontSize: '14px', 
          color: '#333',
          textAlign: 'center'
        }}>
          {message}
        </div>
      )}
      
      <div style={{
        width: '100%',
        height: '20px',
        backgroundColor: '#e0e0e0',
        borderRadius: '10px',
        overflow: 'hidden',
        position: 'relative'
      }}>
        <div
          style={{
            width: `${Math.min(100, Math.max(0, progress))}%`,
            height: '100%',
            backgroundColor: '#1976D2',
            borderRadius: '10px',
            transition: 'width 0.3s ease-in-out',
            background: 'linear-gradient(90deg, #1976D2 0%, #42A5F5 100%)'
          }}
        />
        
        {showPercentage && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: '12px',
            fontWeight: 'bold',
            color: progress > 50 ? 'white' : '#333',
            textShadow: progress > 50 ? '1px 1px 2px rgba(0,0,0,0.3)' : 'none'
          }}>
            {Math.round(progress)}%
          </div>
        )}
      </div>
    </div>
  );
};

export default ProgressBar;
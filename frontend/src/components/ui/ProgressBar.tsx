import React from 'react';

interface ProgressBarProps {
  progress: number; // 0-100
  label?: string;
  subLabel?: string;
  variant?: 'default' | 'success' | 'warning' | 'error';
  showPercentage?: boolean;
  animated?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  label,
  subLabel,
  variant = 'default',
  showPercentage = true,
  animated = true,
}) => {
  const getVariantClass = () => {
    switch (variant) {
      case 'success':
        return 'bg-green-500 dark:bg-green-600';
      case 'warning':
        return 'bg-yellow-500 dark:bg-yellow-600';
      case 'error':
        return 'bg-red-500 dark:bg-red-600';
      default:
        return 'bg-blue-500 dark:bg-blue-600';
    }
  };

  const clampedProgress = Math.min(Math.max(progress, 0), 100);

  return (
    <div className="w-full space-y-2">
      {(label || showPercentage) && (
        <div className="flex justify-between items-center text-sm">
          <span className="font-medium text-gray-700 dark:text-gray-300">
            {label || 'Progress'}
          </span>
          {showPercentage && (
            <span className="font-bold text-gray-900 dark:text-white">
              {clampedProgress.toFixed(0)}%
            </span>
          )}
        </div>
      )}
      
      <div className="relative w-full h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${getVariantClass()} ${
            animated ? 'transition-all duration-500 ease-out' : ''
          } rounded-full relative`}
          style={{ width: `${clampedProgress}%` }}
        >
          {animated && clampedProgress > 0 && clampedProgress < 100 && (
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
          )}
        </div>
      </div>
      
      {subLabel && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
          {subLabel}
        </p>
      )}
    </div>
  );
};

// Animation shimmer effect
const style = document.createElement('style');
style.textContent = `
  @keyframes shimmer {
    0% {
      transform: translateX(-100%);
    }
    100% {
      transform: translateX(100%);
    }
  }
  
  .animate-shimmer {
    animation: shimmer 2s infinite;
  }
`;
document.head.appendChild(style);

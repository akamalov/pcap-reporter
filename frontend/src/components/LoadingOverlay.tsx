'use client';

import React from 'react';
import { Spin, Typography } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface LoadingOverlayProps {
  /** Loading message to display */
  message?: string;
  /** Size of the spinner */
  size?: 'small' | 'default' | 'large';
  /** Whether to show as overlay (absolute positioned) */
  overlay?: boolean;
  /** Custom spinner icon */
  indicator?: React.ReactElement;
  /** Custom CSS class */
  className?: string;
  /** Minimum height for the loading area */
  minHeight?: number;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  message = "Loading...",
  size = "large",
  overlay = false,
  indicator,
  className = "",
  minHeight = 200
}) => {
  const defaultIndicator = <LoadingOutlined style={{ fontSize: size === 'large' ? 24 : size === 'default' ? 18 : 14 }} spin />;
  
  const containerClass = overlay 
    ? `absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm z-50 ${className}`
    : `flex items-center justify-center ${className}`;

  const contentStyle = overlay 
    ? undefined 
    : { minHeight: `${minHeight}px` };

  return (
    <div className={containerClass} style={contentStyle}>
      <div className="text-center">
        <Spin 
          size={size} 
          indicator={indicator || defaultIndicator}
          className="block mb-3"
        />
        {message && (
          <Text 
            type="secondary" 
            className="text-sm animate-pulse"
            aria-live="polite"
          >
            {message}
          </Text>
        )}
      </div>
    </div>
  );
};

interface LoadingSkeletonProps {
  /** Number of skeleton lines */
  lines?: number;
  /** Whether to show avatar skeleton */
  avatar?: boolean;
  /** Custom height for skeleton */
  height?: number;
  /** Whether skeleton is active (animated) */
  active?: boolean;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  lines = 3,
  avatar = false,
  height = 20,
  active = true
}) => {
  return (
    <div className="animate-pulse">
      <div className="flex space-x-4">
        {avatar && (
          <div className="rounded-full bg-gray-300 dark:bg-gray-600 h-12 w-12 flex-shrink-0"></div>
        )}
        <div className="flex-1 space-y-3">
          {Array.from({ length: lines }, (_, i) => (
            <div 
              key={i}
              className="bg-gray-300 dark:bg-gray-600 rounded"
              style={{ 
                height: `${height}px`,
                width: i === lines - 1 ? '75%' : '100%'
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

interface ChartSkeletonProps {
  /** Height of the chart skeleton */
  height?: number;
  /** Whether to show title skeleton */
  showTitle?: boolean;
  /** Whether to show legend skeleton */
  showLegend?: boolean;
}

export const ChartSkeleton: React.FC<ChartSkeletonProps> = ({
  height = 300,
  showTitle = true,
  showLegend = false
}) => {
  return (
    <div className="animate-pulse space-y-4">
      {showTitle && (
        <div className="h-6 bg-gray-300 dark:bg-gray-600 rounded w-1/3"></div>
      )}
      
      <div 
        className="bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center"
        style={{ height: `${height}px` }}
      >
        <div className="text-center">
          <div className="w-16 h-16 bg-gray-300 dark:bg-gray-600 rounded-full mx-auto mb-4"></div>
          <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-24 mx-auto"></div>
        </div>
      </div>
      
      {showLegend && (
        <div className="flex space-x-4 justify-center">
          {Array.from({ length: 3 }, (_, i) => (
            <div key={i} className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-gray-300 dark:bg-gray-600 rounded"></div>
              <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded w-16"></div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default LoadingOverlay;
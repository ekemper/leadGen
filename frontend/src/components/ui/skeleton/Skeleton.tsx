import React from 'react';

export interface SkeletonProps {
  height?: string | number;
  width?: string | number;
  borderRadius?: string | number;
  className?: string;
  animated?: boolean;
  variant?: 'text' | 'circular' | 'rectangular';
  lines?: number;
}

const Skeleton: React.FC<SkeletonProps> = ({
  height,
  width,
  borderRadius,
  className = '',
  animated = true,
  variant = 'rectangular',
  lines = 1,
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'text':
        return {
          height: height || '1em',
          width: width || '100%',
          borderRadius: borderRadius || '4px',
        };
      case 'circular':
        return {
          height: height || '40px',
          width: width || '40px',
          borderRadius: '50%',
        };
      case 'rectangular':
      default:
        return {
          height: height || '20px',
          width: width || '100%',
          borderRadius: borderRadius || '8px',
        };
    }
  };

  const baseStyles = getVariantStyles();

  const skeletonClass = `
    bg-gray-200 dark:bg-gray-700
    ${animated ? 'animate-pulse' : ''}
    ${className}
  `.trim();

  if (lines > 1 && variant === 'text') {
    return (
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={skeletonClass}
            style={{
              ...baseStyles,
              width: index === lines - 1 ? '75%' : baseStyles.width,
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={skeletonClass}
      style={baseStyles}
    />
  );
};

export default Skeleton; 
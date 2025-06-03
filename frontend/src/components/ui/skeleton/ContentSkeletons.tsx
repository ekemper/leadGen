import React from 'react';
import Skeleton from './Skeleton';

export const CampaignCardSkeleton: React.FC = () => (
  <div className="rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03] p-6">
    <div className="flex items-center justify-between mb-4">
      <Skeleton variant="text" width="60%" height="24px" />
      <Skeleton variant="rectangular" width="80px" height="24px" />
    </div>
    <Skeleton variant="text" lines={2} className="mb-4" />
    <div className="flex items-center justify-between">
      <Skeleton variant="text" width="40%" height="16px" />
      <Skeleton variant="text" width="30%" height="16px" />
    </div>
  </div>
);

export const CampaignDetailSkeleton: React.FC = () => (
  <div className="space-y-6">
    {/* Header */}
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div className="flex-1">
        <Skeleton variant="text" width="70%" height="32px" className="mb-2" />
        <div className="flex items-center gap-2 mb-2">
          <Skeleton variant="rectangular" width="80px" height="20px" />
          <Skeleton variant="text" width="100px" height="16px" />
        </div>
        <Skeleton variant="text" lines={2} />
      </div>
      <div className="flex gap-2">
        <Skeleton variant="rectangular" width="120px" height="40px" />
        <Skeleton variant="rectangular" width="100px" height="40px" />
      </div>
    </div>
    
    {/* Stats Cards */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
          <Skeleton variant="text" width="60%" height="16px" className="mb-2" />
          <Skeleton variant="text" width="40%" height="28px" />
        </div>
      ))}
    </div>
    
    {/* Table */}
    <div className="rounded-lg border border-gray-200 dark:border-gray-800">
      <div className="p-4 border-b border-gray-200 dark:border-gray-800">
        <Skeleton variant="text" width="30%" height="20px" />
      </div>
      <div className="p-4 space-y-4">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="flex items-center gap-4">
            <Skeleton variant="rectangular" width="100%" height="16px" />
          </div>
        ))}
      </div>
    </div>
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number; columns?: number }> = ({ 
  rows = 5, 
  columns = 4 
}) => (
  <div className="rounded-lg border border-gray-200 dark:border-gray-800">
    {/* Table Header */}
    <div className="p-4 border-b border-gray-200 dark:border-gray-800">
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={index} variant="text" width="80%" height="16px" />
        ))}
      </div>
    </div>
    
    {/* Table Body */}
    <div className="divide-y divide-gray-200 dark:divide-gray-800">
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="p-4">
          <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton key={colIndex} variant="text" width="90%" height="16px" />
            ))}
          </div>
        </div>
      ))}
    </div>
  </div>
);

export const FormSkeleton: React.FC<{ fields?: number }> = ({ fields = 4 }) => (
  <div className="space-y-6">
    {Array.from({ length: fields }).map((_, index) => (
      <div key={index}>
        <Skeleton variant="text" width="30%" height="16px" className="mb-2" />
        <Skeleton variant="rectangular" width="100%" height="40px" />
      </div>
    ))}
    <div className="flex gap-2 pt-4">
      <Skeleton variant="rectangular" width="100px" height="40px" />
      <Skeleton variant="rectangular" width="80px" height="40px" />
    </div>
  </div>
);

export const StatCardSkeleton: React.FC = () => (
  <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-6">
    <div className="flex items-center justify-between mb-4">
      <Skeleton variant="text" width="60%" height="16px" />
      <Skeleton variant="circular" width="32px" height="32px" />
    </div>
    <Skeleton variant="text" width="40%" height="32px" className="mb-2" />
    <Skeleton variant="text" width="80%" height="14px" />
  </div>
);

export const OrganizationCardSkeleton: React.FC = () => (
  <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-4">
    <div className="flex items-center justify-between mb-3">
      <Skeleton variant="text" width="60%" height="20px" />
      <Skeleton variant="rectangular" width="60px" height="24px" />
    </div>
    <Skeleton variant="text" lines={2} className="mb-3" />
    <div className="flex items-center gap-2">
      <Skeleton variant="text" width="30%" height="14px" />
      <Skeleton variant="text" width="40%" height="14px" />
    </div>
  </div>
); 
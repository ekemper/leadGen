import React from 'react';

interface TableCellProps {
  children: React.ReactNode;
  className?: string;
  isHeader?: boolean;
}

const TableCell: React.FC<TableCellProps> = ({ children, className = '', isHeader = false }) => {
  const Component = isHeader ? 'th' : 'td';
  return (
    <Component className={className}>
      {children}
    </Component>
  );
};

export default TableCell; 
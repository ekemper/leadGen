import React from 'react';

interface TableProps {
  children: React.ReactNode;
  className?: string;
}

const Table: React.FC<TableProps> = ({ children, className = '' }) => {
  return (
    <table className={`w-full ${className}`}>
      {children}
    </table>
  );
};

export default Table; 
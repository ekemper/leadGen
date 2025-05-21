import { ReactNode } from "react";
import React from "react";

// Props for Table
interface TableProps {
  children: ReactNode; // Table content (thead, tbody, etc.)
  className?: string; // Optional className for styling
}

// Props for TableHeader
interface TableHeaderProps {
  children: ReactNode; // Header row(s)
  className?: string; // Optional className for styling
}

// Props for TableBody
interface TableBodyProps {
  children: ReactNode; // Body row(s)
  className?: string; // Optional className for styling
}

// Props for TableRow
interface TableRowProps {
  children: ReactNode; // Cells (th or td)
  className?: string; // Optional className for styling
}

// Props for TableCell
interface TableCellProps {
  children: ReactNode; // Cell content
  isHeader?: boolean; // If true, renders as <th>, otherwise <td>
  className?: string; // Optional className for styling
}

/**
 * StripedTableBody
 *
 * A drop-in replacement for TableBody that automatically applies a striped background
 * to every other TableRow. Use it like:
 *
 * <Table>
 *   <TableHeader>...</TableHeader>
 *   <StripedTableBody>
 *     {rows.map((row, idx) => (
 *       <TableRow key={row.id}>...</TableRow>
 *     ))}
 *   </StripedTableBody>
 * </Table>
 */
interface StripedTableBodyProps {
  children: ReactNode[];
  className?: string;
  stripeClassName?: string; // Optional override for the striped row class
}

// Table Component
const Table: React.FC<TableProps> = ({ children, className }) => {
  return <table className={`min-w-full  ${className}`}>{children}</table>;
};

// TableHeader Component
const TableHeader: React.FC<TableHeaderProps> = ({ children, className }) => {
  return <thead className={className}>{children}</thead>;
};

// TableBody Component
const TableBody: React.FC<TableBodyProps> = ({ children, className }) => {
  return <tbody className={className}>{children}</tbody>;
};

// TableRow Component
const TableRow: React.FC<TableRowProps> = ({ children, className }) => {
  return <tr className={className}>{children}</tr>;
};

// TableCell Component
const TableCell: React.FC<TableCellProps> = ({
  children,
  isHeader = false,
  className,
}) => {
  const CellTag = isHeader ? "th" : "td";
  return <CellTag className={` ${className}`}>{children}</CellTag>;
};

const StripedTableBody: React.FC<StripedTableBodyProps> = ({ children, className = '', stripeClassName = 'bg-gray-50 dark:bg-white/[0.02]' }) => {
  // Ensure children is an array
  const rows = Array.isArray(children) ? children : [children];
  return (
    <tbody className={className}>
      {rows.map((child, idx) => {
        if (!child) return null;
        // Only apply to TableRow elements
        if (typeof child === 'object' && child !== null && 'type' in child && (child as any).type?.displayName === 'TableRow') {
          return React.cloneElement(child as any, {
            className: `${(child as any).props.className || ''} ${idx % 2 === 1 ? stripeClassName : ''}`.trim(),
          });
        }
        // Fallback: just render
        return idx % 2 === 1
          ? <tr className={stripeClassName}>{child}</tr>
          : <tr>{child}</tr>;
      })}
    </tbody>
  );
};

// Set displayName for TableRow for detection
TableRow.displayName = 'TableRow';

export { Table, TableHeader, TableBody, TableRow, TableCell, StripedTableBody };

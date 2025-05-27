import React from 'react';
import PropTypes from 'prop-types';
import { Skeleton, TableRow, TableCell } from '@mui/material';

function TableSkeleton({ rows = 5, columns = 4 }) {
  return (
    <>
      {Array.from(new Array(rows)).map((_, index) => (
        <TableRow key={index}>
          {Array.from(new Array(columns)).map((_, cellIndex) => (
            <TableCell key={cellIndex}>
              <Skeleton 
                animation="wave" 
                width={cellIndex === 0 ? '60%' : '40%'} 
                height={24}
              />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

TableSkeleton.propTypes = {
  rows: PropTypes.number,
  columns: PropTypes.number,
};

export default TableSkeleton;

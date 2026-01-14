import React from 'react';
import PropTypes from 'prop-types';
import './TableSkeleton.css';

function TableSkeleton({ rows = 5, columns = 4 }) {
  return (
    <>
      {Array.from(new Array(rows)).map((_, index) => (
        <tr key={index} className="skeleton-row">
          {Array.from(new Array(columns)).map((_, cellIndex) => (
            <td key={cellIndex}>
              <div
                className="skeleton-loader"
                style={{
                  width: cellIndex === 0 ? '60%' : '40%',
                  height: '20px',
                }}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

TableSkeleton.propTypes = {
  rows: PropTypes.number,
  columns: PropTypes.number,
};

export default TableSkeleton;

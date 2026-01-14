import React, { useEffect, useState } from 'react';
import API from 'api/apiClient';
import '../styles/RunHistoryModal.css';

const RunHistoryModal = ({ open, onClose }) => {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (open) {
      API.getRunHistory().then(setHistory).catch(console.error);
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Recent Discovery Runs</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="modal-body">
          <table className="table">
            <thead>
              <tr>
                <th>Started</th>
                <th>Status</th>
                <th>Stored/Total</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan="3" style={{ textAlign: 'center', padding: '24px' }}>
                    No history available
                  </td>
                </tr>
              ) : (
                history.map((h, i) => (
                  <tr key={i}>
                    <td>{new Date(h.start).toLocaleString()}</td>
                    <td>{h.status}</td>
                    <td>{h.stored ?? '-'} / {h.total ?? '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default RunHistoryModal;

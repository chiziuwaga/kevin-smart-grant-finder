import React, { useState, useEffect } from 'react';
import API from '../api/apiClient';
import '../styles/swiss-theme.css';

const ApplicationsPage = () => {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [selectedApplication, setSelectedApplication] = useState(null);
  const [grants, setGrants] = useState([]);
  const [selectedGrant, setSelectedGrant] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [message, setMessage] = useState({ text: '', type: '' });

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 3000);
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  const fetchApplications = async () => {
    try {
      setLoading(true);
      const response = await API.getApplications();
      const items = response.items || response.data || response || [];
      setApplications(Array.isArray(items) ? items : []);
    } catch (error) {
      console.error('Failed to fetch applications:', error);
      showMessage('Failed to fetch applications', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchGrants = async () => {
    try {
      const response = await API.getGrants({ limit: 50 });
      setGrants(response.items || []);
    } catch (error) {
      console.error('Failed to fetch grants:', error);
      showMessage('Failed to fetch grants', 'error');
    }
  };

  const handleOpenGenerateModal = () => {
    fetchGrants();
    setGenerateModalOpen(true);
  };

  const handleCloseGenerateModal = () => {
    setGenerateModalOpen(false);
    setSelectedGrant('');
    setGenerationProgress(0);
  };

  const handleGenerate = async () => {
    if (!selectedGrant) {
      showMessage('Please select a grant', 'error');
      return;
    }

    setGenerating(true);
    setGenerationProgress(0);

    try {
      // Show progress indicator
      const interval = setInterval(() => {
        setGenerationProgress(prev => {
          if (prev >= 90) {
            clearInterval(interval);
            return 90;
          }
          return prev + 10;
        });
      }, 1000);

      await API.generateApplication(selectedGrant);
      clearInterval(interval);
      setGenerationProgress(100);

      showMessage('Application generated successfully!', 'success');
      handleCloseGenerateModal();
      fetchApplications();
    } catch (error) {
      console.error('Failed to generate application:', error);
      showMessage('Failed to generate application', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const handleView = (application) => {
    setSelectedApplication(application);
    setViewModalOpen(true);
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p className="mt-2">Loading applications...</p>
      </div>
    );
  }

  return (
    <div className="container" style={{ padding: 'var(--space-3)' }}>
      <div className="flex justify-between items-center mb-3">
        <h1>Grant Applications</h1>
        <button className="btn btn-primary" onClick={handleOpenGenerateModal}>
          ➕ Generate New Application
        </button>
      </div>

      {message.text && (
        <div className={`alert alert-${message.type} mb-3`}>
          {message.text}
        </div>
      )}

      {applications.length > 0 ? (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Grant Title</th>
                <th>Created</th>
                <th>Status</th>
                <th>Sections</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {applications.map(app => (
                <tr key={app.id}>
                  <td style={{ fontWeight: '600' }}>{app.grant_title || app.grantTitle}</td>
                  <td>{new Date(app.created_at || app.createdAt).toLocaleDateString()}</td>
                  <td>
                    <span className={`chip chip-${(app.status || '').toLowerCase() === 'completed' ? 'success' : 'warning'}`}>
                      {app.status}
                    </span>
                  </td>
                  <td>{(app.sections || []).length} sections</td>
                  <td>
                    <button className="btn btn-sm btn-text" onClick={() => handleView(app)}>
                      👁️ View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <div style={{ fontSize: '3rem', marginBottom: 'var(--space-2)' }}>📄</div>
          <p>No applications yet</p>
          <button className="btn btn-primary mt-3" onClick={handleOpenGenerateModal}>
            Generate Your First Application
          </button>
        </div>
      )}

      {/* Generate Modal */}
      {generateModalOpen && (
        <div className="modal-backdrop" onClick={handleCloseGenerateModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Generate Application</h3>
              <button className="modal-close" onClick={handleCloseGenerateModal}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="label">Select Grant</label>
                <select
                  className="input"
                  value={selectedGrant}
                  onChange={(e) => setSelectedGrant(e.target.value)}
                >
                  <option value="">Choose a grant...</option>
                  {grants.map(grant => (
                    <option key={grant.id} value={grant.id}>
                      {grant.title}
                    </option>
                  ))}
                </select>
              </div>

              {generating && (
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm">Generating application...</span>
                    <span className="text-sm">{generationProgress}%</span>
                  </div>
                  <div className="progress">
                    <div className="progress-bar" style={{ width: `${generationProgress}%` }}></div>
                  </div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={handleCloseGenerateModal} disabled={generating}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleGenerate} disabled={generating || !selectedGrant}>
                {generating ? 'Generating...' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Modal */}
      {viewModalOpen && selectedApplication && (
        <div className="modal-backdrop" onClick={() => setViewModalOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px' }}>
            <div className="modal-header">
              <h3 className="modal-title">{selectedApplication.grant_title || selectedApplication.grantTitle}</h3>
              <button className="modal-close" onClick={() => setViewModalOpen(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="mb-3">
                <strong>Status:</strong> <span className={`chip chip-${selectedApplication.status === 'Completed' ? 'success' : 'warning'}`}>
                  {selectedApplication.status}
                </span>
              </div>
              <div className="mb-3">
                <strong>Created:</strong> {new Date(selectedApplication.created_at || selectedApplication.createdAt).toLocaleDateString()}
              </div>
              <div>
                <strong>Sections:</strong>
                <ul style={{ marginTop: 'var(--space-1)', paddingLeft: 'var(--space-3)' }}>
                  {(selectedApplication.sections || []).map((section, idx) => (
                    <li key={idx}>{section}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setViewModalOpen(false)}>
                Close
              </button>
              <button className="btn btn-primary">
                📥 Export PDF
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApplicationsPage;

import React, { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import API from '../api/apiClient';
import '../styles/swiss-theme.css';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ACCEPTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
};

const BusinessProfilePage = () => {
  const [profile, setProfile] = useState({
    businessName: '',
    industry: '',
    location: '',
    websiteUrl: '',
    description: '',
    yearsInBusiness: '',
    employeeCount: '',
    annualRevenue: '',
  });
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [totalSize, setTotalSize] = useState(0);
  const [characterCount, setCharacterCount] = useState(0);
  const [hasChanges, setHasChanges] = useState(false);

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 3000);
  };

  useEffect(() => {
    fetchProfile();
    fetchDocuments();
  }, []);

  const fetchProfile = async () => {
    try {
      // TODO: Replace with actual API call
      // const data = await API.getBusinessProfile();
      // setProfile(data);
    } catch (error) {
      console.error('Failed to fetch profile:', error);
    }
  };

  const fetchDocuments = async () => {
    try {
      // TODO: Replace with actual API call
      // const data = await API.getDocuments();
      // setDocuments(data);
      // calculateTotalSize(data);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };

  const calculateTotalSize = (docs) => {
    const total = docs.reduce((acc, doc) => acc + doc.size, 0);
    setTotalSize(total);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setProfile((prev) => ({ ...prev, [name]: value }));
    setHasChanges(true);

    if (name === 'description') {
      setCharacterCount(value.length);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // TODO: Replace with actual API call
      // await API.updateBusinessProfile(profile);
      showMessage('Profile saved successfully!', 'success');
      setHasChanges(false);
    } catch (error) {
      console.error('Failed to save profile:', error);
      showMessage('Failed to save profile', 'error');
    } finally {
      setSaving(false);
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    const validFiles = acceptedFiles.filter(file => {
      if (file.size > MAX_FILE_SIZE) {
        showMessage(`File ${file.name} is too large (max 10MB)`, 'error');
        return false;
      }
      return true;
    });

    if (validFiles.length === 0) return;

    setUploading(true);
    setUploadProgress(0);

    try {
      // Simulate upload progress
      const interval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(interval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // TODO: Replace with actual API call
      // await API.uploadDocuments(validFiles);
      await new Promise(resolve => setTimeout(resolve, 2000));
      clearInterval(interval);
      setUploadProgress(100);

      showMessage(`Successfully uploaded ${validFiles.length} file(s)`, 'success');
      fetchDocuments();
    } catch (error) {
      console.error('Upload failed:', error);
      showMessage('Failed to upload files', 'error');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_FILE_TYPES,
    maxSize: MAX_FILE_SIZE,
  });

  const handleDeleteDocument = async (docId) => {
    try {
      // TODO: Replace with actual API call
      // await API.deleteDocument(docId);
      setDocuments(prev => prev.filter(doc => doc.id !== docId));
      showMessage('Document deleted successfully', 'success');
    } catch (error) {
      console.error('Failed to delete document:', error);
      showMessage('Failed to delete document', 'error');
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="container" style={{ padding: 'var(--space-3)' }}>
      <h1 className="mb-3">Business Profile</h1>

      {message.text && (
        <div className={`alert alert-${message.type} mb-3`}>
          {message.text}
        </div>
      )}

      <div className="card mb-4">
        <h2>Business Information</h2>

        <div className="grid grid-cols-2 gap-3">
          <div className="form-group">
            <label className="label">Business Name *</label>
            <input
              type="text"
              name="businessName"
              className="input"
              value={profile.businessName}
              onChange={handleInputChange}
              placeholder="Your Business Name"
            />
          </div>

          <div className="form-group">
            <label className="label">Industry *</label>
            <input
              type="text"
              name="industry"
              className="input"
              value={profile.industry}
              onChange={handleInputChange}
              placeholder="e.g., Technology, Healthcare"
            />
          </div>

          <div className="form-group">
            <label className="label">Location</label>
            <input
              type="text"
              name="location"
              className="input"
              value={profile.location}
              onChange={handleInputChange}
              placeholder="City, State"
            />
          </div>

          <div className="form-group">
            <label className="label">Website URL</label>
            <input
              type="url"
              name="websiteUrl"
              className="input"
              value={profile.websiteUrl}
              onChange={handleInputChange}
              placeholder="https://example.com"
            />
          </div>

          <div className="form-group">
            <label className="label">Years in Business</label>
            <input
              type="number"
              name="yearsInBusiness"
              className="input"
              value={profile.yearsInBusiness}
              onChange={handleInputChange}
              placeholder="0"
              min="0"
            />
          </div>

          <div className="form-group">
            <label className="label">Employee Count</label>
            <input
              type="number"
              name="employeeCount"
              className="input"
              value={profile.employeeCount}
              onChange={handleInputChange}
              placeholder="0"
              min="0"
            />
          </div>

          <div className="form-group">
            <label className="label">Annual Revenue</label>
            <input
              type="text"
              name="annualRevenue"
              className="input"
              value={profile.annualRevenue}
              onChange={handleInputChange}
              placeholder="$0 - $100,000"
            />
          </div>
        </div>

        <div className="form-group">
          <label className="label">Business Description ({characterCount} / 1000 characters)</label>
          <textarea
            name="description"
            className="input"
            rows="6"
            value={profile.description}
            onChange={handleInputChange}
            placeholder="Describe your business, mission, and what makes you unique..."
            maxLength="1000"
          />
        </div>

        {hasChanges && (
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : '💾 Save Profile'}
          </button>
        )}
      </div>

      <div className="card">
        <h2>Supporting Documents</h2>
        <p className="text-sm text-secondary mb-3">
          Upload documents that support your grant applications (PDF, DOCX, TXT - Max 10MB each)
        </p>

        <div
          {...getRootProps()}
          style={{
            border: '2px dashed var(--border-color)',
            borderRadius: 'var(--border-radius)',
            padding: 'var(--space-4)',
            textAlign: 'center',
            cursor: 'pointer',
            backgroundColor: isDragActive ? 'var(--color-gray-50)' : 'transparent',
            marginBottom: 'var(--space-3)'
          }}
        >
          <input {...getInputProps()} />
          <div style={{ fontSize: '3rem', marginBottom: 'var(--space-2)' }}>📁</div>
          {isDragActive ? (
            <p>Drop files here...</p>
          ) : (
            <div>
              <p>Drag and drop files here, or click to select</p>
              <p className="text-sm text-secondary mt-1">PDF, DOCX, TXT - Max 10MB per file</p>
            </div>
          )}
        </div>

        {uploading && (
          <div className="mb-3">
            <div className="flex justify-between mb-1">
              <span className="text-sm">Uploading...</span>
              <span className="text-sm">{uploadProgress}%</span>
            </div>
            <div className="progress">
              <div className="progress-bar" style={{ width: `${uploadProgress}%` }}></div>
            </div>
          </div>
        )}

        {documents.length > 0 ? (
          <div>
            <div className="flex justify-between items-center mb-2">
              <h3>Uploaded Documents ({documents.length})</h3>
              <span className="text-sm text-secondary">Total: {formatFileSize(totalSize)}</span>
            </div>
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Uploaded</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map(doc => (
                    <tr key={doc.id}>
                      <td>
                        <div className="flex items-center gap-2">
                          <span>📄</span>
                          <span>{doc.name}</span>
                        </div>
                      </td>
                      <td>{formatFileSize(doc.size)}</td>
                      <td>{new Date(doc.uploadedAt).toLocaleDateString()}</td>
                      <td>
                        <button
                          className="btn btn-sm btn-text"
                          onClick={() => handleDeleteDocument(doc.id)}
                          style={{ color: '#E53935' }}
                        >
                          🗑️ Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <p>No documents uploaded yet</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default BusinessProfilePage;

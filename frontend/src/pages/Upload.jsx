import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const Upload = () => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError('');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      setError('');
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/ingest', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setSuccess(`File uploaded successfully! Dataset ID: ${response.data.dataset_id}`);
      setFile(null);

      // Redirect to dataset detail after 2 seconds
      setTimeout(() => {
        navigate(`/datasets/${response.data.dataset_id}`);
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Upload Health Data</h1>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
        <h2 className="text-lg font-semibold text-blue-900 mb-2">Supported Formats</h2>
        <p className="text-blue-800 mb-4">
          We accept CSV, JSON, HL7, and FHIR files. Your data will be automatically normalized
          to our Medical Data Format (MDF) and de-identified according to HIPAA Safe Harbor standards.
        </p>
        <ul className="list-disc list-inside text-blue-800 space-y-1">
          <li>Maximum file size: 100MB</li>
          <li>All data is encrypted in transit and at rest</li>
          <li>You maintain full ownership and control</li>
        </ul>
      </div>

      {/* Upload Area */}
      <div className="bg-white p-8 rounded-lg shadow">
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-500 transition cursor-pointer"
          onClick={() => document.getElementById('fileInput').click()}
        >
          {file ? (
            <div>
              <svg className="mx-auto h-12 w-12 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="mt-4 text-lg font-semibold text-gray-900">{file.name}</p>
              <p className="text-gray-600">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
          ) : (
            <div>
              <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="mt-4 text-lg text-gray-600">
                Drag and drop your file here, or click to browse
              </p>
              <p className="text-sm text-gray-500 mt-2">CSV, JSON, HL7, FHIR (Max 100MB)</p>
            </div>
          )}
        </div>

        <input
          id="fileInput"
          type="file"
          onChange={handleFileChange}
          className="hidden"
          accept=".csv,.json,.hl7,.txt"
        />

        {error && (
          <div className="mt-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {success && (
          <div className="mt-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
            {success}
          </div>
        )}

        <div className="mt-6 flex justify-end space-x-4">
          <button
            onClick={() => setFile(null)}
            disabled={!file || uploading}
            className="px-6 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Clear
          </button>
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400 font-semibold"
          >
            {uploading ? 'Uploading...' : 'Upload File'}
          </button>
        </div>
      </div>

      {/* Consent Notice */}
      <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <h3 className="font-semibold text-yellow-900 mb-2">Data Usage Consent</h3>
        <p className="text-yellow-800 text-sm">
          By uploading data, you acknowledge that you own this data and consent to its normalization
          and de-identification. You can choose to make your data available for sale in the marketplace
          at any time. All data sales require explicit consent and you maintain the right to revoke
          access at any time.
        </p>
      </div>
    </div>
  );
};

export default Upload;

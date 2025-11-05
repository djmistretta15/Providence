import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import api from '../services/api';

const DatasetDetail = () => {
  const { id } = useParams();
  const [dataset, setDataset] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDataset();
  }, [id]);

  const fetchDataset = async () => {
    try {
      const response = await api.get(`/datasets/${id}`);
      setDataset(response.data);
    } catch (error) {
      console.error('Failed to fetch dataset:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center">Loading...</div>;
  }

  if (!dataset) {
    return <div className="p-8 text-center">Dataset not found</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">{dataset.filename}</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Dataset Info */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-bold mb-4">Dataset Information</h2>
          <dl className="space-y-3">
            <div>
              <dt className="text-sm text-gray-600">Status</dt>
              <dd className="font-semibold">{dataset.status}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-600">Total Records</dt>
              <dd className="font-semibold">{dataset.total_records || 'N/A'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-600">Normalized Records</dt>
              <dd className="font-semibold">{dataset.normalized_records || 'N/A'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-600">Confidence Score</dt>
              <dd className="font-semibold">
                {dataset.confidence_score ? `${(dataset.confidence_score * 100).toFixed(1)}%` : 'N/A'}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-gray-600">Uploaded</dt>
              <dd className="font-semibold">{new Date(dataset.created_at).toLocaleDateString()}</dd>
            </div>
          </dl>
        </div>

        {/* Field Mappings */}
        {dataset.field_mappings && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-bold mb-4">Field Mappings</h2>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {Object.entries(dataset.field_mappings).map(([source, target]) => (
                <div key={source} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                  <span className="text-sm text-gray-600">{source}</span>
                  <span className="text-sm font-semibold text-blue-600">→ {target}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DatasetDetail;

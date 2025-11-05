import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, datasetsRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/datasets')
      ]);
      setStats(statsRes.data);
      setDatasets(datasetsRes.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center">Loading...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.full_name || user?.email}!
        </h1>
        <p className="text-gray-600 mt-2">Manage your health data and track earnings</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-600">Total Datasets</div>
          <div className="text-3xl font-bold text-blue-600">{stats?.total_datasets || 0}</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-600">Normalized</div>
          <div className="text-3xl font-bold text-green-600">{stats?.normalized_datasets || 0}</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-600">Total Records</div>
          <div className="text-3xl font-bold text-purple-600">{stats?.total_records_processed || 0}</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-600">Total Earnings</div>
          <div className="text-3xl font-bold text-green-600">${stats?.total_earnings?.toFixed(2) || '0.00'}</div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white p-6 rounded-lg shadow mb-8">
        <h2 className="text-xl font-bold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/upload"
            className="bg-blue-600 text-white px-6 py-3 rounded text-center hover:bg-blue-700 font-semibold"
          >
            Upload New Dataset
          </Link>
          <Link
            to="/marketplace"
            className="bg-green-600 text-white px-6 py-3 rounded text-center hover:bg-green-700 font-semibold"
          >
            Browse Marketplace
          </Link>
          <Link
            to="/earnings"
            className="bg-purple-600 text-white px-6 py-3 rounded text-center hover:bg-purple-700 font-semibold"
          >
            View Earnings
          </Link>
        </div>
      </div>

      {/* Recent Datasets */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-bold mb-4">Your Datasets</h2>
        {datasets.length === 0 ? (
          <p className="text-gray-600">No datasets yet. Upload your first dataset to get started!</p>
        ) : (
          <div className="space-y-4">
            {datasets.slice(0, 10).map((dataset) => (
              <Link
                key={dataset.id}
                to={`/datasets/${dataset.id}`}
                className="block p-4 border border-gray-200 rounded hover:bg-gray-50 transition"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-gray-900">{dataset.filename}</h3>
                    <p className="text-sm text-gray-600">
                      {dataset.total_records || 0} records • {dataset.status}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className={`px-3 py-1 rounded text-sm font-semibold ${
                      dataset.status === 'normalized' ? 'bg-green-100 text-green-800' :
                      dataset.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                      dataset.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {dataset.status}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;

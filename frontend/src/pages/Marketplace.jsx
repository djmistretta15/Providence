import React, { useState, useEffect } from 'react';
import api from '../services/api';

const Marketplace = () => {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchListings();
  }, []);

  const fetchListings = async () => {
    try {
      const response = await api.get('/marketplace/listings');
      setListings(response.data);
    } catch (error) {
      console.error('Failed to fetch listings:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center">Loading marketplace...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Data Marketplace</h1>

      {listings.length === 0 ? (
        <div className="bg-white p-8 rounded-lg shadow text-center">
          <p className="text-gray-600">No datasets available for purchase at this time.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {listings.map((listing) => (
            <div key={listing.dataset_id} className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition">
              <h3 className="font-bold text-lg mb-2">{listing.filename}</h3>
              <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                {listing.description || 'No description available'}
              </p>
              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Records:</span>
                  <span className="font-semibold">{listing.total_records}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Quality:</span>
                  <span className="font-semibold">
                    {listing.confidence_score ? `${(listing.confidence_score * 100).toFixed(0)}%` : 'N/A'}
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center pt-4 border-t">
                <span className="text-2xl font-bold text-green-600">${listing.price?.toFixed(2)}</span>
                <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                  Purchase
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Marketplace;

import React from 'react';
import { useAuth } from '../context/AuthContext';

const Profile = () => {
  const { user } = useAuth();

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Profile</h1>

      <div className="bg-white p-6 rounded-lg shadow">
        <dl className="space-y-4">
          <div>
            <dt className="text-sm text-gray-600">Email</dt>
            <dd className="font-semibold text-lg">{user?.email}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-600">Full Name</dt>
            <dd className="font-semibold">{user?.full_name || 'Not set'}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-600">Role</dt>
            <dd className="font-semibold capitalize">{user?.role}</dd>
          </div>
          <div>
            <dt className="text-sm text-gray-600">Total Earnings</dt>
            <dd className="font-semibold text-green-600 text-xl">
              ${user?.total_earnings?.toFixed(2) || '0.00'}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-gray-600">Member Since</dt>
            <dd className="font-semibold">{new Date(user?.created_at).toLocaleDateString()}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
};

export default Profile;

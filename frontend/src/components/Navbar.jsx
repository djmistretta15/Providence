import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-blue-600 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link to="/dashboard" className="text-2xl font-bold">
              Mist Data Steward
            </Link>

            <div className="hidden md:flex space-x-4">
              <Link to="/dashboard" className="hover:bg-blue-700 px-3 py-2 rounded">
                Dashboard
              </Link>
              <Link to="/upload" className="hover:bg-blue-700 px-3 py-2 rounded">
                Upload
              </Link>
              <Link to="/marketplace" className="hover:bg-blue-700 px-3 py-2 rounded">
                Marketplace
              </Link>
              {user?.role === 'patient' && (
                <Link to="/earnings" className="hover:bg-blue-700 px-3 py-2 rounded">
                  Earnings
                </Link>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-sm">{user?.email}</span>
            <Link to="/profile" className="hover:bg-blue-700 px-3 py-2 rounded">
              Profile
            </Link>
            <button
              onClick={handleLogout}
              className="bg-blue-800 hover:bg-blue-900 px-4 py-2 rounded"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;

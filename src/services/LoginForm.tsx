'use client';

import React, { useState, useEffect } from 'react';
import { wsService } from '@/services/websocket';

interface LoginFormProps {
  onLoginSuccess?: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('supersecret');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [authStatus, setAuthStatus] = useState(wsService.getAuthStatus());

  useEffect(() => {
    // Periodically check auth status in case it changes in another tab
    const interval = setInterval(() => {
      setAuthStatus(wsService.getAuthStatus());
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      await wsService.loginAndConnect(username, password);
      setAuthStatus(wsService.getAuthStatus());
      onLoginSuccess?.();
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    await wsService.logout();
    setAuthStatus(wsService.getAuthStatus());
  };

  if (authStatus.isAuthenticated) {
    return (
      <div className="p-4 bg-green-50 border border-green-200 rounded">
        <p className="text-green-800">
          Logged in as: {authStatus.user?.username || 'Unknown'}
        </p>
        <button
          onClick={handleLogout}
          className="mt-2 px-3 py-1 bg-red-500 text-white rounded text-sm"
        >
          Logout
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleLogin} className="p-4 bg-yellow-50 border border-yellow-200 rounded">
      <h3 className="text-lg font-semibold mb-3">Authentication Required</h3>
      <div className="space-y-3">
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="w-full p-2 border rounded"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full p-2 border rounded"
          required
        />
        {error && (
          <p className="text-red-600 text-sm">{error}</p>
        )}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full p-2 bg-blue-500 text-white rounded disabled:opacity-50"
        >
          {isLoading ? 'Logging in...' : 'Login'}
        </button>
      </div>
    </form>
  );
};

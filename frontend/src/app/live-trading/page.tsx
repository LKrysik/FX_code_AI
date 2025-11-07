/**
 * Live Trading Page - Agent 6
 * =============================
 * Modern 3-panel trading workspace with real-time updates.
 *
 * Layout:
 * - Left Panel: Session controls (Quick Session Starter)
 * - Center Panel: TradingChart, SignalLog, RiskAlerts
 * - Right Panel: PositionMonitor, OrderHistory
 *
 * All components use WebSocket for real-time updates < 1s latency.
 */

'use client';

import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import TradingChart from '@/components/trading/TradingChart';
import OrderHistory from '@/components/trading/OrderHistory';
import SignalLog from '@/components/trading/SignalLog';
import RiskAlerts from '@/components/trading/RiskAlerts';
import PositionMonitor from '@/components/trading/PositionMonitor';

// ========================================
// TypeScript Types
// ========================================

interface SessionConfig {
  session_type: 'paper' | 'live';
  symbols: string[];
  strategies: string[];
}

// ========================================
// Component
// ========================================

export default function LiveTradingPage() {
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(undefined);
  const [selectedSymbol, setSelectedSymbol] = useState('BTC_USDT');
  const [isPanelCollapsed, setIsPanelCollapsed] = useState({
    left: false,
    right: false
  });

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200 shadow-sm">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">Live Trading</h1>
          {activeSessionId && (
            <span className="px-3 py-1 text-xs font-medium text-white bg-green-500 rounded-full">
              Active: {activeSessionId.slice(0, 12)}...
            </span>
          )}
        </div>
        <div className="flex items-center space-x-3">
          {/* Connection Status */}
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-gray-600">Connected</span>
          </div>
        </div>
      </header>

      {/* 3-Panel Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Session Controls */}
        <aside
          className={`bg-white border-r border-gray-200 transition-all duration-300 ${
            isPanelCollapsed.left ? 'w-12' : 'w-80'
          } flex flex-col`}
        >
          {/* Panel Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            {!isPanelCollapsed.left && (
              <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                Session Control
              </h2>
            )}
            <button
              onClick={() => setIsPanelCollapsed(prev => ({ ...prev, left: !prev.left }))}
              className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
              title={isPanelCollapsed.left ? 'Expand' : 'Collapse'}
            >
              <svg
                className={`w-5 h-5 transition-transform ${isPanelCollapsed.left ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          </div>

          {/* Panel Content */}
          {!isPanelCollapsed.left && (
            <div className="flex-1 overflow-y-auto p-4">
              <QuickSessionStarter
                onSessionStarted={(sessionId) => setActiveSessionId(sessionId)}
                onSessionStopped={() => setActiveSessionId(undefined)}
              />
            </div>
          )}
        </aside>

        {/* Center Panel - Charts & Logs */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Trading Chart */}
          <div className="h-1/2 border-b border-gray-200">
            <TradingChart
              session_id={activeSessionId}
              initialSymbol={selectedSymbol}
              className="h-full"
            />
          </div>

          {/* Bottom Split: SignalLog & RiskAlerts */}
          <div className="h-1/2 flex">
            <div className="w-2/3 border-r border-gray-200">
              <SignalLog
                session_id={activeSessionId}
                className="h-full"
              />
            </div>
            <div className="w-1/3">
              <RiskAlerts
                session_id={activeSessionId}
                className="h-full"
              />
            </div>
          </div>
        </main>

        {/* Right Panel - Positions & Orders */}
        <aside
          className={`bg-white border-l border-gray-200 transition-all duration-300 ${
            isPanelCollapsed.right ? 'w-12' : 'w-96'
          } flex flex-col`}
        >
          {/* Panel Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <button
              onClick={() => setIsPanelCollapsed(prev => ({ ...prev, right: !prev.right }))}
              className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
              title={isPanelCollapsed.right ? 'Expand' : 'Collapse'}
            >
              <svg
                className={`w-5 h-5 transition-transform ${isPanelCollapsed.right ? '' : 'rotate-180'}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            {!isPanelCollapsed.right && (
              <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
                Positions & Orders
              </h2>
            )}
          </div>

          {/* Panel Content */}
          {!isPanelCollapsed.right && (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Position Monitor */}
              <div className="h-1/2 border-b border-gray-200">
                <PositionMonitor
                  session_id={activeSessionId}
                  className="h-full"
                />
              </div>

              {/* Order History */}
              <div className="h-1/2">
                <OrderHistory
                  session_id={activeSessionId}
                  className="h-full"
                />
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

// ========================================
// QuickSessionStarter Component (Simplified)
// ========================================

interface QuickSessionStarterProps {
  onSessionStarted: (sessionId: string) => void;
  onSessionStopped: () => void;
}

function QuickSessionStarter({ onSessionStarted, onSessionStopped }: QuickSessionStarterProps) {
  const [isStarting, setIsStarting] = useState(false);
  const [sessionType, setSessionType] = useState<'paper' | 'live'>('paper');
  const [symbols, setSymbols] = useState(['BTC_USDT']);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const availableSymbols = ['BTC_USDT', 'ETH_USDT', 'ADA_USDT', 'SOL_USDT', 'DOT_USDT'];

  const handleStartSession = async () => {
    setIsStarting(true);
    setError(null);

    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(`${API_BASE_URL}/api/sessions/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_type: sessionType,
          symbols,
          strategy_config: {},
          config: {
            budget: { global_cap: 1000 }
          }
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Failed to start session: ${response.statusText}`);
      }

      const data = await response.json();
      const sessionId = data.session_id || data.data?.session_id;

      if (sessionId) {
        setActiveSession(sessionId);
        onSessionStarted(sessionId);
      } else {
        throw new Error('No session ID returned from server');
      }
    } catch (err: any) {
      console.error('[QuickSessionStarter] Failed to start session:', err);
      setError(err.message || 'Failed to start session');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStopSession = async () => {
    if (!activeSession) return;

    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(`${API_BASE_URL}/api/sessions/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: activeSession })
      });

      if (!response.ok) {
        throw new Error('Failed to stop session');
      }

      setActiveSession(null);
      onSessionStopped();
    } catch (err: any) {
      console.error('[QuickSessionStarter] Failed to stop session:', err);
      setError(err.message || 'Failed to stop session');
    }
  };

  return (
    <div className="space-y-4">
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">Quick Start</h3>
        <p className="text-xs text-blue-700">
          Start a new trading session with default settings. Customize strategies in the Strategy Builder.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {!activeSession ? (
        <div className="space-y-3">
          {/* Session Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Session Type
            </label>
            <select
              value={sessionType}
              onChange={(e) => setSessionType(e.target.value as 'paper' | 'live')}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="paper">Paper Trading (Virtual)</option>
              <option value="live">Live Trading (Real Money)</option>
            </select>
          </div>

          {/* Symbols */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Trading Symbols
            </label>
            <div className="space-y-2">
              {availableSymbols.map(symbol => (
                <label key={symbol} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={symbols.includes(symbol)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSymbols(prev => [...prev, symbol]);
                      } else {
                        setSymbols(prev => prev.filter(s => s !== symbol));
                      }
                    }}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">{symbol}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Start Button */}
          <button
            onClick={handleStartSession}
            disabled={isStarting || symbols.length === 0}
            className="w-full px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStarting ? 'Starting...' : 'Start Session'}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="p-3 bg-green-50 border border-green-200 rounded">
            <p className="text-sm font-medium text-green-900">Session Active</p>
            <p className="text-xs text-green-700 mt-1">
              {activeSession.slice(0, 20)}...
            </p>
          </div>

          <button
            onClick={handleStopSession}
            className="w-full px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
          >
            Stop Session
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * RiskAlerts Component - Agent 6
 * ===============================
 * Displays real-time risk alerts from RiskManager with sound notifications.
 *
 * Features:
 * - Real-time alerts via WebSocket (live_trading.risk_alert)
 * - Color-coded severity (CRITICAL = red, WARNING = yellow, INFO = blue)
 * - Sound notification for CRITICAL alerts
 * - Acknowledge/dismiss functionality
 * - Auto-scroll to new alerts
 * - Alert history (last 50 alerts)
 */

'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket, WebSocketMessage } from '@/hooks/useWebSocket';
import { Logger } from '@/services/frontendLogService';

// ========================================
// TypeScript Types
// ========================================

export interface RiskAlert {
  alert_id: string;
  session_id: string;
  timestamp: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  alert_type: string;
  message: string;
  details?: string;
  acknowledged: boolean;
}

interface RiskAlertsProps {
  session_id?: string;
  maxAlerts?: number;
  playSound?: boolean;
  className?: string;
}

// ========================================
// Component
// ========================================

export default function RiskAlerts({
  session_id,
  maxAlerts = 50,
  playSound = true,
  className = ''
}: RiskAlertsProps) {
  const [alerts, setAlerts] = useState<RiskAlert[]>([]);
  const [unacknowledgedCount, setUnacknowledgedCount] = useState(0);
  const alertsEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const { lastMessage, isConnected } = useWebSocket({
    onMessage: (message: WebSocketMessage) => {
      // Listen for risk alert events from live_trading stream
      if (message.type === 'data' && message.stream === 'live_trading') {
        const data = message.data;
        if (data.alert_type || data.severity) {
          // This is a risk alert
          handleNewAlert(data);
        }
      }
      // Also listen for direct risk_alert events
      else if (message.type === 'risk_alert' || message.stream === 'risk_alert') {
        handleNewAlert(message.data);
      }
    }
  });

  // Initialize audio for critical alerts
  useEffect(() => {
    if (typeof window !== 'undefined' && playSound) {
      audioRef.current = new Audio('/sounds/alert.mp3');  // Add alert sound to public/sounds/
      audioRef.current.volume = 0.5;
    }
  }, [playSound]);

  // Handle new alert
  const handleNewAlert = (alertData: any) => {
    const alert: RiskAlert = {
      alert_id: alertData.alert_id || `alert_${Date.now()}`,
      session_id: alertData.session_id || session_id || 'unknown',
      timestamp: alertData.timestamp || new Date().toISOString(),
      severity: alertData.severity || 'INFO',
      alert_type: alertData.alert_type || 'UNKNOWN',
      message: alertData.message || 'Risk alert triggered',
      details: alertData.details,
      acknowledged: false
    };

    // Filter by session if provided
    if (session_id && alert.session_id !== session_id) {
      return;
    }

    setAlerts(prev => {
      const newAlerts = [alert, ...prev].slice(0, maxAlerts);
      return newAlerts;
    });

    setUnacknowledgedCount(prev => prev + 1);

    // Play sound for CRITICAL alerts
    if (alert.severity === 'CRITICAL' && playSound && audioRef.current) {
      audioRef.current.play().catch(err => {
        Logger.warn('RiskAlerts.playSound', 'Failed to play alert sound', { error: err });
      });
    }

    // Auto-scroll to new alert
    setTimeout(() => {
      alertsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  // Acknowledge alert
  const acknowledgeAlert = (alert_id: string) => {
    setAlerts(prev =>
      prev.map(alert =>
        alert.alert_id === alert_id
          ? { ...alert, acknowledged: true }
          : alert
      )
    );
    setUnacknowledgedCount(prev => Math.max(0, prev - 1));
  };

  // Acknowledge all alerts
  const acknowledgeAll = () => {
    setAlerts(prev => prev.map(alert => ({ ...alert, acknowledged: true })));
    setUnacknowledgedCount(0);
  };

  // Clear all alerts
  const clearAll = () => {
    setAlerts([]);
    setUnacknowledgedCount(0);
  };

  // Get severity color
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'text-red-600 bg-red-50 border-red-300';
      case 'WARNING':
        return 'text-yellow-600 bg-yellow-50 border-yellow-300';
      case 'INFO':
        return 'text-blue-600 bg-blue-50 border-blue-300';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-300';
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center space-x-2">
          <h3 className="text-lg font-semibold text-gray-900">Risk Alerts</h3>
          {unacknowledgedCount > 0 && (
            <span className="px-2 py-1 text-xs font-medium text-white bg-red-500 rounded-full">
              {unacknowledgedCount} new
            </span>
          )}
          {!isConnected && (
            <span className="px-2 py-1 text-xs font-medium text-white bg-gray-400 rounded-full">
              Disconnected
            </span>
          )}
        </div>
        <div className="flex space-x-2">
          {unacknowledgedCount > 0 && (
            <button
              onClick={acknowledgeAll}
              className="px-3 py-1 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
            >
              Acknowledge All
            </button>
          )}
          {alerts.length > 0 && (
            <button
              onClick={clearAll}
              className="px-3 py-1 text-sm font-medium text-gray-700 bg-gray-200 rounded hover:bg-gray-300"
            >
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Alerts List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
        {alerts.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p className="mt-2 text-sm">No alerts</p>
              <p className="mt-1 text-xs text-gray-400">
                {isConnected ? 'System monitoring active' : 'Waiting for connection...'}
              </p>
            </div>
          </div>
        ) : (
          <>
            {alerts.map((alert) => (
              <div
                key={alert.alert_id}
                className={`p-4 border rounded-lg ${getSeverityColor(alert.severity)} ${
                  alert.acknowledged ? 'opacity-50' : ''
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-1 text-xs font-semibold rounded bg-white bg-opacity-50">
                        {alert.severity}
                      </span>
                      <span className="text-xs font-medium">
                        {alert.alert_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs text-gray-500">
                        {formatTimestamp(alert.timestamp)}
                      </span>
                    </div>
                    <p className="mt-2 text-sm font-medium">{alert.message}</p>
                    {alert.details && (
                      <p className="mt-1 text-xs opacity-75">{alert.details}</p>
                    )}
                  </div>
                  {!alert.acknowledged && (
                    <button
                      onClick={() => acknowledgeAlert(alert.alert_id)}
                      className="ml-4 px-3 py-1 text-xs font-medium text-white bg-black bg-opacity-20 rounded hover:bg-opacity-30"
                    >
                      Dismiss
                    </button>
                  )}
                </div>
              </div>
            ))}
            <div ref={alertsEndRef} />
          </>
        )}
      </div>

      {/* Footer Stats */}
      <div className="p-3 border-t border-gray-200 bg-white">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>Total: {alerts.length} alerts</span>
          <span>
            Critical: {alerts.filter(a => a.severity === 'CRITICAL').length} |
            Warning: {alerts.filter(a => a.severity === 'WARNING').length}
          </span>
        </div>
      </div>
    </div>
  );
}

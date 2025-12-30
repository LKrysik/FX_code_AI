'use client';

/**
 * ConnectionNotificationsProvider
 * ================================
 * BUG-008-3: Client component that enables connection status toast notifications (AC5).
 *
 * This component should be included in the app layout to enable automatic
 * toast notifications for WebSocket connection events.
 */

import { useConnectionNotifications } from '@/hooks/useConnectionNotifications';

export function ConnectionNotificationsProvider() {
  useConnectionNotifications();
  return null;
}

export default ConnectionNotificationsProvider;

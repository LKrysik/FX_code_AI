/**
 * Debug Store
 * ===========
 * Manages debug panel state and WebSocket message history.
 * Only active in development mode.
 *
 * Story: 0-4-debug-panel-foundation
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// Message types from websocket.ts relevantTypes
export const MESSAGE_TYPES = [
  'market_data',
  'indicators',
  'signal',
  'signals',
  'session_status',
  'session_update',
  'strategy_status',
  'strategy_update',
  'health_check',
  'comprehensive_health_check',
  'data',
  'execution_result',
  'status',
] as const;

export type MessageType = typeof MESSAGE_TYPES[number] | string;

export interface DebugMessage {
  id: number;
  type: MessageType;
  stream?: string;
  timestamp: string;
  payload: unknown;
}

export interface DebugState {
  // Panel state
  isOpen: boolean;

  // Messages (circular buffer, max 50)
  messages: DebugMessage[];
  maxMessages: number;

  // Filters
  activeFilters: Set<MessageType>;

  // Actions
  togglePanel: () => void;
  setOpen: (open: boolean) => void;
  addMessage: (message: Omit<DebugMessage, 'id'>) => void;
  clearMessages: () => void;
  toggleFilter: (type: MessageType) => void;
  setFilters: (types: MessageType[]) => void;
  clearFilters: () => void;
}

// Load persisted state from localStorage
const loadPersistedState = () => {
  if (typeof window === 'undefined') return { isOpen: false, activeFilters: new Set<MessageType>() };

  try {
    const isOpen = localStorage.getItem('debugPanel.isOpen') === 'true';
    const savedFilters = localStorage.getItem('debugPanel.filters');
    const activeFilters = savedFilters
      ? new Set<MessageType>(JSON.parse(savedFilters))
      : new Set<MessageType>();
    return { isOpen, activeFilters };
  } catch {
    return { isOpen: false, activeFilters: new Set<MessageType>() };
  }
};

let messageIdCounter = 0;

export const useDebugStore = create<DebugState>()(
  devtools(
    (set, get) => {
      const persisted = loadPersistedState();

      return {
        // Initial state
        isOpen: persisted.isOpen,
        messages: [],
        maxMessages: 50,
        activeFilters: persisted.activeFilters,

        // Toggle panel open/closed
        togglePanel: () => {
          const newState = !get().isOpen;
          set({ isOpen: newState });
          if (typeof window !== 'undefined') {
            localStorage.setItem('debugPanel.isOpen', String(newState));
          }
        },

        // Set panel open state
        setOpen: (open: boolean) => {
          set({ isOpen: open });
          if (typeof window !== 'undefined') {
            localStorage.setItem('debugPanel.isOpen', String(open));
          }
        },

        // Add message to circular buffer (max 50)
        addMessage: (message: Omit<DebugMessage, 'id'>) => {
          const { messages, maxMessages } = get();
          const newMessage: DebugMessage = {
            ...message,
            id: ++messageIdCounter,
          };

          // Circular buffer: keep last maxMessages
          const newMessages = [newMessage, ...messages].slice(0, maxMessages);
          set({ messages: newMessages });
        },

        // Clear all messages
        clearMessages: () => {
          set({ messages: [] });
        },

        // Toggle a specific filter
        toggleFilter: (type: MessageType) => {
          const { activeFilters } = get();
          const newFilters = new Set(activeFilters);

          if (newFilters.has(type)) {
            newFilters.delete(type);
          } else {
            newFilters.add(type);
          }

          set({ activeFilters: newFilters });
          if (typeof window !== 'undefined') {
            localStorage.setItem('debugPanel.filters', JSON.stringify([...newFilters]));
          }
        },

        // Set multiple filters at once
        setFilters: (types: MessageType[]) => {
          const newFilters = new Set<MessageType>(types);
          set({ activeFilters: newFilters });
          if (typeof window !== 'undefined') {
            localStorage.setItem('debugPanel.filters', JSON.stringify(types));
          }
        },

        // Clear all filters (show all messages)
        clearFilters: () => {
          set({ activeFilters: new Set() });
          if (typeof window !== 'undefined') {
            localStorage.removeItem('debugPanel.filters');
          }
        },
      };
    },
    { name: 'debug-store' }
  )
);

// Helper to get filtered messages
export const getFilteredMessages = (state: DebugState): DebugMessage[] => {
  if (state.activeFilters.size === 0) {
    return state.messages;
  }
  return state.messages.filter(msg => state.activeFilters.has(msg.type));
};

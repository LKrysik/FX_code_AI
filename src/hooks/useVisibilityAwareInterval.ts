import { useEffect, useRef } from 'react';

export function useVisibilityAwareInterval(callback: () => void, delay: number) {
  const savedCallback = useRef<() => void>();
  const intervalId = useRef<NodeJS.Timeout>();

  // Remember the latest callback
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Set up the interval
  useEffect(() => {
    function tick() {
      if (savedCallback.current) {
        savedCallback.current();
      }
    }

    function handleVisibilityChange() {
      if (document.hidden) {
        // Page is hidden, clear interval
        if (intervalId.current) {
          clearInterval(intervalId.current);
          intervalId.current = undefined;
        }
      } else {
        // Page is visible, restart interval
        if (!intervalId.current) {
          intervalId.current = setInterval(tick, delay);
        }
      }
    }

    // Start interval immediately if page is visible
    if (!document.hidden) {
      intervalId.current = setInterval(tick, delay);
    }

    // Listen for visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      if (intervalId.current) {
        clearInterval(intervalId.current);
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [delay]);
}
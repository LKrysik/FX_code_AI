/**
 * Next.js Middleware for URL Rewrites
 * =====================================
 *
 * Provides backward compatibility for legacy /trading and /backtesting URLs
 * by redirecting them to the unified dashboard with appropriate mode parameter.
 *
 * Redirects:
 * - /trading → /dashboard?mode=live
 * - /backtesting → /dashboard?mode=backtest
 *
 * This maintains URL consistency while consolidating the codebase to a single
 * unified dashboard interface per TARGET_STATE_TRADING_INTERFACE.md
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Redirect /trading → /dashboard?mode=live
  if (pathname === '/trading') {
    const url = request.nextUrl.clone();
    url.pathname = '/dashboard';
    url.searchParams.set('mode', 'live');
    return NextResponse.redirect(url);
  }

  // Redirect /paper → /dashboard?mode=paper
  if (pathname === '/paper') {
    const url = request.nextUrl.clone();
    url.pathname = '/dashboard';
    url.searchParams.set('mode', 'paper');
    return NextResponse.redirect(url);
  }

  // Redirect /backtesting → /dashboard?mode=backtest
  if (pathname === '/backtesting') {
    const url = request.nextUrl.clone();
    url.pathname = '/dashboard';
    url.searchParams.set('mode', 'backtest');
    return NextResponse.redirect(url);
  }

  // Allow all other requests to proceed normally
  return NextResponse.next();
}

// Configure which paths the middleware should run on
export const config = {
  matcher: [
    '/trading',
    '/paper',
    '/backtesting',
  ],
};

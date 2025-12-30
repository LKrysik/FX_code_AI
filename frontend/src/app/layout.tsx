import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import ThemeProvider from '@/components/theme/ThemeProvider'
import Layout from '@/components/layout/Layout'
import ErrorBoundary from '@/components/ErrorBoundary'
import NotificationProvider from '@/components/common/NotificationProvider'
import ConnectionNotificationsProvider from '@/components/common/ConnectionNotificationsProvider'
import CsrfInitializer from '@/components/common/CsrfInitializer'
import FrontendLogInitializer from '@/components/common/FrontendLogInitializer'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Crypto Trading Bot - Pump & Dump Detection',
  description: 'Advanced cryptocurrency trading system with pump and dump detection',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ThemeProvider>
          <FrontendLogInitializer />
          <ErrorBoundary>
            <CsrfInitializer />
            <Layout>
              {children}
              <NotificationProvider />
              <ConnectionNotificationsProvider />
            </Layout>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  )
}
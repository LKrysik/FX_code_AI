import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import ThemeProvider from '@/components/theme/ThemeProvider'
import Layout from '@/components/layout/Layout'
import ErrorBoundary from '@/components/ErrorBoundary'
import NotificationProvider from '@/components/common/NotificationProvider'
import CsrfInitializer from '@/components/common/CsrfInitializer'

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
          <ErrorBoundary>
            <CsrfInitializer />
            <Layout>
              {children}
              <NotificationProvider />
            </Layout>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  )
}
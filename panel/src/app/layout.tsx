import type { Metadata } from 'next'
import './globals.css'
import ConditionalLayout from '@/components/ConditionalLayout'
import { WebVitals } from './web-vitals'

export const metadata: Metadata = {
  title: 'IKZOCR — Panel',
  description: 'Platforma OCR dla dokumentów medycznych',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl">
      <body style={{ margin: 0, padding: 0, background: '#F5F8F6' }}>
        <WebVitals />
        <ConditionalLayout>{children}</ConditionalLayout>
      </body>
    </html>
  )
}

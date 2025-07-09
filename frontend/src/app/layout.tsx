import React from 'react'
import { Inter } from 'next/font/google'
import { AntdRegistry } from '@ant-design/nextjs-registry'
import { ConfigProvider } from 'antd'
import { Metadata } from 'next'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'PCAP Reporter - Network Analysis Tool',
  description: 'Comprehensive PCAP file analysis and reporting tool with advanced network diagnostics',
  keywords: ['pcap', 'network analysis', 'wireshark', 'tshark', 'scapy', 'network security'],
  authors: [{ name: 'PCAP Reporter Team' }],
  viewport: 'width=device-width, initial-scale=1',
  robots: 'index, follow',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AntdRegistry>
          <ConfigProvider
            theme={{
              token: {
                colorPrimary: '#1890ff',
                colorSuccess: '#52c41a',
                colorWarning: '#faad14',
                colorError: '#f5222d',
                colorInfo: '#1890ff',
                borderRadius: 6,
                fontFamily: inter.style.fontFamily,
              },
              components: {
                Layout: {
                  headerBg: '#001529',
                  headerPadding: '0 24px',
                },
                Menu: {
                  darkItemBg: '#001529',
                  darkItemSelectedBg: '#1890ff',
                },
                Button: {
                  borderRadius: 6,
                },
                Card: {
                  borderRadius: 8,
                },
                Table: {
                  borderRadius: 8,
                },
              },
            }}
          >
            {children}
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  )
} 
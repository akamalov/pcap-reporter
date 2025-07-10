'use client'

import React from 'react'
import { Layout, Typography, Button, Card, Row, Col, Space, Divider } from 'antd'
import { 
  CloudUploadOutlined, 
  FileTextOutlined, 
  BarChartOutlined,
  SafetyOutlined,
  GlobalOutlined,
  RocketOutlined
} from '@ant-design/icons'
import Link from 'next/link'
import { ThemeToggle } from './components/ThemeToggle'

const { Header, Content, Footer } = Layout
const { Title, Paragraph, Text } = Typography

const features = [
  {
    icon: <CloudUploadOutlined className="text-blue-500" style={{ fontSize: '32px' }} />,
    title: 'Easy Upload',
    description: 'Drag and drop PCAP files for instant analysis. Supports all major PCAP formats.'
  },
  {
    icon: <BarChartOutlined className="text-green-500" style={{ fontSize: '32px' }} />,
    title: 'Detailed Analytics',
    description: 'Comprehensive traffic analysis with protocol statistics, top talkers, and performance metrics.'
  },
  {
    icon: <SafetyOutlined className="text-red-500" style={{ fontSize: '32px' }} />,
    title: 'Security Analysis',
    description: 'Advanced security scanning to identify potential threats and network anomalies.'
  },
  {
    icon: <GlobalOutlined className="text-purple-500" style={{ fontSize: '32px' }} />,
    title: 'Network Topology',
    description: 'Visual network diagrams showing communication patterns and logical connections.'
  },
  {
    icon: <FileTextOutlined className="text-orange-500" style={{ fontSize: '32px' }} />,
    title: 'Professional Reports',
    description: 'Generate comprehensive PDF reports with executive summaries and technical details.'
  },
  {
    icon: <RocketOutlined className="text-cyan-500" style={{ fontSize: '32px' }} />,
    title: 'Fast Processing',
    description: 'Hybrid analysis engine combining tshark and Scapy for optimal speed and accuracy.'
  }
]

export default function HomePage() {
  return (
    <Layout className="min-h-screen">
      {/* Header */}
      <Header className="bg-slate-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 flex items-center justify-between gap-2 sm:gap-4">
          <Link href="/" className="flex items-center space-x-2 sm:space-x-3 min-w-0 flex-shrink-0">
            <GlobalOutlined className="text-white text-lg sm:text-xl md:text-2xl" />
            <Title level={3} className="text-white mb-0 truncate text-sm sm:text-base md:text-lg lg:text-xl">
              PCAP Reporter
            </Title>
          </Link>
          <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
            <Link href="/upload">
              <Button 
                type="primary" 
                icon={<CloudUploadOutlined />} 
                className="hidden md:inline-flex"
                size="middle"
              >
                Upload PCAP
              </Button>
              <Button 
                type="primary" 
                icon={<CloudUploadOutlined />} 
                className="md:hidden" 
                size="small"
                title="Upload PCAP"
              />
            </Link>
            <Link href="/reports">
              <Button 
                type="default" 
                icon={<FileTextOutlined />} 
                className="hidden md:inline-flex"
                size="middle"
              >
                View Reports
              </Button>
              <Button 
                type="default" 
                icon={<FileTextOutlined />} 
                className="md:hidden" 
                size="small"
                title="View Reports"
              />
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </Header>

      {/* Main Content */}
      <Content className="bg-gray-50">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-12 sm:py-16 md:py-20">
          <div className="max-w-5xl mx-auto px-6 text-center">
            <div className="mb-6 sm:mb-8">
              <Title level={1} className="text-white mb-0 text-xl sm:text-2xl md:text-3xl lg:text-4xl xl:text-5xl leading-tight font-bold">
                Professional PCAP Analysis Made Simple
              </Title>
            </div>
            <div className="max-w-3xl mx-auto mb-8 sm:mb-10 md:mb-12">
              <Paragraph className="text-sm sm:text-base md:text-lg lg:text-xl text-blue-100 leading-relaxed mb-0">
                Upload your PCAP files and get comprehensive network analysis reports with 
                security insights, performance metrics, and visual network diagrams.
              </Paragraph>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center items-center max-w-md sm:max-w-lg mx-auto">
              <Link href="/upload" className="w-full sm:w-auto">
                <Button type="primary" size="large" icon={<CloudUploadOutlined />} className="w-full sm:w-auto min-w-[140px]">
                  Start Analysis
                </Button>
              </Link>
              <Link href="/reports" className="w-full sm:w-auto">
                <Button type="default" size="large" ghost className="w-full sm:w-auto min-w-[140px]">
                  View Reports
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="py-20 px-4">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <Title level={2} className="mb-4">
                Powerful Network Analysis Features
              </Title>
              <Paragraph className="text-lg text-gray-600 max-w-2xl mx-auto">
                Our advanced analysis engine provides comprehensive insights into your network traffic
                with professional-grade reporting capabilities.
              </Paragraph>
            </div>

            <Row gutter={[32, 32]}>
              {features.map((feature, index) => (
                <Col xs={24} md={12} lg={8} key={index}>
                  <Card 
                    className="h-full hover:shadow-lg transition-shadow duration-300"
                    hoverable
                  >
                    <div className="text-center">
                      <div className="mb-4">
                        {feature.icon}
                      </div>
                      <Title level={4} className="mb-3">
                        {feature.title}
                      </Title>
                      <Paragraph className="text-gray-600">
                        {feature.description}
                      </Paragraph>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          </div>
        </div>

        {/* Stats Section */}
        <div className="bg-white py-16">
          <div className="max-w-7xl mx-auto px-4">
            <Row gutter={[32, 32]} className="text-center">
              <Col xs={24} sm={8}>
                <div>
                  <Title level={2} className="text-blue-600 mb-2">
                    99.9%
                  </Title>
                  <Text className="text-gray-600">Analysis Accuracy</Text>
                </div>
              </Col>
              <Col xs={24} sm={8}>
                <div>
                  <Title level={2} className="text-green-600 mb-2">
                    &lt;30s
                  </Title>
                  <Text className="text-gray-600">Average Processing Time</Text>
                </div>
              </Col>
              <Col xs={24} sm={8}>
                <div>
                  <Title level={2} className="text-purple-600 mb-2">
                    50+
                  </Title>
                  <Text className="text-gray-600">Analysis Metrics</Text>
                </div>
              </Col>
            </Row>
          </div>
        </div>

        {/* Call to Action */}
        <div className="bg-gray-100 py-16">
          <div className="max-w-4xl mx-auto text-center px-4">
            <Title level={2} className="mb-4">
              Ready to Analyze Your Network Traffic?
            </Title>
            <Paragraph className="text-lg text-gray-600 mb-8">
              Upload your PCAP files and get detailed insights in minutes. 
              No registration required - start analyzing immediately.
            </Paragraph>
            <Link href="/upload">
              <Button type="primary" size="large" icon={<CloudUploadOutlined />}>
                Upload Your First PCAP File
              </Button>
            </Link>
          </div>
        </div>
      </Content>

      {/* Footer */}
      <Footer className="bg-slate-800 text-white">
        <div className="max-w-7xl mx-auto px-4">
          <Row gutter={[32, 32]}>
            <Col xs={24} md={8}>
              <div className="flex items-center space-x-2 mb-4">
                <GlobalOutlined className="text-xl" />
                <Title level={4} className="text-white mb-0">
                  PCAP Reporter
                </Title>
              </div>
              <Paragraph className="text-gray-400">
                Professional network analysis and reporting tool for PCAP files.
              </Paragraph>
            </Col>
            <Col xs={24} md={8}>
              <Title level={5} className="text-white mb-4">
                Features
              </Title>
              <ul className="space-y-2 text-gray-400">
                <li>PCAP Analysis</li>
                <li>Security Scanning</li>
                <li>Performance Metrics</li>
                <li>PDF Reports</li>
              </ul>
            </Col>
            <Col xs={24} md={8}>
              <Title level={5} className="text-white mb-4">
                Support
              </Title>
              <ul className="space-y-2 text-gray-400">
                <li>Documentation</li>
                <li>API Reference</li>
                <li>Sample Files</li>
                <li>Contact Support</li>
              </ul>
            </Col>
          </Row>
          <Divider className="border-gray-600" />
          <div className="text-center text-gray-400">
            <Text>© 2024 PCAP Reporter. Built with Next.js, FastAPI, and modern web technologies.</Text>
          </div>
        </div>
      </Footer>
    </Layout>
  )
} 
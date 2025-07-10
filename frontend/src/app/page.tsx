'use client'

import React from 'react'
import { Layout, Typography, Button, Card, Row, Col, Divider } from 'antd'
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
        <div className="max-w-7xl mx-auto px-4 lg:px-6 flex items-center justify-between h-16">
          <Link href="/" className="flex items-center flex-shrink-0">
            <GlobalOutlined className="text-white text-2xl" />
            <div style={{ marginLeft: '12px', display: 'flex', alignItems: 'center' }}>
              <ThemeToggle />
            </div>
            <Title level={3} className="text-white mb-0 hidden sm:block" style={{ marginLeft: '24px', marginRight: '10px' }}>
              PCAP Reporter
            </Title>
          </Link>
        </div>
      </Header>

      {/* Main Content */}
      <Content className="bg-gray-50">
        {/* Hero Section */}
        <section className="bg-gradient-to-r from-blue-600 to-purple-600 text-white min-h-[600px] flex items-center">
          <div className="container px-4 sm:px-6 lg:px-8 py-12" style={{ marginLeft: '8%', marginRight: 'auto' }}>
            <div className="max-w-4xl text-left">
              <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-8 leading-[1.1]">
                Professional PCAP Analysis Made Simple
              </h1>
              
              <p className="text-lg sm:text-xl md:text-2xl text-blue-100 mb-10 leading-relaxed max-w-3xl mx-auto px-4">
                Upload PCAP files. Get instant analysis reports.
              </p>
              
              <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-start', marginTop: '32px', gap: '32px' }}>
                <Link href="/upload">
                  <Button 
                    type="primary" 
                    size="large" 
                    icon={<CloudUploadOutlined />} 
                    className="w-56 h-12 text-base font-medium"
                  >
                    Start Analysis
                  </Button>
                </Link>
                <Link href="/reports">
                  <Button 
                    type="primary" 
                    size="large" 
                    icon={<FileTextOutlined />}
                    className="w-56 h-12 text-base font-medium"
                  >
                    View Reports
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="bg-slate-800 text-white" style={{ paddingTop: '48px', paddingBottom: '48px', paddingLeft: '24px', paddingRight: '24px' }}>
          <div className="container max-w-6xl" style={{ marginLeft: '8%', marginRight: 'auto' }}>
            <div className="text-left mb-12 lg:mb-16">
              <Title level={2} className="mb-4 text-2xl sm:text-3xl md:text-4xl font-bold px-4 text-white">
                Key Features
              </Title>
              <Paragraph className="text-lg sm:text-xl text-gray-300 max-w-3xl leading-relaxed">
                Our advanced analysis engine provides comprehensive insights into your network traffic
                with professional-grade reporting capabilities.
              </Paragraph>
            </div>

            <Row gutter={[24, 24]} className="mt-8">
              {features.map((feature, index) => (
                <Col xs={24} sm={12} lg={8} key={index}>
                  <Card 
                    className="h-full hover:shadow-xl transition-all duration-300 border-0 shadow-md bg-slate-700"
                    hoverable
                  >
                    <div className="text-center p-6">
                      <div className="mb-6 p-4 bg-slate-600 rounded-full inline-block">
                        {feature.icon}
                      </div>
                      <Title level={4} className="mb-4 text-lg font-semibold text-white">
                        {feature.title}
                      </Title>
                      <Paragraph className="text-gray-300 leading-relaxed text-sm">
                        {feature.description}
                      </Paragraph>
                    </div>
                  </Card>
                </Col>
              ))}
            </Row>
          </div>
        </section>

        {/* Stats Section */}
        <section className="bg-slate-800 text-white" style={{ paddingTop: '16px', paddingBottom: '32px' }}>
          <div className="container max-w-6xl px-4 sm:px-6 lg:px-8" style={{ marginLeft: '12%', marginRight: 'auto' }}>
            <Row gutter={[32, 32]} className="text-left">
              <Col xs={24} sm={8}>
                <div className="py-8">
                  <div className="text-4xl lg:text-5xl font-bold text-blue-400 mb-4">
                    99.9%
                  </div>
                  <div className="text-gray-300 text-base lg:text-lg font-medium">
                    Analysis Accuracy
                  </div>
                </div>
              </Col>
              <Col xs={24} sm={8}>
                <div className="py-8">
                  <div className="text-4xl lg:text-5xl font-bold text-green-400 mb-4">
                    &lt;30s
                  </div>
                  <div className="text-gray-300 text-base lg:text-lg font-medium">
                    Average Processing Time
                  </div>
                </div>
              </Col>
              <Col xs={24} sm={8}>
                <div className="py-8">
                  <div className="text-4xl lg:text-5xl font-bold text-purple-400 mb-4">
                    50+
                  </div>
                  <div className="text-gray-300 text-base lg:text-lg font-medium">
                    Analysis Metrics
                  </div>
                </div>
              </Col>
            </Row>
          </div>
        </section>

        {/* Call to Action */}
        <section className="bg-slate-800 text-white" style={{ paddingTop: '48px', paddingBottom: '48px' }}>
          <div className="container max-w-4xl px-4 sm:px-6 lg:px-8" style={{ marginLeft: '9%', marginRight: 'auto' }}>
            <Title level={2} className="mb-6 text-2xl sm:text-3xl md:text-4xl font-bold text-white text-left">
              Ready to Analyze Your Network Traffic?
            </Title>
            <Paragraph className="text-lg sm:text-xl text-gray-300 mb-12 leading-relaxed max-w-2xl text-left">
              Upload your PCAP files and get detailed insights in minutes. 
              No registration required - start analyzing immediately.
            </Paragraph>
            <div className="mb-8 text-left">
              <Link href="/upload">
                <Button 
                  type="primary" 
                  size="large" 
                  icon={<CloudUploadOutlined />} 
                  className="h-12 px-8 text-base font-medium"
                >
                  Upload PCAP File
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </Content>

      {/* Footer */}
      <Footer className="bg-slate-800 text-white">
        <div className="container max-w-6xl px-4 sm:px-6 lg:px-8" style={{ marginLeft: '7%', marginRight: 'auto' }}>
          <Row gutter={[32, 32]} className="py-8">
            <Col xs={24} md={8}>
              <div className="flex items-center space-x-3 mb-4">
                <GlobalOutlined className="text-2xl" />
                <Title level={4} className="text-white mb-0">
                  PCAP Reporter
                </Title>
              </div>
              <Paragraph className="text-gray-400 text-base">
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
          <Divider className="border-gray-600 my-6" />
          <div className="text-center text-gray-400 pb-4">
            <Text>© 2024 PCAP Reporter. Built with Next.js, FastAPI, and modern web technologies.</Text>
          </div>
        </div>
      </Footer>
    </Layout>
  )
} 
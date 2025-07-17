'use client'

import React, { useState, useCallback, useEffect } from 'react'
import { 
  Layout, 
  Typography, 
  Card, 
  Button, 
  Progress, 
  Alert, 
  Space, 
  Row, 
  Col,
  Divider,
  List,
  Tag,
  App
} from 'antd'
import { 
  CloudUploadOutlined, 
  FileTextOutlined, 
  CheckCircleOutlined,
  LoadingOutlined,
  ExclamationCircleOutlined,
  GlobalOutlined,
  UploadOutlined
} from '@ant-design/icons'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
// Remove unused Upload-related imports
import { ApiService, handleApiError, formatFileSize } from '@/lib/api'
import type { UploadResponse } from '@/lib/api'
import { ThemeToggle } from '../components/ThemeToggle'
import { useTheme } from '../components/ThemeProvider'
import { AppHeader } from '@/components'

const { Header, Content, Footer } = Layout
const { Title, Paragraph, Text } = Typography

// UploadResponse interface is now imported from @/lib/api

export default function UploadPage() {
  const router = useRouter()
  const { theme } = useTheme()
  const { message } = App.useApp()
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadedFiles, setUploadedFiles] = useState<UploadResponse[]>([])
  const [currentUpload, setCurrentUpload] = useState<string | null>(null)

  const handleUpload = useCallback(async (file: File): Promise<boolean> => {
    console.log('handleUpload called with file:', file)
    console.log('File name:', file.name)
    console.log('File size:', file.size)
    console.log('File type:', file.type)
    
    // Validate file type
    const allowedTypes = ['.pcap', '.pcapng', '.cap']
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
    console.log('File extension:', fileExtension)
    console.log('Allowed types:', allowedTypes)
    
    if (!allowedTypes.includes(fileExtension)) {
      message.error({
        content: `Invalid file type. Please upload ${allowedTypes.join(', ')} files only.`,
        duration: 5,
        style: { marginTop: '20vh' }
      })
      return false
    }

    // Validate file size (100MB limit)
    const maxSize = 100 * 1024 * 1024 // 100MB
    if (file.size > maxSize) {
      message.error({
        content: 'File size exceeds 100MB limit. Please choose a smaller file.',
        duration: 5,
        style: { marginTop: '20vh' }
      })
      return false
    }

    setUploading(true)
    setUploadProgress(0)
    setCurrentUpload(file.name)

    try {
      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return prev
          }
          return prev + Math.random() * 10
        })
      }, 200)

      console.log('About to call ApiService.submitAnalysis')
      const result = await ApiService.submitAnalysis(file, 'comprehensive', 'normal')
      console.log('ApiService.submitAnalysis result:', result)

      clearInterval(progressInterval)
      
      setUploadProgress(100)
      setUploadedFiles(prev => [result, ...prev])
      
      message.success({
        content: `File uploaded successfully! Analysis started.`,
        duration: 3,
        style: { marginTop: '20vh' }
      })
      
      // Redirect to the report page after a short delay
      setTimeout(() => {
        router.push(`/reports/${result.job_id}`)
      }, 2000)

      return true
    } catch (error: any) {
      console.error('Upload error:', error)
      console.error('Error details:', error.message, error.stack)
      message.error(handleApiError(error))
      return false
    } finally {
      console.log('Upload finally block - cleaning up')
      setUploading(false)
      setCurrentUpload(null)
      setUploadProgress(0)
    }
  }, [router])

  // Removed unused functions and refs - using direct file input now

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <Layout className="min-h-screen" style={{ backgroundColor: '#f9fafb' }}>
      {/* Header */}
      <div style={{ position: 'relative', zIndex: 1000 }}>
        <AppHeader 
          title="PCAP Reporter"
        />
      </div>

      {/* Main Content */}
      <Content 
        className="bg-gray-50 p-6" 
        style={{ 
          marginTop: '64px', // Space for header (matches header height)
          paddingTop: '3rem',
          position: 'relative',
          zIndex: 1
        }}
      >
        <div className="max-w-4xl mx-auto">

          {/* Upload Area */}
          <Card className="mb-6" style={{ marginTop: '4rem' }}>
            <div className="text-center py-16">
              <div className="mb-6" style={{ marginTop: '3%' }}>
                <Title level={2} className="text-gray-800 mb-4">
                  Upload PCAP File
                </Title>
                <Paragraph className="text-gray-600 mb-8" style={{ fontSize: '16px' }}>
                  Upload your PCAP files for comprehensive network analysis
                </Paragraph>
              </div>
              
              <div className="mb-10">
                <UploadOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
              </div>
              
              <div className="mb-6 flex flex-row gap-4 items-center justify-center" style={{ marginTop: '2rem' }}>
                <Button
                  type="primary"
                  size="large"
                  icon={<UploadOutlined />}
                  onClick={() => {
                    console.log('Browse button clicked')
                    document.getElementById('file-input')?.click()
                  }}
                  disabled={uploading}
                  style={{ 
                    padding: '12px 32px', 
                    fontSize: '16px', 
                    fontWeight: 'bold',
                    height: '48px'
                  }}
                >
                  {uploading ? 'Uploading...' : 'Browse for PCAP File'}
                </Button>
                
                <Link href="/reports">
                  <Button
                    type="primary"
                    size="large"
                    icon={<FileTextOutlined />}
                    style={{ 
                      padding: '12px 32px', 
                      fontSize: '16px', 
                      fontWeight: 'bold',
                      height: '48px',
                      marginLeft: '20px'
                    }}
                  >
                    View Reports
                  </Button>
                </Link>
                
                <input
                  id="file-input"
                  type="file"
                  accept=".pcap,.pcapng,.cap"
                  onChange={(e) => {
                    console.log('File input onChange triggered')
                    console.log('Event target:', e.target)
                    console.log('Files:', e.target.files)
                    const file = e.target.files?.[0]
                    console.log('Selected file:', file)
                    if (file) {
                      console.log('Calling handleUpload with file:', file.name)
                      handleUpload(file)
                    } else {
                      console.log('No file selected')
                    }
                  }}
                  style={{ display: 'none' }}
                />
              </div>
              
              <div className="text-gray-600 text-sm">
                <p>Support for .pcap, .pcapng, and .cap files up to 100MB.</p>
                <p>Analysis will start automatically after upload.</p>
              </div>
            </div>

            {/* Upload Progress */}
            {uploading && (
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <Text strong>Uploading: {currentUpload}</Text>
                  <Text>{Math.round(uploadProgress)}%</Text>
                </div>
                <Progress 
                  percent={Math.round(uploadProgress)} 
                  status={uploadProgress === 100 ? 'success' : 'active'}
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
                {uploadProgress === 100 && (
                  <Alert
                    message="Upload Complete!"
                    description="Redirecting to analysis report..."
                    type="success"
                    icon={<CheckCircleOutlined />}
                    className="mt-3"
                  />
                )}
              </div>
            )}
          </Card>

          <div style={{ marginTop: '32px' }}>
            <Row gutter={[24, 24]}>
            <Col xs={24} sm={12} lg={6}>
              {/* Supported Formats */}
              <Card title="Supported Formats" className="mb-6">
                <ul className="text-sm text-gray-600">
                  <li>PCAP (.pcap)</li>
                  <li>PCAP Next Generation (.pcapng)</li>
                  <li>Wireshark Capture (.cap)</li>
                </ul>
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              {/* File Requirements */}
              <Card title="File Requirements" className="mb-6">
                <ul className="text-sm text-gray-600">
                  <li>Maximum file size: 100MB</li>
                  <li>Valid PCAP file structure</li>
                  <li>Readable packet data</li>
                </ul>
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              {/* Analysis Process */}
              <Card title="Analysis Process" className="mb-6">
                <ul className="text-sm text-gray-600">
                  <li>Upload validation (~5 seconds)</li>
                  <li>Basic statistics extraction</li>
                  <li>Protocol analysis</li>
                  <li>Security scanning</li>
                  <li>Report generation</li>
                </ul>
              </Card>
            </Col>

            <Col xs={24} sm={12} lg={6}>
              {/* Sample Files */}
              <Card title="Need Sample Files?" className="mb-6">
                <Paragraph className="text-sm text-gray-600 mb-4">
                  Don't have a PCAP file? Download our sample files to test the analysis features.
                </Paragraph>
                <Space direction="vertical" className="w-full">
                  <Button type="dashed" block size="small">
                    Download HTTP Traffic Sample
                  </Button>
                  <Button type="dashed" block size="small">
                    Download DNS Analysis Sample
                  </Button>
                  <Button type="dashed" block size="small">
                    Download Mixed Protocol Sample
                  </Button>
                </Space>
              </Card>
            </Col>
            </Row>
          </div>

          {/* Recent Uploads */}
          {uploadedFiles.length > 0 && (
            <Card title="Recent Uploads" className="mb-6">
              <List
                dataSource={uploadedFiles}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Link key="view" href={`/reports/${item.job_id}`}>
                        <Button type="link" icon={<FileTextOutlined />}>
                          View Report
                        </Button>
                      </Link>
                    ]}
                  >
                    <List.Item.Meta
                      avatar={<FileTextOutlined style={{ fontSize: '24px', color: '#1890ff' }} />}
                      title={
                        <div className="flex items-center space-x-2">
                          <Text strong>{item.filename}</Text>
                          <Tag color="blue">{item.status}</Tag>
                        </div>
                      }
                      description={
                        <div>
                          <Text type="secondary">
                            Size: {formatFileSize(item.file_size)} • 
                            Uploaded: {formatDate(item.created_at)} • 
                            Type: {item.analysis_type}
                          </Text>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>
          )}
        </div>
      </Content>

      {/* Flexible spacer section that adapts to theme */}
      <div 
        className="flex-1 transition-colors duration-300 min-h-32" 
        style={{ 
          backgroundColor: theme === 'dark' ? '#1e293b' : '#f9fafb'
        }}
      >
        {/* This section stretches to fill remaining space and matches the current theme */}
      </div>

      {/* Footer - pinned to bottom */}
      <Footer className="bg-slate-800 text-white text-center mt-auto">
        <Text className="text-gray-400">
          © 2024 PCAP Reporter. Built with Next.js, FastAPI, and modern web technologies.
        </Text>
      </Footer>
    </Layout>
  )
} 
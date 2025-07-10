'use client'

import React, { useState, useCallback } from 'react'
import { 
  Layout, 
  Typography, 
  Card, 
  Upload, 
  Button, 
  Progress, 
  Alert, 
  Space, 
  Row, 
  Col,
  Divider,
  List,
  Tag,
  message
} from 'antd'
import { 
  CloudUploadOutlined, 
  FileTextOutlined, 
  CheckCircleOutlined,
  LoadingOutlined,
  ExclamationCircleOutlined,
  InboxOutlined,
  GlobalOutlined
} from '@ant-design/icons'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import type { UploadProps, UploadFile } from 'antd/es/upload/interface'
import { ApiService, handleApiError, formatFileSize } from '@/lib/api'
import type { UploadResponse } from '@/lib/api'
import { ThemeToggle } from '../components/ThemeToggle'

const { Header, Content, Footer } = Layout
const { Title, Paragraph, Text } = Typography
const { Dragger } = Upload

// UploadResponse interface is now imported from @/lib/api

export default function UploadPage() {
  const router = useRouter()
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadedFiles, setUploadedFiles] = useState<UploadResponse[]>([])
  const [currentUpload, setCurrentUpload] = useState<string | null>(null)

  const handleUpload = useCallback(async (file: File): Promise<boolean> => {
    // Validate file type
    const allowedTypes = ['.pcap', '.pcapng', '.cap']
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
    
    if (!allowedTypes.includes(fileExtension)) {
      message.error(`Invalid file type. Please upload ${allowedTypes.join(', ')} files only.`)
      return false
    }

    // Validate file size (100MB limit)
    const maxSize = 100 * 1024 * 1024 // 100MB
    if (file.size > maxSize) {
      message.error('File size exceeds 100MB limit.')
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

      const result = await ApiService.submitAnalysis(file, 'comprehensive', 'normal')

      clearInterval(progressInterval)
      
      setUploadProgress(100)
      setUploadedFiles(prev => [result, ...prev])
      
      message.success(`File uploaded successfully! Analysis started.`)
      
      // Redirect to the report page after a short delay
      setTimeout(() => {
        router.push(`/reports/${result.job_id}`)
      }, 2000)

      return true
    } catch (error: any) {
      console.error('Upload error:', error)
      message.error(handleApiError(error))
      return false
    } finally {
      setUploading(false)
      setCurrentUpload(null)
      setUploadProgress(0)
    }
  }, [router])

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pcap,.pcapng,.cap',
    beforeUpload: (file) => {
      handleUpload(file)
      return false // Prevent default upload behavior
    },
    onDrop(e) {
      console.log('Dropped files', e.dataTransfer.files)
    },
    disabled: uploading,
  }

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <Layout className="min-h-screen">
      {/* Header */}
      <Header className="bg-slate-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 flex items-center justify-between h-32">
          <Link href="/" className="flex items-center space-x-3 flex-shrink-0">
            <GlobalOutlined className="text-white text-2xl" />
            <div style={{ marginLeft: '-7px' }}>
              <ThemeToggle />
            </div>
            <Title level={3} className="text-white mb-0 hidden sm:block">
              PCAP Reporter
            </Title>
          </Link>
          <div className="flex items-center space-x-3 flex-shrink-0">
            <Link href="/reports">
              <Button 
                type="default" 
                icon={<FileTextOutlined />} 
                className="h-8 px-4 text-sm"
              >
                <span className="hidden sm:inline">View Reports</span>
              </Button>
            </Link>
          </div>
        </div>
      </Header>

      {/* Main Content */}
      <Content className="bg-gray-50 p-6">
        <div className="max-w-4xl mx-auto">
          
          {/* Page Header */}
          <div className="mb-8" style={{ marginTop: '120px', paddingTop: '60px', marginLeft: '20px' }}>
            <Title level={2} className="mb-2 text-xl sm:text-2xl md:text-3xl">
              Upload PCAP File
            </Title>
            <Paragraph className="text-gray-600 text-sm sm:text-base leading-relaxed">
              Upload your PCAP files for comprehensive network analysis. 
              Supported formats: .pcap, .pcapng, .cap (max 100MB)
            </Paragraph>
          </div>

          {/* Upload Area */}
          <Card className="mb-6">
            <Dragger {...uploadProps} className="mb-4">
              <p className="ant-upload-drag-icon">
                <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
              </p>
              <p className="ant-upload-text">
                Click or drag PCAP file to this area to upload
              </p>
              <p className="ant-upload-hint">
                Support for .pcap, .pcapng, and .cap files up to 100MB.
                Analysis will start automatically after upload.
              </p>
            </Dragger>

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

      {/* Footer */}
      <Footer className="bg-slate-800 text-white text-center">
        <Text className="text-gray-400">
          © 2024 PCAP Reporter. Built with Next.js, FastAPI, and modern web technologies.
        </Text>
      </Footer>
    </Layout>
  )
} 
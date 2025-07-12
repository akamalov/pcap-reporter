'use client'

import React, { useState, useEffect } from 'react'
import { 
  Layout, 
  Typography, 
  Card, 
  Table, 
  Button, 
  Space, 
  Row, 
  Col,
  Input,
  Select,
  Tag,
  Tooltip,
  Dropdown,
  Modal,
  message,
  Progress,
  Statistic,
  DatePicker
} from 'antd'
import { 
  FileTextOutlined, 
  CloudUploadOutlined,
  SearchOutlined,
  FilterOutlined,
  ReloadOutlined,
  DownloadOutlined,
  EyeOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  GlobalOutlined,
  BarChartOutlined
} from '@ant-design/icons'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import type { ColumnsType } from 'antd/es/table'
import type { RangeValue } from 'rc-picker/lib/interface'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { ApiService, handleApiError, formatFileSize, formatDuration } from '@/lib/api'
import type { AnalysisJob, ReportsStats } from '@/lib/api'
import { 
  AppHeader, 
  LoadingOverlay, 
  LoadingSkeleton, 
  ErrorBoundary, 
  useErrorHandler 
} from '@/components'
import { ThemeToggle } from '../components/ThemeToggle'

dayjs.extend(relativeTime)

const { Header, Content, Footer } = Layout
const { Title, Paragraph, Text } = Typography
const { Search } = Input
const { Option } = Select
const { RangePicker } = DatePicker

export default function ReportsPage() {
  const router = useRouter()
  const [reports, setReports] = useState<AnalysisJob[]>([])
  const [filteredReports, setFilteredReports] = useState<AnalysisJob[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [dateRange, setDateRange] = useState<RangeValue<dayjs.Dayjs>>(null)
  const [stats, setStats] = useState<ReportsStats>({
    total_reports: 0,
    completed_reports: 0,
    processing_reports: 0,
    failed_reports: 0,
    total_packets_analyzed: 0,
    total_data_processed: 0
  })

  // Fetch reports data
  const fetchReports = async (showLoading = true) => {
    if (showLoading) setLoading(true)
    setRefreshing(true)
    
    try {
      const data = await ApiService.getAnalysisJobs()
      setReports(data.jobs || [])
      setStats(data.stats || stats)
    } catch (error: any) {
      console.error('Error fetching reports:', error)
      message.error(handleApiError(error))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  // Filter reports based on search and filters
  const applyFilters = () => {
    let filtered = [...reports]

    // Text search
    if (searchText) {
      filtered = filtered.filter(report => 
        report.filename.toLowerCase().includes(searchText.toLowerCase()) ||
        report.job_id.toLowerCase().includes(searchText.toLowerCase())
      )
    }

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(report => report.status === statusFilter)
    }

    // Date range filter
    if (dateRange) {
      const [start, end] = dateRange as [dayjs.Dayjs, dayjs.Dayjs]
      filtered = filtered.filter(report => {
        const reportDate = dayjs(report.created_at)
        return reportDate.isAfter(start) && reportDate.isBefore(end)
      })
    }

    setFilteredReports(filtered)
  }

  // Delete report
  const handleDelete = async (jobId: string) => {
    Modal.confirm({
      title: 'Delete Report',
      content: 'Are you sure you want to delete this analysis report? This action cannot be undone.',
      icon: <ExclamationCircleOutlined />,
      okText: 'Delete',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: async () => {
        try {
          await ApiService.deleteAnalysis(jobId)
          message.success({
            content: 'Report deleted successfully',
            duration: 3,
            style: { marginTop: '20vh' }
          })
          fetchReports(false)
        } catch (error: any) {
          console.error('Error deleting report:', error)
          message.error(handleApiError(error))
        }
      }
    })
  }

  // Download report
  const handleDownload = async (jobId: string, filename: string) => {
    try {
      const blob = await ApiService.downloadReport(jobId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${filename.replace(/\.[^/.]+$/, '')}_analysis_report.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      message.success({
        content: 'Report downloaded successfully',
        duration: 3,
        style: { marginTop: '20vh' }
      })
    } catch (error: any) {
      console.error('Error downloading report:', error)
      message.error(handleApiError(error))
    }
  }

  // Get status color and icon
  const getStatusDisplay = (status: string, progress?: number) => {
    switch (status) {
      case 'completed':
        return <Tag icon={<CheckCircleOutlined />} color="success">Completed</Tag>
      case 'processing':
        return (
          <div className="flex items-center space-x-2">
            <Tag icon={<LoadingOutlined />} color="processing">Processing</Tag>
            {progress && <Progress percent={progress} size="small" style={{ width: 60 }} />}
          </div>
        )
      case 'pending':
        return <Tag icon={<ClockCircleOutlined />} color="default">Pending</Tag>
      case 'failed':
        return <Tag icon={<ExclamationCircleOutlined />} color="error">Failed</Tag>
      case 'cancelled':
        return <Tag color="default">Cancelled</Tag>
      default:
        return <Tag>{status}</Tag>
    }
  }

  // Table columns
  const columns: ColumnsType<AnalysisJob> = [
    {
      title: 'Filename',
      dataIndex: 'filename',
      key: 'filename',
      width: 200,
      ellipsis: true,
      render: (filename: string, record: AnalysisJob) => (
        <div>
          <Text strong className="block">{filename}</Text>
          <Text type="secondary" className="text-xs">
            ID: {record.job_id.slice(0, 8)}...
          </Text>
        </div>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 150,
      render: (status: string, record: AnalysisJob) => getStatusDisplay(status, record.progress),
      filters: [
        { text: 'Completed', value: 'completed' },
        { text: 'Processing', value: 'processing' },
        { text: 'Pending', value: 'pending' },
        { text: 'Failed', value: 'failed' },
        { text: 'Cancelled', value: 'cancelled' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: 'File Size',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (size: number) => formatFileSize(size),
      sorter: (a, b) => a.file_size - b.file_size,
    },
    {
      title: 'Packets',
      dataIndex: 'total_packets',
      key: 'total_packets',
      width: 100,
      render: (packets?: number) => packets ? packets.toLocaleString() : 'N/A',
      sorter: (a, b) => (a.total_packets || 0) - (b.total_packets || 0),
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      render: (duration?: number) => duration ? formatDuration(duration) : '-',
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => (
        <Tooltip title={dayjs(date).format('YYYY-MM-DD HH:mm:ss')}>
          {dayjs(date).fromNow()}
        </Tooltip>
      ),
      sorter: (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
      defaultSortOrder: 'descend',
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record: AnalysisJob) => (
        <Space size="small">
          <Tooltip title="View Report">
            <Link href={`/reports/${record.job_id}`}>
              <Button 
                type="text" 
                icon={<EyeOutlined />} 
                size="small"
                disabled={record.status !== 'completed'}
              />
            </Link>
          </Tooltip>
          <Tooltip title="Download PDF">
            <Button 
              type="text" 
              icon={<DownloadOutlined />} 
              size="small"
              onClick={() => handleDownload(record.job_id, record.filename)}
              disabled={record.status !== 'completed'}
            />
          </Tooltip>
          <Tooltip title="Delete">
            <Button 
              type="text" 
              icon={<DeleteOutlined />} 
              size="small"
              danger
              onClick={() => handleDelete(record.job_id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  // Effects
  useEffect(() => {
    fetchReports()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [reports, searchText, statusFilter, dateRange])

  // Auto-refresh for processing reports
  useEffect(() => {
    const hasProcessing = reports.some(r => r.status === 'processing' || r.status === 'pending')
    if (hasProcessing) {
      const interval = setInterval(() => {
        fetchReports(false)
      }, 10000) // Refresh every 10 seconds
      
      return () => clearInterval(interval)
    }
  }, [reports])

  return (
    <Layout className="min-h-screen">
      {/* Header */}
      <AppHeader 
        title="Analysis Reports"
        actions={
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
        }
      />

      {/* Main Content */}
      <Content className="bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          
          {/* Page Header */}
          <div className="mb-6">
            <Title level={2} className="mb-2">
              Analysis Reports
            </Title>
            <Paragraph className="text-gray-600">
              View and manage all your PCAP analysis reports
            </Paragraph>
          </div>

          {/* Statistics Cards */}
          <Row gutter={[16, 16]} className="mb-6">
            <Col xs={12} sm={6}>
              <Card>
                <Statistic
                  title="Total Reports"
                  value={stats.total_reports}
                  prefix={<FileTextOutlined />}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic
                  title="Completed"
                  value={stats.completed_reports}
                  prefix={<CheckCircleOutlined />}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic
                  title="Processing"
                  value={stats.processing_reports}
                  prefix={<LoadingOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic
                  title="Packets Analyzed"
                  value={stats.total_packets_analyzed}
                  prefix={<BarChartOutlined />}
                />
              </Card>
            </Col>
          </Row>

          {/* Filters and Search */}
          <Card className="mb-6">
            <Row gutter={[16, 16]} align="middle">
              <Col xs={24} sm={8}>
                <Search
                  placeholder="Search by filename or job ID..."
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  prefix={<SearchOutlined />}
                  allowClear
                />
              </Col>
              <Col xs={12} sm={4}>
                <Select
                  value={statusFilter}
                  onChange={setStatusFilter}
                  style={{ width: '100%' }}
                  placeholder="Filter by status"
                >
                  <Option value="all">All Status</Option>
                  <Option value="completed">Completed</Option>
                  <Option value="processing">Processing</Option>
                  <Option value="pending">Pending</Option>
                  <Option value="failed">Failed</Option>
                  <Option value="cancelled">Cancelled</Option>
                </Select>
              </Col>
              <Col xs={12} sm={6}>
                <RangePicker
                  value={dateRange}
                  onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
                  style={{ width: '100%' }}
                  placeholder={['Start Date', 'End Date']}
                />
              </Col>
              <Col xs={24} sm={6}>
                <Space>
                  <Button
                    icon={<ReloadOutlined />}
                    loading={refreshing}
                    onClick={() => fetchReports(false)}
                  >
                    Refresh
                  </Button>
                  <Button
                    icon={<FilterOutlined />}
                    onClick={() => {
                      setSearchText('')
                      setStatusFilter('all')
                      setDateRange(null)
                    }}
                  >
                    Clear Filters
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>

          {/* Reports Table */}
          <Card>
            <Table
              columns={columns}
              dataSource={filteredReports}
              rowKey="job_id"
              loading={loading}
              locale={{
                emptyText: (
                  <div className="py-8">
                    <FileTextOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
                    <div className="mt-4">
                      <Title level={4} type="secondary">No reports found</Title>
                      <Paragraph type="secondary">
                        {searchText || statusFilter !== 'all' || dateRange 
                          ? 'Try adjusting your filters or search terms.'
                          : 'Upload your first PCAP file to generate analysis reports.'
                        }
                      </Paragraph>
                      {!searchText && statusFilter === 'all' && !dateRange && (
                        <Link href="/upload">
                          <Button type="primary" icon={<CloudUploadOutlined />}>
                            Upload PCAP File
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                )
              }}
              pagination={{
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => 
                  `${range[0]}-${range[1]} of ${total} reports`,
                pageSizeOptions: ['10', '20', '50', '100'],
                defaultPageSize: 20,
              }}
              scroll={{ x: 'max-content' }}
              size="middle"
            />
          </Card>
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
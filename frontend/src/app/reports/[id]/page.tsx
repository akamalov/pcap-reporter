'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { 
  Layout, 
  Typography, 
  Card, 
  Button, 
  Space, 
  Row, 
  Col,
  Tag,
  Descriptions,
  Table,
  Progress,
  Alert,
  Spin,
  Divider,
  Tabs,
  Statistic,
  List,
  App,
  Tooltip,
  Badge,
  Result
} from 'antd'
import { 
  DownloadOutlined,
  ReloadOutlined,
  FileTextOutlined,
  BarChartOutlined,
  SafetyOutlined,
  GlobalOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  EyeOutlined,
  ArrowLeftOutlined
} from '@ant-design/icons'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip as RechartsTooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Area,
  AreaChart
} from 'recharts'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { ApiService, handleApiError, formatFileSize, formatDuration, getSeverityColor } from '@/lib/api'
import type { AnalysisResult } from '@/lib/api'
import { AppHeader } from '@/components/AppHeader'
import { LoadingOverlay, ChartSkeleton } from '@/components/LoadingOverlay'
import { ErrorBoundary, useErrorHandler } from '@/components/ErrorBoundary'
import NetworkDiagramViewer from '@/components/NetworkDiagramViewer'
import AdvancedSearch from '@/components/AdvancedSearch'

dayjs.extend(relativeTime)

const { Content, Footer } = Layout
const { Title, Paragraph, Text } = Typography

function ReportViewPageContent() {
  const params = useParams()
  const router = useRouter()
  const reportId = params.id as string
  const { message } = App.useApp()
  
  const [report, setReport] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const { error, handleError, retry, reset } = useErrorHandler()

  // Fetch report data with enhanced error handling
  const fetchReport = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true)
    setRefreshing(true)
    reset() // Clear any previous errors
    
    try {
      const data = await ApiService.getAnalysisResult(reportId)
      setReport(data)
    } catch (error: any) {
      console.error('Error fetching report:', error)
      if (error.response?.status === 404) {
        handleError('Report not found')
        // Don't redirect immediately, let user see the error
        setTimeout(() => router.push('/reports'), 5000)
        return
      }
      handleError(error)
      // Show user-friendly error message
      message.error({
        content: handleApiError(error),
        duration: 5,
        style: { marginTop: '20vh' }
      })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [reportId, router, handleError, reset])

  // Download report as PDF with better error handling
  const handleDownload = useCallback(async () => {
    if (!report) return
    
    try {
      const blob = await ApiService.downloadReport(reportId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const filename = report.filename || 'analysis_report'
      a.download = `${filename.replace(/\.[^/.]+$/, '')}_analysis_report.pdf`
      a.setAttribute('aria-label', 'Download analysis report as PDF')
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      message.success('Report downloaded successfully')
    } catch (error: any) {
      console.error('Error downloading report:', error)
      handleError(error)
      message.error(handleApiError(error))
    }
  }, [reportId, report, handleError])

  useEffect(() => {
    if (reportId) {
      fetchReport()
    }
  }, [reportId, fetchReport])

  // Retry function for error recovery
  const handleRetry = useCallback(() => {
    if (retry()) {
      fetchReport()
    }
  }, [retry, fetchReport])

  // Handle loading state
  if (loading) {
    return (
      <Layout className="min-h-screen">
        <AppHeader 
          title="Analysis Report" 
          showBackButton 
          backUrl="/reports"
        />
        <Content className="bg-gray-50 dark:bg-gray-900 p-4 md:p-6">
          <div className="max-w-7xl mx-auto">
            <LoadingOverlay 
              message="Loading analysis report..." 
              minHeight={400}
            />
          </div>
        </Content>
      </Layout>
    )
  }

  // Handle error state
  if (error) {
    return (
      <Layout className="min-h-screen">
        <AppHeader 
          title="Analysis Report" 
          showBackButton 
          backUrl="/reports"
        />
        <Content className="bg-gray-50 dark:bg-gray-900 p-4 md:p-6">
          <div className="max-w-7xl mx-auto">
            <Result
              status="error"
              title="Failed to Load Report"
              subTitle={error}
              extra={[
                <Button type="primary" onClick={handleRetry} key="retry">
                  Try Again
                </Button>,
                <Link href="/reports" key="back">
                  <Button>Back to Reports</Button>
                </Link>
              ]}
            />
          </div>
        </Content>
      </Layout>
    )
  }

  // Handle report not found
  if (!report) {
    return (
      <Layout className="min-h-screen">
        <AppHeader 
          title="Analysis Report" 
          showBackButton 
          backUrl="/reports"
        />
        <Content className="bg-gray-50 dark:bg-gray-900 p-4 md:p-6">
          <div className="max-w-7xl mx-auto">
            <Result
              status="404"
              title="Report Not Found"
              subTitle="The requested analysis report could not be found."
              extra={
                <Link href="/reports">
                  <Button type="primary">Back to Reports</Button>
                </Link>
              }
            />
          </div>
        </Content>
      </Layout>
    )
  }

  // Prepare chart data
  const protocolChartData = Object.entries(report.protocols || {}).map(([protocol, count]) => ({
    protocol,
    count,
    percentage: ((count / report.total_packets) * 100).toFixed(1)
  }))

  const topTalkersData = report.performance_metrics?.top_talkers?.slice(0, 10).map(talker => ({
    ip: talker.ip,
    sent: talker.bytes_sent,
    received: talker.bytes_received,
    total: talker.total_bytes
  })) || []

  // Header actions
  const headerActions = (
    <>
      <Button
        icon={<ReloadOutlined />}
        loading={refreshing}
        onClick={() => fetchReport(false)}
        className="hidden sm:inline-flex"
        aria-label="Refresh report data"
      >
        Refresh
      </Button>
      <Button
        icon={<ReloadOutlined />}
        loading={refreshing}
        onClick={() => fetchReport(false)}
        className="sm:hidden"
        aria-label="Refresh report data"
      />
      <Button
        type="primary"
        icon={<DownloadOutlined />}
        onClick={handleDownload}
        disabled={report.status !== 'completed'}
        className="hidden sm:inline-flex"
        aria-label="Download PDF report"
      >
        Download PDF
      </Button>
      <Button
        type="primary"
        icon={<DownloadOutlined />}
        onClick={handleDownload}
        disabled={report.status !== 'completed'}
        className="sm:hidden"
        aria-label="Download PDF report"
      />
    </>
  )

  return (
    <Layout className="min-h-screen">
      <AppHeader 
        title="Analysis Report" 
        showBackButton 
        backUrl="/reports"
        actions={headerActions}
      />

      {/* Main Content */}
      <Content className="bg-gray-50 dark:bg-gray-900 p-4 md:p-6">
        <div className="max-w-7xl mx-auto" role="main" aria-label="Report analysis content">
          
          {/* Report Header */}
          <Card className="mb-6" aria-labelledby="report-header">
            <Row gutter={[24, 24]} align="middle">
              <Col xs={24} lg={12}>
                <div>
                  <Title level={2} className="mb-2" id="report-header">
                    {report.filename}
                  </Title>
                  <Space size="middle" wrap className="flex-wrap">
                    {report.status === 'completed' ? (
                      <Tag icon={<CheckCircleOutlined />} color="success" aria-label="Status: Completed">Completed</Tag>
                    ) : report.status === 'processing' ? (
                      <Tag icon={<ClockCircleOutlined />} color="processing" aria-label="Status: Processing">Processing</Tag>
                    ) : (
                      <Tag aria-label={`Status: ${report.status}`}>{report.status}</Tag>
                    )}
                    <Text type="secondary" className="text-xs sm:text-sm">
                      Job ID: {report.job_id}
                    </Text>
                    <Text type="secondary" className="text-xs sm:text-sm">
                      {formatFileSize(report.file_size)}
                    </Text>
                  </Space>
                </div>
              </Col>
              <Col xs={24} lg={12}>
                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={8}>
                    <Statistic
                      title="Total Packets"
                      value={report.total_packets}
                      prefix={<FileTextOutlined aria-hidden="true" />}
                    />
                  </Col>
                  <Col xs={24} sm={8}>
                    <Statistic
                      title="Unique IPs"
                      value={report.unique_ips}
                      prefix={<GlobalOutlined aria-hidden="true" />}
                    />
                  </Col>
                  <Col xs={24} sm={8}>
                    <Statistic
                      title="Duration"
                      value={formatDuration(report.duration)}
                      prefix={<ClockCircleOutlined aria-hidden="true" />}
                    />
                  </Col>
                </Row>
              </Col>
            </Row>
          </Card>

          {/* Main Content Tabs */}
          <Card>
            <Tabs 
              activeKey={activeTab} 
              onChange={setActiveTab} 
              size="large"
              aria-label="Report analysis sections"
              tabBarStyle={{ marginBottom: '24px' }}
              items={[
                {
                  key: 'overview',
                  label: 'Overview',
                  children: (
                    <div aria-label="Report overview and statistics">
                <Row gutter={[24, 24]}>
                  
                  {/* Basic Information */}
                  <Col xs={24} lg={12}>
                    <Card title="Analysis Details" size="small" aria-labelledby="analysis-details">
                      <Descriptions column={1} size="small" labelStyle={{ fontWeight: 'bold' }}>
                        <Descriptions.Item label="Filename">
                          <Text copyable className="break-all">{report.filename}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="File Size">{formatFileSize(report.file_size)}</Descriptions.Item>
                        <Descriptions.Item label="File Hash">
                          <Text copyable className="break-all font-mono text-xs">{report.file_hash}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="Analysis Type">
                          <Tag color="blue">{report.analysis_type}</Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label="Created">
                          <Tooltip title={dayjs(report.created_at).format('dddd, MMMM D, YYYY [at] h:mm:ss A')}>
                            {dayjs(report.created_at).format('YYYY-MM-DD HH:mm:ss')}
                          </Tooltip>
                        </Descriptions.Item>
                        {report.completed_at && (
                          <Descriptions.Item label="Completed">
                            <Tooltip title={dayjs(report.completed_at).format('dddd, MMMM D, YYYY [at] h:mm:ss A')}>
                              {dayjs(report.completed_at).format('YYYY-MM-DD HH:mm:ss')}
                            </Tooltip>
                          </Descriptions.Item>
                        )}
                        <Descriptions.Item label="Processing Time">
                          <Badge count={formatDuration(report.duration)} showZero color="green" />
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>
                  </Col>

                  {/* Quick Stats */}
                  <Col xs={24} lg={12}>
                    <Card title="Quick Statistics" size="small" aria-labelledby="quick-stats">
                      <Row gutter={[16, 16]}>
                        <Col xs={12} sm={6} lg={12}>
                          <Statistic
                            title="Total Packets"
                            value={report.total_packets}
                            suffix="packets"
                            valueStyle={{ fontSize: '1.25rem', fontWeight: 'bold' }}
                          />
                        </Col>
                        <Col xs={12} sm={6} lg={12}>
                          <Statistic
                            title="Unique IPs"
                            value={report.unique_ips}
                            suffix="addresses"
                            valueStyle={{ fontSize: '1.25rem', fontWeight: 'bold' }}
                          />
                        </Col>
                        <Col xs={12} sm={6} lg={12}>
                          <Statistic
                            title="Unique Ports"
                            value={report.unique_ports}
                            suffix="ports"
                            valueStyle={{ fontSize: '1.25rem', fontWeight: 'bold' }}
                          />
                        </Col>
                        <Col xs={12} sm={6} lg={12}>
                          <Statistic
                            title="Total Data"
                            value={formatFileSize(report.packet_sizes?.total_bytes || 0)}
                            valueStyle={{ fontSize: '1.25rem', fontWeight: 'bold' }}
                          />
                        </Col>
                      </Row>
                    </Card>
                  </Col>

                  {/* Protocol Distribution */}
                  <Col xs={24}>
                    <Card title="Protocol Distribution" size="small" aria-labelledby="protocol-distribution">
                      {protocolChartData.length > 0 ? (
                        <Row gutter={[24, 24]}>
                          <Col xs={24} lg={12}>
                            <div aria-label="Protocol distribution pie chart">
                              <ResponsiveContainer width="100%" height={300}>
                                <PieChart>
                                  <Pie
                                    data={protocolChartData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ protocol, percentage }) => `${protocol} (${percentage}%)`}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    dataKey="count"
                                  >
                                    {protocolChartData.map((entry, index) => (
                                      <Cell key={`cell-${index}`} fill={['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe', '#00c49f'][index % 6]} />
                                    ))}
                                  </Pie>
                                  <RechartsTooltip />
                                </PieChart>
                              </ResponsiveContainer>
                            </div>
                          </Col>
                          <Col xs={24} lg={12}>
                            <div aria-label="Protocol distribution bar chart">
                              <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={protocolChartData}>
                                  <CartesianGrid strokeDasharray="3 3" />
                                  <XAxis dataKey="protocol" />
                                  <YAxis />
                                  <RechartsTooltip />
                                  <Bar dataKey="count" fill="#8884d8" />
                                </BarChart>
                              </ResponsiveContainer>
                            </div>
                          </Col>
                        </Row>
                      ) : (
                        <ChartSkeleton height={300} showTitle={false} />
                      )}
                    </Card>
                  </Col>
                </Row>
                    </div>
                  )
                },
                {
                  key: 'protocols',
                  label: 'Protocol Analysis',
                  children: (
                    <div aria-label="Detailed protocol analysis">
                <Row gutter={[24, 24]}>
                  
                  {/* TCP Analysis */}
                  {report.protocol_analysis?.tcp && (
                    <Col xs={24}>
                      <Card title="TCP Analysis" size="small">
                        <Row gutter={[16, 16]}>
                          <Col xs={12} sm={6}>
                            <Statistic
                              title="Total Connections"
                              value={report.protocol_analysis.tcp.total_connections}
                            />
                          </Col>
                          <Col xs={12} sm={6}>
                            <Statistic
                              title="Established"
                              value={report.protocol_analysis.tcp.established_connections}
                              valueStyle={{ color: '#3f8600' }}
                            />
                          </Col>
                          <Col xs={12} sm={6}>
                            <Statistic
                              title="Failed"
                              value={report.protocol_analysis.tcp.failed_connections}
                              valueStyle={{ color: '#cf1322' }}
                            />
                          </Col>
                          <Col xs={12} sm={6}>
                            <Statistic
                              title="Avg Duration"
                              value={report.protocol_analysis.tcp.average_connection_duration}
                              suffix="s"
                            />
                          </Col>
                        </Row>
                        
                        {report.protocol_analysis.tcp.top_conversations && (
                          <div className="mt-4">
                            <Title level={5}>Top Conversations</Title>
                            <div className="overflow-x-auto">
                              <Table
                                dataSource={report.protocol_analysis.tcp.top_conversations}
                                size="small"
                                pagination={false}
                                scroll={{ x: 800 }}
                                rowKey={(record, index) => `tcp-conv-${record.src_ip}-${record.dst_ip}-${record.src_port}-${record.dst_port}-${index}`}
                                aria-label="TCP conversations table"
                                columns={[
                                  { 
                                    title: 'Source IP', 
                                    dataIndex: 'src_ip', 
                                    key: 'src_ip',
                                    render: (ip) => <Text copyable className="font-mono text-xs">{ip}</Text>
                                  },
                                  { title: 'Source Port', dataIndex: 'src_port', key: 'src_port', width: 100 },
                                  { 
                                    title: 'Destination IP', 
                                    dataIndex: 'dst_ip', 
                                    key: 'dst_ip',
                                    render: (ip) => <Text copyable className="font-mono text-xs">{ip}</Text>
                                  },
                                  { title: 'Destination Port', dataIndex: 'dst_port', key: 'dst_port', width: 120 },
                                  { 
                                    title: 'Packets', 
                                    dataIndex: 'packets', 
                                    key: 'packets', 
                                    sorter: (a, b) => a.packets - b.packets,
                                    render: (packets) => packets.toLocaleString()
                                  },
                                  { 
                                    title: 'Bytes', 
                                    dataIndex: 'bytes', 
                                    key: 'bytes', 
                                    render: (bytes) => formatFileSize(bytes), 
                                    sorter: (a, b) => a.bytes - b.bytes 
                                  },
                                ]}
                              />
                            </div>
                          </div>
                        )}
                      </Card>
                    </Col>
                  )}

                  {/* HTTP Analysis */}
                  {report.protocol_analysis?.http && (
                    <Col xs={24}>
                      <Card title="HTTP Analysis" size="small">
                        <Row gutter={[16, 16]}>
                          <Col xs={12} sm={6}>
                            <Statistic
                              title="Total Requests"
                              value={report.protocol_analysis.http.total_requests}
                            />
                          </Col>
                        </Row>
                        
                        <Row gutter={[24, 24]} className="mt-4">
                          <Col xs={24} lg={12}>
                            <Title level={5}>Status Codes</Title>
                            <List
                              size="small"
                              dataSource={Object.entries(report.protocol_analysis.http.status_codes || {})}
                              renderItem={([code, count]) => (
                                <List.Item>
                                  <Text strong>{code}</Text>
                                  <Tag>{count}</Tag>
                                </List.Item>
                              )}
                            />
                          </Col>
                          <Col xs={24} lg={12}>
                            <Title level={5}>HTTP Methods</Title>
                            <List
                              size="small"
                              dataSource={Object.entries(report.protocol_analysis.http.methods || {})}
                              renderItem={([method, count]) => (
                                <List.Item>
                                  <Text strong>{method}</Text>
                                  <Tag>{count}</Tag>
                                </List.Item>
                              )}
                            />
                          </Col>
                        </Row>
                      </Card>
                    </Col>
                  )}

                  {/* DNS Analysis */}
                  {report.protocol_analysis?.dns && (
                    <Col xs={24}>
                      <Card title="DNS Analysis" size="small">
                        <Row gutter={[16, 16]}>
                          <Col xs={12} sm={6}>
                            <Statistic
                              title="Total Queries"
                              value={report.protocol_analysis.dns.total_queries}
                            />
                          </Col>
                        </Row>
                        
                        <Row gutter={[24, 24]} className="mt-4">
                          <Col xs={24} lg={12}>
                            <Title level={5}>Query Types</Title>
                            <List
                              size="small"
                              dataSource={Object.entries(report.protocol_analysis.dns.query_types || {})}
                              renderItem={([type, count]) => (
                                <List.Item>
                                  <Text strong>{type}</Text>
                                  <Tag>{count}</Tag>
                                </List.Item>
                              )}
                            />
                          </Col>
                          <Col xs={24} lg={12}>
                            <Title level={5}>Top Domains</Title>
                            <List
                              size="small"
                              dataSource={report.protocol_analysis.dns.top_domains || []}
                              renderItem={(domain) => (
                                <List.Item>
                                  <Text strong>{domain.domain}</Text>
                                  <Tag>{domain.queries}</Tag>
                                </List.Item>
                              )}
                            />
                          </Col>
                        </Row>
                      </Card>
                    </Col>
                  )}
                </Row>
                    </div>
                  )
                },
                {
                  key: 'security',
                  label: 'Security Analysis',
                  children: (
                    <div aria-label="Security analysis and threats">
                <Row gutter={[24, 24]}>
                  
                  {/* Security Overview */}
                  <Col xs={24}>
                    <Card title="Security Overview" size="small">
                      <Row gutter={[16, 16]}>
                        <Col xs={8}>
                          <Statistic
                            title="Suspicious IPs"
                            value={report.security_analysis?.suspicious_ips?.length || 0}
                            prefix={<WarningOutlined />}
                            valueStyle={{ color: report.security_analysis?.suspicious_ips?.length ? '#cf1322' : '#3f8600' }}
                          />
                        </Col>
                        <Col xs={8}>
                          <Statistic
                            title="Port Scans"
                            value={report.security_analysis?.port_scans?.length || 0}
                            prefix={<SafetyOutlined />}
                            valueStyle={{ color: report.security_analysis?.port_scans?.length ? '#cf1322' : '#3f8600' }}
                          />
                        </Col>
                        <Col xs={8}>
                          <Statistic
                            title="Anomalies"
                            value={report.security_analysis?.anomalies?.length || 0}
                            prefix={<ExclamationCircleOutlined />}
                            valueStyle={{ color: report.security_analysis?.anomalies?.length ? '#cf1322' : '#3f8600' }}
                          />
                        </Col>
                      </Row>
                    </Card>
                  </Col>

                  {/* Suspicious IPs */}
                  {report.security_analysis?.suspicious_ips && report.security_analysis.suspicious_ips.length > 0 && (
                    <Col xs={24}>
                      <Card title="Suspicious IP Addresses" size="small" aria-labelledby="suspicious-ips">
                        <div className="overflow-x-auto">
                          <Table
                            dataSource={report.security_analysis.suspicious_ips}
                            size="small"
                            pagination={{ pageSize: 10, showSizeChanger: false }}
                            rowKey={(record, index) => `suspicious-ip-${record.ip}-${index}`}
                            aria-label="Suspicious IP addresses table"
                            scroll={{ x: 600 }}
                            columns={[
                              { 
                                title: 'IP Address', 
                                dataIndex: 'ip', 
                                key: 'ip',
                                render: (ip) => <Text copyable className="font-mono">{ip}</Text>
                              },
                              { 
                                title: 'Reason', 
                                dataIndex: 'reason', 
                                key: 'reason',
                                ellipsis: { showTitle: false },
                                render: (reason) => <Tooltip title={reason}><Text>{reason}</Text></Tooltip>
                              },
                              { 
                                title: 'Severity', 
                                dataIndex: 'severity', 
                                key: 'severity',
                                render: (severity) => (
                                  <Tag 
                                    color={getSeverityColor(severity)} 
                                    aria-label={`Severity level: ${severity}`}
                                  >
                                    {severity.toUpperCase()}
                                  </Tag>
                                )
                              },
                              { 
                                title: 'Occurrences', 
                                dataIndex: 'count', 
                                key: 'count',
                                render: (count) => <Badge count={count} showZero />
                              },
                            ]}
                          />
                        </div>
                      </Card>
                    </Col>
                  )}

                  {/* Port Scans */}
                  {report.security_analysis?.port_scans && report.security_analysis.port_scans.length > 0 && (
                    <Col xs={24}>
                      <Card title="Port Scan Detection" size="small">
                        <Table
                          dataSource={report.security_analysis.port_scans}
                          size="small"
                          pagination={false}
                          columns={[
                            { title: 'Scanner IP', dataIndex: 'scanner_ip', key: 'scanner_ip' },
                            { title: 'Target IP', dataIndex: 'target_ip', key: 'target_ip' },
                            { title: 'Ports Scanned', dataIndex: 'ports_scanned', key: 'ports_scanned' },
                            { title: 'Scan Type', dataIndex: 'scan_type', key: 'scan_type' },
                          ]}
                        />
                      </Card>
                    </Col>
                  )}

                  {/* Anomalies */}
                  {report.security_analysis?.anomalies && report.security_analysis.anomalies.length > 0 && (
                    <Col xs={24}>
                      <Card title="Network Anomalies" size="small">
                        <List
                          dataSource={report.security_analysis.anomalies}
                          renderItem={(anomaly) => (
                            <List.Item>
                              <List.Item.Meta
                                avatar={<Badge status="error" />}
                                title={
                                  <div className="flex items-center space-x-2">
                                    <Text strong>{anomaly.type}</Text>
                                    <Tag color={getSeverityColor(anomaly.severity)}>
                                      {anomaly.severity.toUpperCase()}
                                    </Tag>
                                  </div>
                                }
                                description={
                                  <div>
                                    <Paragraph className="mb-1">{anomaly.description}</Paragraph>
                                    <Text type="secondary" className="text-xs">
                                      {dayjs(anomaly.timestamp).format('YYYY-MM-DD HH:mm:ss')}
                                    </Text>
                                  </div>
                                }
                              />
                            </List.Item>
                          )}
                        />
                      </Card>
                    </Col>
                  )}

                  {/* No Security Issues */}
                  {(!report.security_analysis?.suspicious_ips?.length && 
                    !report.security_analysis?.port_scans?.length && 
                    !report.security_analysis?.anomalies?.length) && (
                    <Col xs={24}>
                      <Alert
                        message="No Security Issues Detected"
                        description="The analysis did not identify any suspicious activities, port scans, or network anomalies in this PCAP file."
                        type="success"
                        icon={<CheckCircleOutlined />}
                        showIcon
                      />
                    </Col>
                  )}
                </Row>
                    </div>
                  )
                },
                {
                  key: 'diagrams',
                  label: 'Network Diagrams',
                  children: (
                    <div aria-label="Network topology and flow diagrams">
                {report.status === 'processing' ? (
                  <ChartSkeleton height={600} showTitle={true} showLegend={true} />
                ) : (
                  <NetworkDiagramViewer
                    diagramData={report.analysis_results?.network_diagrams}
                    loading={false}
                    height={600}
                  />
                )}
                    </div>
                  )
                },
                {
                  key: 'performance',
                  label: 'Performance',
                  children: (
                    <div aria-label="Network performance metrics and analytics">
                <Row gutter={[24, 24]}>
                  
                  {/* Top Talkers */}
                  {topTalkersData.length > 0 ? (
                    <Col xs={24}>
                      <Card title="Top Talkers by Data Volume" size="small" aria-labelledby="top-talkers">
                        <div aria-label="Top talkers data volume chart">
                          <ResponsiveContainer width="100%" height={400}>
                            <BarChart data={topTalkersData}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis 
                                dataKey="ip" 
                                angle={-45}
                                textAnchor="end"
                                height={80}
                                fontSize={12}
                              />
                              <YAxis tickFormatter={(value) => formatFileSize(value)} />
                              <RechartsTooltip 
                                formatter={(value, name) => [formatFileSize(value as number), name]}
                                labelFormatter={(ip) => `IP: ${ip}`}
                              />
                              <Bar dataKey="sent" stackId="a" fill="#8884d8" name="Sent" />
                              <Bar dataKey="received" stackId="a" fill="#82ca9d" name="Received" />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </Card>
                    </Col>
                  ) : (
                    <Col xs={24}>
                      <Card title="Top Talkers by Data Volume" size="small">
                        <ChartSkeleton height={400} showTitle={false} />
                      </Card>
                    </Col>
                  )}

                  {/* Bandwidth Usage */}
                  {report.performance_metrics?.bandwidth_usage ? (
                    <Col xs={24}>
                      <Card title="Bandwidth Usage Over Time" size="small" aria-labelledby="bandwidth-usage">
                        <div aria-label="Bandwidth usage over time chart">
                          <ResponsiveContainer width="100%" height={300}>
                            <AreaChart data={report.performance_metrics.bandwidth_usage}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis 
                                dataKey="timestamp"
                                tickFormatter={(timestamp) => dayjs(timestamp).format('HH:mm:ss')}
                              />
                              <YAxis tickFormatter={(value) => `${formatFileSize(value)}/s`} />
                              <RechartsTooltip 
                                formatter={(value) => [`${formatFileSize(value as number)}/s`, 'Bandwidth']}
                                labelFormatter={(timestamp) => dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss')}
                              />
                              <Area 
                                type="monotone" 
                                dataKey="bytes_per_second" 
                                stroke="#8884d8" 
                                fill="#8884d8" 
                                fillOpacity={0.6}
                              />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>
                      </Card>
                    </Col>
                  ) : (
                    <Col xs={24}>
                      <Card title="Bandwidth Usage Over Time" size="small">
                        <ChartSkeleton height={300} showTitle={false} />
                      </Card>
                    </Col>
                  )}

                  {/* Packet Rate */}
                  {report.performance_metrics?.packet_rate ? (
                    <Col xs={24}>
                      <Card title="Packet Rate Over Time" size="small" aria-labelledby="packet-rate">
                        <div aria-label="Packet rate over time chart">
                          <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={report.performance_metrics.packet_rate}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis 
                                dataKey="timestamp"
                                tickFormatter={(timestamp) => dayjs(timestamp).format('HH:mm:ss')}
                              />
                              <YAxis tickFormatter={(value) => `${value} pps`} />
                              <RechartsTooltip 
                                formatter={(value) => [`${value} pps`, 'Packet Rate']}
                                labelFormatter={(timestamp) => dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss')}
                              />
                              <Line 
                                type="monotone" 
                                dataKey="packets_per_second" 
                                stroke="#82ca9d" 
                                strokeWidth={2}
                                dot={false}
                              />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      </Card>
                    </Col>
                  ) : (
                    <Col xs={24}>
                      <Card title="Packet Rate Over Time" size="small">
                        <ChartSkeleton height={300} showTitle={false} />
                      </Card>
                    </Col>
                  )}
                </Row>
                    </div>
                  )
                },
                {
                  key: 'search',
                  label: 'Advanced Search',
                  children: (
                    <div aria-label="Advanced search and filtering capabilities">
                      <AdvancedSearch 
                        jobId={reportId}
                        onResults={(results) => {
                          message.success(`Found ${results.filteredCount} results in ${results.queryTimeMs.toFixed(1)}ms`)
                        }}
                      />
                    </div>
                  )
                }
              ]}
            />
          </Card>
        </div>
      </Content>

      {/* Footer */}
      <Footer className="bg-slate-800 text-white text-center p-4" role="contentinfo">
        <Text className="text-gray-400 text-sm">
          © 2024 PCAP Reporter. Built with Next.js, FastAPI, and modern web technologies.
        </Text>
      </Footer>
    </Layout>
  )
}

// Main component with error boundary
export default function ReportViewPage() {
  return (
    <App>
      <ErrorBoundary 
        showDetails={process.env.NODE_ENV === 'development'}
        onError={(error, errorInfo) => {
          console.error('Report page error:', error, errorInfo)
          // In production, send to error reporting service
        }}
      >
        <ReportViewPageContent />
      </ErrorBoundary>
    </App>
  )
} 
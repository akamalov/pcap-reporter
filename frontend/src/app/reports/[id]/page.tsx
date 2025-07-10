'use client'

import React, { useState, useEffect } from 'react'
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
  message,
  Tooltip,
  Badge
} from 'antd'
import { 
  ArrowLeftOutlined,
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
  EyeOutlined
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
import { ThemeToggle } from '../../components/ThemeToggle'

dayjs.extend(relativeTime)

const { Header, Content, Footer } = Layout
const { Title, Paragraph, Text } = Typography
const { TabPane } = Tabs

export default function ReportViewPage() {
  const params = useParams()
  const router = useRouter()
  const reportId = params.id as string
  
  const [report, setReport] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')

  // Fetch report data
  const fetchReport = async (showLoading = true) => {
    if (showLoading) setLoading(true)
    setRefreshing(true)
    
    try {
      const data = await ApiService.getAnalysisResult(reportId)
      setReport(data)
    } catch (error: any) {
      console.error('Error fetching report:', error)
      if (error.response?.status === 404) {
        message.error('Report not found')
        router.push('/reports')
        return
      }
      message.error(handleApiError(error))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  // Download report as PDF
  const handleDownload = async () => {
    try {
      const blob = await ApiService.downloadReport(reportId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${report?.filename.replace(/\.[^/.]+$/, '')}_analysis_report.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      message.success('Report downloaded successfully')
    } catch (error: any) {
      console.error('Error downloading report:', error)
      message.error(handleApiError(error))
    }
  }

  useEffect(() => {
    if (reportId) {
      fetchReport()
    }
  }, [reportId])

  if (loading) {
    return (
      <Layout className="min-h-screen">
        <Content className="flex items-center justify-center">
          <Spin size="large" />
        </Content>
      </Layout>
    )
  }

  if (!report) {
    return (
      <Layout className="min-h-screen">
        <Content className="flex items-center justify-center">
          <div className="text-center">
            <Title level={3}>Report Not Found</Title>
            <Paragraph>The requested analysis report could not be found.</Paragraph>
            <Link href="/reports">
              <Button type="primary">Back to Reports</Button>
            </Link>
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

  return (
    <Layout className="min-h-screen">
      {/* Header */}
      <Header className="bg-slate-800 shadow-lg">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href="/reports">
              <Button type="text" icon={<ArrowLeftOutlined />} className="text-white">
                Back to Reports
              </Button>
            </Link>
            <GlobalOutlined className="text-white text-2xl" />
            <Title level={3} className="text-white mb-0">
              Analysis Report
            </Title>
          </div>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              loading={refreshing}
              onClick={() => fetchReport(false)}
            >
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleDownload}
              disabled={report.status !== 'completed'}
            >
              Download PDF
            </Button>
            <ThemeToggle />
          </Space>
        </div>
      </Header>

      {/* Main Content */}
      <Content className="bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          
          {/* Report Header */}
          <Card className="mb-6">
            <Row gutter={[24, 24]} align="middle">
              <Col xs={24} lg={12}>
                <div>
                  <Title level={2} className="mb-2">
                    {report.filename}
                  </Title>
                  <Space size="middle" wrap>
                    {report.status === 'completed' ? (
                      <Tag icon={<CheckCircleOutlined />} color="success">Completed</Tag>
                    ) : report.status === 'processing' ? (
                      <Tag icon={<ClockCircleOutlined />} color="processing">Processing</Tag>
                    ) : (
                      <Tag>{report.status}</Tag>
                    )}
                    <Text type="secondary">
                      Job ID: {report.job_id}
                    </Text>
                    <Text type="secondary">
                      {formatFileSize(report.file_size)}
                    </Text>
                  </Space>
                </div>
              </Col>
              <Col xs={24} lg={12}>
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title="Total Packets"
                      value={report.total_packets}
                      prefix={<FileTextOutlined />}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Unique IPs"
                      value={report.unique_ips}
                      prefix={<GlobalOutlined />}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Duration"
                      value={formatDuration(report.duration)}
                      prefix={<ClockCircleOutlined />}
                    />
                  </Col>
                </Row>
              </Col>
            </Row>
          </Card>

          {/* Main Content Tabs */}
          <Card>
            <Tabs activeKey={activeTab} onChange={setActiveTab} size="large">
              
              {/* Overview Tab */}
              <TabPane tab="Overview" key="overview">
                <Row gutter={[24, 24]}>
                  
                  {/* Basic Information */}
                  <Col xs={24} lg={12}>
                    <Card title="Analysis Details" size="small">
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="Filename">{report.filename}</Descriptions.Item>
                        <Descriptions.Item label="File Size">{formatFileSize(report.file_size)}</Descriptions.Item>
                        <Descriptions.Item label="File Hash">{report.file_hash}</Descriptions.Item>
                        <Descriptions.Item label="Analysis Type">{report.analysis_type}</Descriptions.Item>
                        <Descriptions.Item label="Created">{dayjs(report.created_at).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
                        {report.completed_at && (
                          <Descriptions.Item label="Completed">{dayjs(report.completed_at).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
                        )}
                        <Descriptions.Item label="Processing Time">{formatDuration(report.duration)}</Descriptions.Item>
                      </Descriptions>
                    </Card>
                  </Col>

                  {/* Quick Stats */}
                  <Col xs={24} lg={12}>
                    <Card title="Quick Statistics" size="small">
                      <Row gutter={[16, 16]}>
                        <Col span={12}>
                          <Statistic
                            title="Total Packets"
                            value={report.total_packets}
                            suffix="packets"
                          />
                        </Col>
                        <Col span={12}>
                          <Statistic
                            title="Unique IPs"
                            value={report.unique_ips}
                            suffix="addresses"
                          />
                        </Col>
                        <Col span={12}>
                          <Statistic
                            title="Unique Ports"
                            value={report.unique_ports}
                            suffix="ports"
                          />
                        </Col>
                        <Col span={12}>
                          <Statistic
                            title="Total Data"
                            value={formatFileSize(report.packet_sizes?.total_bytes || 0)}
                          />
                        </Col>
                      </Row>
                    </Card>
                  </Col>

                  {/* Protocol Distribution */}
                  <Col xs={24}>
                    <Card title="Protocol Distribution" size="small">
                      <Row gutter={[24, 24]}>
                        <Col xs={24} lg={12}>
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
                        </Col>
                        <Col xs={24} lg={12}>
                          <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={protocolChartData}>
                              <CartesianGrid strokeDasharray="3 3" />
                              <XAxis dataKey="protocol" />
                              <YAxis />
                              <RechartsTooltip />
                              <Bar dataKey="count" fill="#8884d8" />
                            </BarChart>
                          </ResponsiveContainer>
                        </Col>
                      </Row>
                    </Card>
                  </Col>
                </Row>
              </TabPane>

              {/* Protocol Analysis Tab */}
              <TabPane tab="Protocol Analysis" key="protocols">
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
                            <Table
                              dataSource={report.protocol_analysis.tcp.top_conversations}
                              size="small"
                              pagination={false}
                              scroll={{ x: 'max-content' }}
                              columns={[
                                { title: 'Source IP', dataIndex: 'src_ip', key: 'src_ip' },
                                { title: 'Source Port', dataIndex: 'src_port', key: 'src_port' },
                                { title: 'Destination IP', dataIndex: 'dst_ip', key: 'dst_ip' },
                                { title: 'Destination Port', dataIndex: 'dst_port', key: 'dst_port' },
                                { title: 'Packets', dataIndex: 'packets', key: 'packets', sorter: (a, b) => a.packets - b.packets },
                                { title: 'Bytes', dataIndex: 'bytes', key: 'bytes', render: (bytes) => formatFileSize(bytes), sorter: (a, b) => a.bytes - b.bytes },
                              ]}
                            />
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
              </TabPane>

              {/* Security Analysis Tab */}
              <TabPane tab="Security Analysis" key="security">
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
                      <Card title="Suspicious IP Addresses" size="small">
                        <Table
                          dataSource={report.security_analysis.suspicious_ips}
                          size="small"
                          pagination={false}
                          columns={[
                            { title: 'IP Address', dataIndex: 'ip', key: 'ip' },
                            { title: 'Reason', dataIndex: 'reason', key: 'reason' },
                            { 
                              title: 'Severity', 
                              dataIndex: 'severity', 
                              key: 'severity',
                              render: (severity) => <Tag color={getSeverityColor(severity)}>{severity.toUpperCase()}</Tag>
                            },
                            { title: 'Occurrences', dataIndex: 'count', key: 'count' },
                          ]}
                        />
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
              </TabPane>

              {/* Performance Tab */}
              <TabPane tab="Performance" key="performance">
                <Row gutter={[24, 24]}>
                  
                  {/* Top Talkers */}
                  {topTalkersData.length > 0 && (
                    <Col xs={24}>
                      <Card title="Top Talkers by Data Volume" size="small">
                        <ResponsiveContainer width="100%" height={400}>
                          <BarChart data={topTalkersData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="ip" />
                            <YAxis />
                            <RechartsTooltip formatter={(value) => formatFileSize(value as number)} />
                            <Bar dataKey="sent" stackId="a" fill="#8884d8" name="Sent" />
                            <Bar dataKey="received" stackId="a" fill="#82ca9d" name="Received" />
                          </BarChart>
                        </ResponsiveContainer>
                      </Card>
                    </Col>
                  )}

                  {/* Bandwidth Usage */}
                  {report.performance_metrics?.bandwidth_usage && (
                    <Col xs={24}>
                      <Card title="Bandwidth Usage Over Time" size="small">
                        <ResponsiveContainer width="100%" height={300}>
                          <AreaChart data={report.performance_metrics.bandwidth_usage}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="timestamp" />
                            <YAxis />
                            <RechartsTooltip formatter={(value) => `${formatFileSize(value as number)}/s`} />
                            <Area type="monotone" dataKey="bytes_per_second" stroke="#8884d8" fill="#8884d8" />
                          </AreaChart>
                        </ResponsiveContainer>
                      </Card>
                    </Col>
                  )}

                  {/* Packet Rate */}
                  {report.performance_metrics?.packet_rate && (
                    <Col xs={24}>
                      <Card title="Packet Rate Over Time" size="small">
                        <ResponsiveContainer width="100%" height={300}>
                          <LineChart data={report.performance_metrics.packet_rate}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="timestamp" />
                            <YAxis />
                            <RechartsTooltip formatter={(value) => `${value} pps`} />
                            <Line type="monotone" dataKey="packets_per_second" stroke="#82ca9d" />
                          </LineChart>
                        </ResponsiveContainer>
                      </Card>
                    </Col>
                  )}
                </Row>
              </TabPane>
            </Tabs>
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
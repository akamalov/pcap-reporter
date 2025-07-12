import axios, { AxiosResponse, AxiosError } from 'axios'

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add any auth headers or request modifications here
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error: AxiosError) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Handle unauthorized access
      console.error('Unauthorized access')
    } else if (error.response?.status === 500) {
      // Handle server errors
      console.error('Server error:', error.response.data)
    }
    return Promise.reject(error)
  }
)

// Types
export interface AnalysisJob {
  job_id: string
  filename: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  file_size: number
  created_at: string
  updated_at: string
  completed_at?: string
  analysis_type: string
  priority: string
  progress?: number
  error_message?: string
  total_packets?: number
  duration?: number
  protocols?: string[]
}

export interface ReportsStats {
  total_reports: number
  completed_reports: number
  processing_reports: number
  failed_reports: number
  total_packets_analyzed: number
  total_data_processed: number
}

export interface AnalysisResult {
  job_id: string
  filename: string
  status: string
  file_size: number
  created_at: string
  completed_at?: string
  analysis_type: string
  total_packets: number
  duration: number
  file_hash: string
  unique_ips: number
  unique_ports: number
  protocols: Record<string, number>
  packet_sizes: {
    min: number
    max: number
    avg: number
    total_bytes: number
  }
  protocol_analysis?: {
    tcp?: {
      total_connections: number
      established_connections: number
      failed_connections: number
      average_connection_duration: number
      top_conversations: Array<{
        src_ip: string
        dst_ip: string
        src_port: number
        dst_port: number
        packets: number
        bytes: number
      }>
    }
    udp?: {
      total_flows: number
      top_talkers: Array<{
        ip: string
        packets: number
        bytes: number
      }>
    }
    http?: {
      total_requests: number
      status_codes: Record<string, number>
      top_domains: Array<{
        domain: string
        requests: number
      }>
      methods: Record<string, number>
    }
    dns?: {
      total_queries: number
      query_types: Record<string, number>
      top_domains: Array<{
        domain: string
        queries: number
      }>
      response_codes: Record<string, number>
    }
  }
  security_analysis?: {
    suspicious_ips: Array<{
      ip: string
      reason: string
      severity: 'low' | 'medium' | 'high'
      count: number
    }>
    port_scans: Array<{
      scanner_ip: string
      target_ip: string
      ports_scanned: number
      scan_type: string
    }>
    anomalies: Array<{
      type: string
      description: string
      severity: 'low' | 'medium' | 'high'
      timestamp: string
    }>
  }
  performance_metrics?: {
    bandwidth_usage: Array<{
      timestamp: string
      bytes_per_second: number
    }>
    packet_rate: Array<{
      timestamp: string
      packets_per_second: number
    }>
    top_talkers: Array<{
      ip: string
      bytes_sent: number
      bytes_received: number
      total_bytes: number
    }>
  }
  analysis_results?: {
    network_diagrams?: {
      network_topology?: string
      protocol_flow?: string
      security_incidents?: string
      performance_analysis?: string
      _metadata?: {
        generated_at?: string
        diagram_count?: number
        generator_version?: string
        error?: string
      }
      error?: string
    }
  }
}

export interface UploadResponse {
  job_id: string
  status: string
  filename: string
  file_size: number
  created_at: string
  estimated_completion: string
  analysis_type: string
  priority: string
}

export interface ApiError {
  detail: {
    error: string
    code?: string
    timestamp?: string
  }
}

// API Service Class
export class ApiService {
  
  // Analysis endpoints
  static async submitAnalysis(
    file: File, 
    analysisType: string = 'comprehensive',
    priority: string = 'normal'
  ): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('analysis_type', analysisType)
    formData.append('priority', priority)

    const response = await apiClient.post('/api/v1/analysis/submit', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  // Get all reports (equivalent to getAnalysisJobs)
  static async getAnalysisJobs(): Promise<{ jobs: AnalysisJob[], stats: ReportsStats }> {
    const response = await apiClient.get('/api/v1/reports/')
    // Transform the backend response to match frontend expectations
    const reports = response.data.reports || []
    const jobs = reports.map((report: any) => ({
      job_id: report.job_id,
      filename: report.original_filename || report.filename,
      status: report.status,
      file_size: report.file_size,
      created_at: report.created_at,
      updated_at: report.updated_at,
      completed_at: report.completed_at,
      analysis_type: 'comprehensive', // Default since backend doesn't store this
      priority: 'normal', // Default since backend doesn't store this
      progress: report.status === 'completed' ? 100 : report.status === 'processing' ? 50 : 0,
      error_message: report.error_message,
      total_packets: report.analysis_results?.total_packets,
      duration: report.processing_time,
      protocols: report.analysis_results?.protocols ? Object.keys(report.analysis_results.protocols) : []
    }))
    
    // Calculate stats
    const stats = {
      total_reports: reports.length,
      completed_reports: reports.filter((r: any) => r.status === 'completed').length,
      processing_reports: reports.filter((r: any) => r.status === 'processing').length,
      failed_reports: reports.filter((r: any) => r.status === 'failed').length,
      total_packets_analyzed: reports.reduce((sum: number, r: any) => sum + (r.analysis_results?.total_packets || 0), 0),
      total_data_processed: reports.reduce((sum: number, r: any) => sum + (r.file_size || 0), 0)
    }
    
    return { jobs, stats }
  }

  // Get specific report by ID (equivalent to getAnalysisResult)
  static async getAnalysisResult(jobId: string): Promise<AnalysisResult> {
    const response = await apiClient.get(`/api/v1/reports/${jobId}`)
    return response.data
  }

  // Get report status (uses same endpoint as getAnalysisResult)
  static async getAnalysisStatus(jobId: string): Promise<AnalysisJob> {
    const response = await apiClient.get(`/api/v1/reports/${jobId}`)
    const report = response.data
    return {
      job_id: report.job_id,
      filename: report.original_filename || report.filename,
      status: report.status,
      file_size: report.file_size,
      created_at: report.created_at,
      updated_at: report.updated_at,
      completed_at: report.completed_at,
      analysis_type: 'comprehensive',
      priority: 'normal',
      progress: report.status === 'completed' ? 100 : report.status === 'processing' ? 50 : 0,
      error_message: report.error_message,
      total_packets: report.analysis_results?.total_packets,
      duration: report.processing_time,
      protocols: report.analysis_results?.protocols ? Object.keys(report.analysis_results.protocols) : []
    }
  }

  static async deleteAnalysis(jobId: string): Promise<void> {
    await apiClient.delete(`/api/v1/reports/${jobId}`)
  }

  static async downloadReport(jobId: string): Promise<Blob> {
    const response = await apiClient.get(`/api/v1/export/pdf/${jobId}`, {
      responseType: 'blob',
    })
    return response.data
  }

  static async cancelAnalysis(jobId: string): Promise<void> {
    // Backend doesn't have cancel endpoint, so we'll use delete
    await apiClient.delete(`/api/v1/reports/${jobId}`)
  }

  // Health check endpoint (use root health endpoint)
  static async healthCheck(): Promise<{ status: string, timestamp: string }> {
    const response = await apiClient.get('/health')
    return {
      status: response.data.status === 'healthy' ? 'healthy' : 'unhealthy',
      timestamp: response.data.timestamp || new Date().toISOString()
    }
  }

  // System info endpoint (mock response since backend doesn't have this)
  static async getSystemInfo(): Promise<{
    version: string
    uptime: number
    active_jobs: number
    total_analyses: number
  }> {
    // Get health info first
    const healthResponse = await apiClient.get('/health')
    const reportsResponse = await apiClient.get('/api/v1/reports/')
    
    const reports = reportsResponse.data.reports || []
    return {
      version: '1.0.0',
      uptime: 0, // Backend doesn't provide this
      active_jobs: reports.filter((r: any) => r.status === 'processing' || r.status === 'pending').length,
      total_analyses: reports.length
    }
  }
}

// Utility functions
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
}

export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'completed': return 'green'
    case 'processing': return 'blue'
    case 'pending': return 'orange'
    case 'failed': return 'red'
    case 'cancelled': return 'gray'
    default: return 'default'
  }
}

export const getSeverityColor = (severity: string): string => {
  switch (severity) {
    case 'high': return 'red'
    case 'medium': return 'orange'
    case 'low': return 'yellow'
    default: return 'default'
  }
}

// Error handling utility
export const handleApiError = (error: any): string => {
  if (error.response?.data?.detail?.error) {
    return error.response.data.detail.error
  } else if (error.response?.data?.message) {
    return error.response.data.message
  } else if (error.message) {
    return error.message
  } else {
    return 'An unexpected error occurred'
  }
}

export default ApiService 
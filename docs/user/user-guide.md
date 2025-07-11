# PCAP Reporter User Guide

Welcome to PCAP Reporter! This guide will help you get started with analyzing network packet capture files using our web-based interface.

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Uploading PCAP Files](#uploading-pcap-files)
3. [Analysis Options](#analysis-options)
4. [Viewing Results](#viewing-results)
5. [Managing Reports](#managing-reports)
6. [Advanced Features](#advanced-features)
7. [Tips and Best Practices](#tips-and-best-practices)

## 🚀 Getting Started

### Accessing PCAP Reporter

1. Open your web browser
2. Navigate to your PCAP Reporter instance (e.g., `https://pcap-reporter.yourdomain.com`)
3. The dashboard will load showing recent reports and system status

### Dashboard Overview

The main dashboard provides:
- **Upload Section**: Drag and drop area for PCAP files
- **Recent Reports**: List of your recent analysis reports
- **System Status**: Real-time system health indicators
- **Quick Stats**: Overview of total reports and processing status

## 📁 Uploading PCAP Files

### Supported File Types

PCAP Reporter supports the following file formats:
- `.pcap` - Standard PCAP format
- `.pcapng` - Next Generation PCAP format
- `.cap` - Alternative PCAP extension

### Upload Methods

#### Method 1: Drag and Drop
1. Locate your PCAP file in your file manager
2. Drag the file to the upload area on the dashboard
3. Drop the file when the area highlights

#### Method 2: File Browser
1. Click the "Choose File" button in the upload area
2. Browse to your PCAP file location
3. Select the file and click "Open"

### File Size Limits

- **Maximum file size**: 2GB per file
- **Large files** (>100MB): Automatically processed using streaming for optimal performance
- **Processing time**: Varies based on file size and complexity

## ⚙️ Analysis Options

When uploading a file, you can configure various analysis options:

### Basic Analysis
- **Protocol Distribution**: Breakdown of protocols found in the capture
- **Traffic Statistics**: Packet counts, bytes transferred, duration
- **Top Talkers**: Most active source and destination addresses

### Advanced Analysis
- **Deep Packet Inspection**: Detailed protocol analysis
- **Security Analysis**: Detection of suspicious patterns
- **Performance Metrics**: Latency, throughput, and quality metrics
- **Conversation Analysis**: Communication patterns between hosts

### Custom Options
- **Time Range**: Analyze specific time periods within the capture
- **Filter Expressions**: Apply BPF (Berkeley Packet Filter) expressions
- **Protocol Focus**: Concentrate analysis on specific protocols

## 📊 Viewing Results

### Report Sections

Each analysis report contains several sections:

#### 1. Executive Summary
- High-level overview of the capture
- Key findings and statistics
- Processing time and file information

#### 2. Protocol Analysis
- Protocol distribution charts
- Detailed protocol breakdowns
- Protocol-specific statistics

#### 3. Traffic Analysis
- Traffic patterns over time
- Peak usage periods
- Bandwidth utilization

#### 4. Network Topology
- Visual representation of network communications
- Host relationships and traffic flows
- Geographic distribution (if applicable)

#### 5. Security Insights
- Potential security issues
- Anomaly detection results
- Suspicious traffic patterns

#### 6. Performance Metrics
- Response times and latency
- Throughput measurements
- Quality of service indicators

### Interactive Features

- **Zoom and Pan**: Interactive charts for detailed examination
- **Filtering**: Click on legend items to show/hide data series
- **Export**: Download charts as images or data as CSV
- **Search**: Find specific information within reports

## 📋 Managing Reports

### Report List

The reports page shows all your analysis reports with:
- **Status**: Current processing status (Pending, Processing, Completed, Failed)
- **Created**: When the analysis was started
- **File Info**: Original filename and size
- **Actions**: View, download, or delete options

### Report Status

- **🟡 Pending**: Report is queued for processing
- **🔵 Processing**: Analysis is currently running
- **🟢 Completed**: Analysis finished successfully
- **🔴 Failed**: Analysis encountered an error

### Real-time Updates

Reports update in real-time during processing:
- **Progress Bar**: Shows analysis completion percentage
- **Status Messages**: Current processing step
- **Estimated Time**: Remaining processing time

## 🔧 Advanced Features

### WebSocket Real-time Updates

PCAP Reporter provides real-time updates during analysis:
- Live progress tracking
- Instant status notifications
- Real-time error reporting

### Batch Processing

For multiple files:
1. Upload files one by one or use multiple selections
2. Each file is processed independently
3. Monitor progress from the reports page

### API Access

For programmatic access, see the [API Reference](../api/api-reference.md).

## 💡 Tips and Best Practices

### File Preparation

1. **Verify File Integrity**: Ensure PCAP files are not corrupted
2. **Reasonable Size**: For faster processing, consider splitting very large files
3. **Meaningful Names**: Use descriptive filenames for easier identification

### Analysis Configuration

1. **Start Simple**: Begin with basic analysis for overview
2. **Targeted Analysis**: Use filters for specific investigations
3. **Time Ranges**: Focus on relevant time periods for efficiency

### Performance Optimization

1. **Network Connection**: Ensure stable internet connection for uploads
2. **Browser Compatibility**: Use modern browsers for best experience
3. **File Management**: Regularly clean up old reports to save space

### Troubleshooting

1. **Upload Issues**: Check file format and size limits
2. **Processing Delays**: Large files may take significant time
3. **Browser Issues**: Try refreshing or using a different browser

For detailed troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).

## 🆘 Getting Help

If you encounter issues or have questions:

1. Check the [FAQ](faq.md) for common questions
2. Review the [Troubleshooting Guide](troubleshooting.md)
3. Contact your system administrator
4. Report bugs through the issue tracker

## 📚 Next Steps

- Learn about [API access](../api/api-reference.md) for automation
- Explore [advanced configuration](../deployment/production.md) options
- Contribute to the project via the [Contributing Guide](../development/contributing.md)

---

*Need help? Check our [FAQ](faq.md) or [Troubleshooting Guide](troubleshooting.md)* 
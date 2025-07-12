'use client';

import React, { useState } from 'react';
import { Tabs, Card, Empty, Alert, Space, Tag, Tooltip, Button } from 'antd';
import { 
  ShareAltOutlined, 
  SafetyCertificateOutlined, 
  DashboardOutlined,
  PartitionOutlined,
  InfoCircleOutlined,
  DownloadOutlined 
} from '@ant-design/icons';
import MermaidDiagram from './MermaidDiagram';

interface NetworkDiagramData {
  network_topology?: string;
  protocol_flow?: string;
  security_incidents?: string;
  performance_analysis?: string;
  _metadata?: {
    generated_at?: string;
    diagram_count?: number;
    generator_version?: string;
    error?: string;
  };
  error?: string;
}

interface NetworkDiagramViewerProps {
  /** Network diagram data from analysis results */
  diagramData?: NetworkDiagramData | null;
  /** Whether diagrams are still being generated */
  loading?: boolean;
  /** Custom height for diagram containers */
  height?: number;
  /** Custom CSS class */
  className?: string;
}

export const NetworkDiagramViewer: React.FC<NetworkDiagramViewerProps> = ({
  diagramData,
  loading = false,
  height = 500,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState<string>('topology');

  // Handle case where no diagram data is available
  if (!diagramData && !loading) {
    return (
      <Card 
        title="Network Diagrams" 
        className={className}
        bodyStyle={{ textAlign: 'center', padding: '48px 24px' }}
      >
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No network diagrams available for this analysis"
        />
      </Card>
    );
  }

  // Handle loading state
  if (loading) {
    return (
      <Card 
        title="Network Diagrams" 
        className={className}
        loading={true}
        bodyStyle={{ minHeight: `${height}px` }}
      >
        <div style={{ textAlign: 'center', padding: '48px 24px' }}>
          Generating network diagrams...
        </div>
      </Card>
    );
  }

  // Handle error state
  if (diagramData?.error || diagramData?._metadata?.error) {
    const errorMessage = diagramData.error || diagramData._metadata?.error || 'Unknown error';
    return (
      <Card title="Network Diagrams" className={className}>
        <Alert
          message="Diagram Generation Error"
          description={`Failed to generate network diagrams: ${errorMessage}`}
          type="error"
          showIcon
        />
      </Card>
    );
  }

  // Define available diagram types with their configurations
  const diagramTypes = [
    {
      key: 'topology',
      label: 'Network Topology',
      icon: <ShareAltOutlined />,
      definition: diagramData?.network_topology,
      description: 'Shows network hosts, connections, and traffic patterns',
      color: '#1890ff'
    },
    {
      key: 'protocol',
      label: 'Protocol Flow',
      icon: <PartitionOutlined />,
      definition: diagramData?.protocol_flow,
      description: 'Sequence diagram of communication patterns',
      color: '#52c41a'
    },
    {
      key: 'security',
      label: 'Security Analysis',
      icon: <SafetyCertificateOutlined />,
      definition: diagramData?.security_incidents,
      description: 'Highlights security threats and incidents',
      color: '#ff4d4f'
    },
    {
      key: 'performance',
      label: 'Performance Issues',
      icon: <DashboardOutlined />,
      definition: diagramData?.performance_analysis,
      description: 'Shows performance bottlenecks and issues',
      color: '#fa8c16'
    }
  ];

  // Filter to only include diagrams that have definitions
  const availableDiagrams = diagramTypes.filter(diagram => 
    diagram.definition && 
    diagram.definition.trim() && 
    !diagram.definition.includes('No ') && // Filter out "No data" diagrams
    !diagram.definition.includes('Error')
  );

  // If no diagrams are available, show empty state
  if (availableDiagrams.length === 0) {
    return (
      <Card 
        title="Network Diagrams" 
        className={className}
        bodyStyle={{ textAlign: 'center', padding: '48px 24px' }}
      >
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No network diagrams could be generated from this analysis"
        />
      </Card>
    );
  }

  // Download all diagrams as a ZIP file
  const handleDownloadAll = async () => {
    try {
      // This would typically integrate with a backend endpoint
      // For now, we'll download individual SVGs
      availableDiagrams.forEach((diagram, index) => {
        setTimeout(() => {
          // Trigger download for each diagram
          const event = new CustomEvent('download-diagram', { 
            detail: { 
              type: diagram.key, 
              definition: diagram.definition,
              title: diagram.label 
            } 
          });
          document.dispatchEvent(event);
        }, index * 500); // Stagger downloads
      });
    } catch (error) {
      console.error('Failed to download diagrams:', error);
    }
  };

  // Build tab items
  const tabItems = availableDiagrams.map(diagram => ({
    key: diagram.key,
    label: (
      <Space>
        {diagram.icon}
        <span>{diagram.label}</span>
        <Tag color={diagram.color} style={{ marginLeft: 4 }}>
          {diagram.definition?.split('\n').length || 0} lines
        </Tag>
      </Space>
    ),
    children: (
      <div style={{ position: 'relative' }}>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Tooltip title={diagram.description}>
              <InfoCircleOutlined style={{ color: '#666' }} />
            </Tooltip>
            <span style={{ color: '#666', fontSize: '14px' }}>
              {diagram.description}
            </span>
          </div>
        </div>
        
        <MermaidDiagram
          definition={diagram.definition || ''}
          title={diagram.label}
          height={height}
          theme="default"
          showDownload={true}
          showFullscreen={true}
          onError={(error) => {
            console.error(`Error rendering ${diagram.label}:`, error);
          }}
        />
      </div>
    )
  }));

  // Generate metadata display
  const metadata = diagramData?._metadata;
  const metadataInfo = metadata ? (
    <div style={{ 
      fontSize: '12px', 
      color: '#666', 
      padding: '8px 16px', 
      borderTop: '1px solid #f0f0f0',
      background: '#fafafa'
    }}>
      <Space split={<span style={{ color: '#d9d9d9' }}>•</span>}>
        {metadata.diagram_count && (
          <span>{metadata.diagram_count} diagrams generated</span>
        )}
        {metadata.generated_at && (
          <span>Generated: {new Date(metadata.generated_at).toLocaleString()}</span>
        )}
        {metadata.generator_version && (
          <span>Version: {metadata.generator_version}</span>
        )}
      </Space>
    </div>
  ) : null;

  return (
    <Card
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <ShareAltOutlined />
            <span>Network Diagrams</span>
            <Tag color="blue">{availableDiagrams.length} available</Tag>
          </Space>
          
          {availableDiagrams.length > 1 && (
            <Tooltip title="Download all diagrams">
              <Button 
                type="default" 
                size="small"
                icon={<DownloadOutlined />}
                onClick={handleDownloadAll}
              >
                Download All
              </Button>
            </Tooltip>
          )}
        </div>
      }
      className={className}
      bodyStyle={{ padding: 0 }}
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        size="large"
        items={tabItems}
        style={{ minHeight: `${height + 100}px` }}
        tabBarStyle={{ 
          margin: 0, 
          paddingLeft: 16, 
          paddingRight: 16,
          background: '#fafafa'
        }}
      />
      
      {metadataInfo}
    </Card>
  );
};

export default NetworkDiagramViewer;
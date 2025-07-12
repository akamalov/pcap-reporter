'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Card, Spin, Alert, Button, Tooltip } from 'antd';
import { DownloadOutlined, FullscreenOutlined, ReloadOutlined } from '@ant-design/icons';

interface MermaidDiagramProps {
  /** Mermaid diagram definition string */
  definition: string;
  /** Title for the diagram */
  title?: string;
  /** Additional CSS class name */
  className?: string;
  /** Height of the diagram container */
  height?: number;
  /** Whether to show download button */
  showDownload?: boolean;
  /** Whether to show fullscreen button */
  showFullscreen?: boolean;
  /** Custom theme for the diagram */
  theme?: 'default' | 'dark' | 'forest' | 'neutral';
  /** Callback when diagram fails to render */
  onError?: (error: string) => void;
}

export const MermaidDiagram: React.FC<MermaidDiagramProps> = ({
  definition,
  title,
  className = '',
  height = 400,
  showDownload = true,
  showFullscreen = true,
  theme = 'default',
  onError
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mermaid, setMermaid] = useState<any>(null);
  const [diagramId] = useState(`mermaid-${Math.random().toString(36).substr(2, 9)}`);

  // Initialize Mermaid
  useEffect(() => {
    const initMermaid = async () => {
      try {
        const mermaidModule = await import('mermaid');
        const mermaidInstance = mermaidModule.default;
        
        // Configure Mermaid
        mermaidInstance.initialize({
          startOnLoad: false,
          theme: theme,
          securityLevel: 'strict',
          fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
          themeVariables: {
            primaryColor: '#1890ff',
            primaryTextColor: '#000',
            primaryBorderColor: '#d9d9d9',
            lineColor: '#666',
            secondaryColor: '#f0f0f0',
            tertiaryColor: '#fafafa'
          },
          flowchart: {
            useMaxWidth: true,
            htmlLabels: true,
            curve: 'basis'
          },
          sequence: {
            useMaxWidth: true,
            showSequenceNumbers: true,
            wrap: true,
            width: 150,
            height: 65,
            boxMargin: 10,
            boxTextMargin: 5,
            noteMargin: 10,
            messageMargin: 35
          },
          gantt: {
            useMaxWidth: true
          }
        });
        
        setMermaid(mermaidInstance);
      } catch (err) {
        const errorMsg = 'Failed to initialize Mermaid.js';
        setError(errorMsg);
        onError?.(errorMsg);
        console.error('Mermaid initialization error:', err);
      }
    };

    initMermaid();
  }, [theme, onError]);

  // Render diagram when mermaid is ready
  useEffect(() => {
    if (!mermaid || !definition || !containerRef.current) {
      return;
    }

    const renderDiagram = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Clear previous content
        if (containerRef.current) {
          containerRef.current.innerHTML = '';
        }

        // Validate definition
        if (!definition.trim()) {
          throw new Error('Empty diagram definition');
        }

        // Parse and render the diagram
        const { svg } = await mermaid.render(diagramId, definition);
        
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
          
          // Apply responsive sizing
          const svgElement = containerRef.current.querySelector('svg');
          if (svgElement) {
            svgElement.style.maxWidth = '100%';
            svgElement.style.height = 'auto';
            svgElement.style.display = 'block';
            svgElement.style.margin = '0 auto';
          }
        }

        setIsLoading(false);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to render diagram';
        setError(errorMsg);
        setIsLoading(false);
        onError?.(errorMsg);
        console.error('Mermaid rendering error:', err);
      }
    };

    renderDiagram();
  }, [mermaid, definition, diagramId, onError]);

  // Download diagram as SVG
  const handleDownload = () => {
    if (!containerRef.current) return;

    const svgElement = containerRef.current.querySelector('svg');
    if (svgElement) {
      const svgData = new XMLSerializer().serializeToString(svgElement);
      const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
      const svgUrl = URL.createObjectURL(svgBlob);
      
      const downloadLink = document.createElement('a');
      downloadLink.href = svgUrl;
      downloadLink.download = `${title || 'diagram'}.svg`;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
      URL.revokeObjectURL(svgUrl);
    }
  };

  // Open diagram in fullscreen
  const handleFullscreen = () => {
    if (!containerRef.current) return;

    const svgElement = containerRef.current.querySelector('svg');
    if (svgElement && svgElement.requestFullscreen) {
      svgElement.requestFullscreen().catch(console.error);
    }
  };

  // Reload diagram
  const handleReload = () => {
    if (containerRef.current) {
      containerRef.current.innerHTML = '';
      setError(null);
      setIsLoading(true);
    }
  };

  const cardActions = [];
  
  if (showDownload) {
    cardActions.push(
      <Tooltip title="Download as SVG" key="download">
        <Button 
          type="text" 
          icon={<DownloadOutlined />} 
          onClick={handleDownload}
          disabled={isLoading || !!error}
        />
      </Tooltip>
    );
  }

  if (showFullscreen) {
    cardActions.push(
      <Tooltip title="View Fullscreen" key="fullscreen">
        <Button 
          type="text" 
          icon={<FullscreenOutlined />} 
          onClick={handleFullscreen}
          disabled={isLoading || !!error}
        />
      </Tooltip>
    );
  }

  cardActions.push(
    <Tooltip title="Reload Diagram" key="reload">
      <Button 
        type="text" 
        icon={<ReloadOutlined />} 
        onClick={handleReload}
        disabled={isLoading}
      />
    </Tooltip>
  );

  return (
    <Card
      title={title}
      className={className}
      actions={cardActions.length > 0 ? cardActions : undefined}
      bodyStyle={{ 
        padding: isLoading || error ? '24px' : '16px',
        minHeight: `${height}px`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      {isLoading && (
        <div style={{ textAlign: 'center' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#666' }}>
            Rendering diagram...
          </div>
        </div>
      )}

      {error && (
        <Alert
          message="Diagram Rendering Error"
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" onClick={handleReload}>
              Retry
            </Button>
          }
        />
      )}

      <div
        ref={containerRef}
        style={{
          width: '100%',
          minHeight: error || isLoading ? 'auto' : `${height}px`,
          display: error || isLoading ? 'none' : 'block',
          overflow: 'auto'
        }}
      />
    </Card>
  );
};

export default MermaidDiagram;
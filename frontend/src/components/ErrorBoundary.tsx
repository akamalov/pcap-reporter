'use client';

import React from 'react';
import { Result, Button, Typography, Card, Space } from 'antd';
import { 
  BugOutlined, 
  ReloadOutlined, 
  HomeOutlined,
  ExclamationCircleOutlined 
} from '@ant-design/icons';

const { Paragraph, Text } = Typography;

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
  errorId?: string;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  /** Custom fallback component */
  fallback?: React.ComponentType<{ error: Error; retry: () => void }>;
  /** Callback when error occurs */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  /** Whether to show detailed error information */
  showDetails?: boolean;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Generate a unique error ID for tracking
    const errorId = `error_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    
    return {
      hasError: true,
      error,
      errorId
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to console for development
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // Update state with error info
    this.setState({
      error,
      errorInfo
    });

    // Call optional error callback
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // In production, you would send this to an error reporting service
    if (process.env.NODE_ENV === 'production') {
      // Example: sendErrorToService(error, errorInfo, this.state.errorId);
    }
  }

  handleRetry = () => {
    this.setState({ 
      hasError: false, 
      error: undefined, 
      errorInfo: undefined, 
      errorId: undefined 
    });
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        const FallbackComponent = this.props.fallback;
        return (
          <FallbackComponent 
            error={this.state.error!} 
            retry={this.handleRetry} 
          />
        );
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50 dark:bg-gray-900">
          <Card className="max-w-2xl w-full">
            <Result
              status="error"
              title="Something went wrong"
              subTitle="An unexpected error occurred. Our team has been notified."
              icon={<BugOutlined className="text-red-500" />}
              extra={
                <Space direction="vertical" size="middle" className="w-full">
                  <Space wrap>
                    <Button 
                      type="primary" 
                      icon={<ReloadOutlined />}
                      onClick={this.handleRetry}
                    >
                      Try Again
                    </Button>
                    <Button 
                      icon={<HomeOutlined />}
                      onClick={() => window.location.href = '/'}
                    >
                      Go Home
                    </Button>
                  </Space>
                  
                  {this.props.showDetails && this.state.error && (
                    <Card 
                      size="small" 
                      title={
                        <Space>
                          <ExclamationCircleOutlined />
                          Error Details
                        </Space>
                      }
                      className="text-left"
                    >
                      <Paragraph>
                        <Text strong>Error ID:</Text> {this.state.errorId}
                      </Paragraph>
                      <Paragraph>
                        <Text strong>Message:</Text> {this.state.error.message}
                      </Paragraph>
                      {process.env.NODE_ENV === 'development' && (
                        <>
                          <Paragraph>
                            <Text strong>Stack:</Text>
                          </Paragraph>
                          <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-auto max-h-40">
                            {this.state.error.stack}
                          </pre>
                        </>
                      )}
                    </Card>
                  )}
                </Space>
              }
            />
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

// Simple functional error component for specific use cases
interface SimpleErrorDisplayProps {
  /** Error message to display */
  message: string;
  /** Optional description */
  description?: string;
  /** Retry callback */
  onRetry?: () => void;
  /** Whether to show retry button */
  showRetry?: boolean;
  /** Error type for styling */
  type?: 'error' | 'warning' | 'info';
}

export const SimpleErrorDisplay: React.FC<SimpleErrorDisplayProps> = ({
  message,
  description,
  onRetry,
  showRetry = true,
  type = 'error'
}) => {
  return (
    <Result
      status={type}
      title={message}
      subTitle={description}
      extra={
        showRetry && onRetry && (
          <Button type="primary" onClick={onRetry} icon={<ReloadOutlined />}>
            Try Again
          </Button>
        )
      }
    />
  );
};

// Hook for error handling in functional components
export const useErrorHandler = () => {
  const [error, setError] = React.useState<string | null>(null);
  const [retryCount, setRetryCount] = React.useState(0);
  const maxRetries = 3;

  const handleError = React.useCallback((error: Error | string) => {
    const errorMessage = typeof error === 'string' ? error : error.message;
    setError(errorMessage);
    
    // Log error for debugging
    console.error('Error handled:', error);
  }, []);

  const retry = React.useCallback(() => {
    if (retryCount < maxRetries) {
      setError(null);
      setRetryCount(prev => prev + 1);
      return true;
    }
    return false;
  }, [retryCount, maxRetries]);

  const reset = React.useCallback(() => {
    setError(null);
    setRetryCount(0);
  }, []);

  return {
    error,
    retryCount,
    maxRetries,
    hasMaxRetries: retryCount >= maxRetries,
    handleError,
    retry,
    reset
  };
};

export default ErrorBoundary;
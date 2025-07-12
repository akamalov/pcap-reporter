'use client';

import React from 'react';
import { Layout, Typography, Button, Space } from 'antd';
import { ArrowLeftOutlined, GlobalOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { ThemeToggle } from './ThemeToggle';

const { Header } = Layout;
const { Title } = Typography;

interface AppHeaderProps {
  /** Page title to display */
  title?: string;
  /** Additional action buttons or components */
  actions?: React.ReactNode;
  /** Whether to show back button */
  showBackButton?: boolean;
  /** Back button destination (defaults to /reports) */
  backUrl?: string;
  /** Custom CSS class */
  className?: string;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  title = "PCAP Reporter",
  actions,
  showBackButton = false,
  backUrl = "/reports",
  className = ""
}) => {
  return (
    <Header className={`bg-slate-800 shadow-lg ${className}`}>
      <div className="max-w-7xl mx-auto px-4 lg:px-6 flex items-center justify-between h-16">
        
        {/* Left side - Logo and title */}
        <div className="flex items-center space-x-3 min-w-0 flex-1">
          {showBackButton && (
            <Link href={backUrl}>
              <Button 
                type="text" 
                icon={<ArrowLeftOutlined />} 
                className="text-white hover:bg-slate-700 transition-colors"
                aria-label="Go back"
              >
                <span className="hidden sm:inline">Back</span>
              </Button>
            </Link>
          )}
          
          <Link href="/" className="flex items-center hover:opacity-80 transition-opacity">
            <GlobalOutlined className="text-white text-2xl flex-shrink-0" />
            <Title 
              level={3} 
              className="text-white mb-0 ml-3 truncate hidden sm:block"
              aria-label={`PCAP Reporter - ${title}`}
            >
              {title}
            </Title>
            <Title 
              level={4} 
              className="text-white mb-0 ml-2 truncate sm:hidden"
              aria-label={`PCAP Reporter - ${title}`}
            >
              PCAP
            </Title>
          </Link>
        </div>

        {/* Right side - Actions and theme toggle */}
        <div className="flex items-center space-x-2 flex-shrink-0">
          {actions && (
            <Space size="small" className="hidden xs:flex">
              {actions}
            </Space>
          )}
          
          {/* Mobile actions dropdown - can be implemented later */}
          {actions && (
            <div className="xs:hidden">
              {/* Mobile-optimized actions can be added here */}
            </div>
          )}
          
          <ThemeToggle />
        </div>
      </div>
    </Header>
  );
};

export default AppHeader;
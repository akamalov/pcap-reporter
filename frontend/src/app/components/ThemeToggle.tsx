'use client';

import React from 'react';
import { Button, Tooltip } from 'antd';
import { BulbOutlined, BulbFilled } from '@ant-design/icons';
import { useTheme } from './ThemeProvider';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  const handleToggle = () => {
    console.log('Theme toggle clicked, current theme:', theme);
    toggleTheme();
  };

  return (
    <Tooltip title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
      <Button
        type="text"
        icon={theme === 'light' ? <BulbOutlined /> : <BulbFilled />}
        onClick={handleToggle}
        style={{
          color: theme === 'light' ? '#fff' : '#fff',
          fontSize: '20px',
          padding: '12px 0',
          height: '40px',
          width: '40px',
          lineHeight: '1',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minWidth: 'auto',
          marginTop: '4px',
        }}
      />
    </Tooltip>
  );
}; 
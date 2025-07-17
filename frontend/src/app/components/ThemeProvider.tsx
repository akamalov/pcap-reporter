'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { ConfigProvider, theme, App } from 'antd';
import { AntdRegistry } from '@ant-design/nextjs-registry';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentTheme, setCurrentTheme] = useState<Theme>('light');

  useEffect(() => {
    // Load theme from localStorage on client side
    const savedTheme = localStorage.getItem('theme') as Theme;
    if (savedTheme) {
      setCurrentTheme(savedTheme);
    } else {
      // Check system preference
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      setCurrentTheme(systemTheme);
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setCurrentTheme(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  const { darkAlgorithm, defaultAlgorithm } = theme;

  const antdTheme = {
    algorithm: currentTheme === 'dark' ? darkAlgorithm : defaultAlgorithm,
    token: {
      colorPrimary: '#1890ff',
      colorSuccess: '#52c41a',
      colorWarning: '#faad14',
      colorError: '#f5222d',
      colorInfo: '#1890ff',
      borderRadius: 6,
      fontFamily: 'Inter, sans-serif',
    },
    components: {
      Layout: {
        headerBg: currentTheme === 'dark' ? '#141414' : '#001529',
        headerPadding: '0 24px',
        bodyBg: currentTheme === 'dark' ? '#1e293b' : '#f0f2f5',
        siderBg: currentTheme === 'dark' ? '#141414' : '#001529',
      },
      Menu: {
        darkItemBg: currentTheme === 'dark' ? '#141414' : '#001529',
        darkItemSelectedBg: '#1890ff',
      },
      Button: {
        borderRadius: 6,
      },
      Card: {
        borderRadius: 8,
      },
      Table: {
        borderRadius: 8,
      },
    },
  };

  return (
    <ThemeContext.Provider value={{ theme: currentTheme, toggleTheme }}>
      <AntdRegistry>
        <ConfigProvider theme={antdTheme}>
          <App>
            <div className={currentTheme === 'dark' ? 'dark' : ''}>
              {children}
            </div>
          </App>
        </ConfigProvider>
      </AntdRegistry>
    </ThemeContext.Provider>
  );
}; 
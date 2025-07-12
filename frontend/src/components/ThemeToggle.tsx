'use client';

import React, { useState, useEffect } from 'react';
import { Button, Tooltip } from 'antd';
import { SunOutlined, MoonOutlined } from '@ant-design/icons';

type Theme = 'light' | 'dark';

interface ThemeToggleProps {
  /** Size of the toggle button */
  size?: 'small' | 'middle' | 'large';
  /** Custom CSS class */
  className?: string;
  /** Whether to show tooltip */
  showTooltip?: boolean;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  size = 'middle',
  className = '',
  showTooltip = true
}) => {
  const [theme, setTheme] = useState<Theme>('light');
  const [mounted, setMounted] = useState(false);

  // Only run on client side to avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
    
    // Get initial theme from localStorage or system preference
    const savedTheme = localStorage.getItem('theme') as Theme;
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    const initialTheme = savedTheme || systemTheme;
    
    setTheme(initialTheme);
    applyTheme(initialTheme);
  }, []);

  const applyTheme = (newTheme: Theme) => {
    const root = document.documentElement;
    
    if (newTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    
    // Save to localStorage
    localStorage.setItem('theme', newTheme);
  };

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    applyTheme(newTheme);
  };

  // Don't render until mounted to avoid hydration issues
  if (!mounted) {
    return (
      <Button 
        type="text" 
        size={size}
        className={`text-white opacity-50 ${className}`}
        disabled
      >
        <SunOutlined />
      </Button>
    );
  }

  const button = (
    <Button
      type="text"
      size={size}
      onClick={toggleTheme}
      className={`text-white hover:bg-slate-700 transition-all duration-300 ${className}`}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      role="switch"
      aria-checked={theme === 'dark'}
    >
      {theme === 'light' ? (
        <MoonOutlined className="transition-transform duration-300 hover:rotate-12" />
      ) : (
        <SunOutlined className="transition-transform duration-300 hover:rotate-12" />
      )}
    </Button>
  );

  if (!showTooltip) {
    return button;
  }

  return (
    <Tooltip 
      title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      placement="bottom"
    >
      {button}
    </Tooltip>
  );
};

// Hook for accessing theme in components
export const useTheme = () => {
  const [theme, setTheme] = useState<Theme>('light');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    
    const savedTheme = localStorage.getItem('theme') as Theme;
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    const currentTheme = savedTheme || systemTheme;
    
    setTheme(currentTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    
    const root = document.documentElement;
    if (newTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    
    localStorage.setItem('theme', newTheme);
  };

  return {
    theme: mounted ? theme : 'light',
    isDark: mounted ? theme === 'dark' : false,
    toggleTheme,
    mounted
  };
};

export default ThemeToggle;
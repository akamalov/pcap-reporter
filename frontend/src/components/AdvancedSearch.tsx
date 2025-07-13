/**
 * Advanced Search Component
 * 
 * Provides sophisticated search and filtering capabilities for network analysis data.
 * Supports multiple search criteria, operators, and predefined filter rules.
 */

'use client';

import React, { useState, useEffect } from 'react';
import {
  Button,
  Input,
  Select,
  Card,
  Badge,
  Tabs,
  Collapse,
  Switch,
  Space,
  Row,
  Col,
  Typography,
  Alert,
  Divider,
  Tooltip,
  Statistic,
  message,
  Form
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  PlusOutlined,
  MinusOutlined,
  ReloadOutlined,
  DownloadOutlined,
  ClockCircleOutlined,
  SecurityScanOutlined,
  GlobalOutlined,
  ExclamationTriangleOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

interface SearchCriteria {
  field: string;
  operator: string;
  value: any;
  caseSensitive: boolean;
}

interface SearchQuery {
  criteria: SearchCriteria[];
  logicalOperator: string;
  limit?: number;
  offset?: number;
  sortBy?: string;
  sortOrder: string;
  groupBy?: string;
}

interface FilterRule {
  name: string;
  description: string;
  enabled: boolean;
  type: string;
}

interface SearchResults {
  matches: any[];
  totalCount: number;
  filteredCount: number;
  queryTimeMs: number;
  aggregations?: any;
}

interface AdvancedSearchProps {
  jobId: string;
  onResults?: (results: SearchResults) => void;
}

const AdvancedSearch: React.FC<AdvancedSearchProps> = ({ jobId, onResults }) => {
  const [searchQuery, setSearchQuery] = useState<SearchQuery>({
    criteria: [{ field: 'src_ip', operator: 'eq', value: '', caseSensitive: false }],
    logicalOperator: 'AND',
    sortOrder: 'desc'
  });
  
  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterRules, setFilterRules] = useState<FilterRule[]>([]);
  const [availableFields, setAvailableFields] = useState<any>({});
  const [statistics, setStatistics] = useState<any>({});
  const [activeKey, setActiveKey] = useState<string[]>(['1']);

  // Available search operators
  const operators = [
    { value: 'eq', label: 'Equals', types: ['string', 'integer', 'float'] },
    { value: 'ne', label: 'Not Equals', types: ['string', 'integer', 'float'] },
    { value: 'contains', label: 'Contains', types: ['string'] },
    { value: 'not_contains', label: 'Does Not Contain', types: ['string'] },
    { value: 'gt', label: 'Greater Than', types: ['integer', 'float', 'datetime'] },
    { value: 'lt', label: 'Less Than', types: ['integer', 'float', 'datetime'] },
    { value: 'gte', label: 'Greater Than or Equal', types: ['integer', 'float', 'datetime'] },
    { value: 'lte', label: 'Less Than or Equal', types: ['integer', 'float', 'datetime'] },
    { value: 'in', label: 'In List', types: ['string', 'integer'] },
    { value: 'not_in', label: 'Not In List', types: ['string', 'integer'] },
    { value: 'regex', label: 'Regular Expression', types: ['string'] },
    { value: 'between', label: 'Between', types: ['integer', 'float', 'datetime'] }
  ];

  // Load initial data
  useEffect(() => {
    loadFilterRules();
    loadAvailableFields();
    loadStatistics();
  }, [jobId]);

  const loadFilterRules = async () => {
    try {
      const response = await fetch('/api/v1/search/rules');
      const data = await response.json();
      if (data.status === 'success') {
        setFilterRules(data.rules);
      }
    } catch (err) {
      console.error('Error loading filter rules:', err);
    }
  };

  const loadAvailableFields = async () => {
    try {
      const response = await fetch('/api/v1/search/fields');
      const data = await response.json();
      if (data.status === 'success') {
        setAvailableFields(data.fields);
      }
    } catch (err) {
      console.error('Error loading available fields:', err);
    }
  };

  const loadStatistics = async () => {
    try {
      const response = await fetch(`/api/v1/search/statistics/${jobId}`);
      const data = await response.json();
      if (data.status === 'success') {
        setStatistics(data.statistics);
      }
    } catch (err) {
      console.error('Error loading statistics:', err);
    }
  };

  const executeSearch = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/v1/search/query/${jobId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(searchQuery),
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        setResults(data.results);
        onResults?.(data.results);
        message.success('Search completed successfully');
      } else {
        setError(data.detail || 'Search failed');
        message.error(data.detail || 'Search failed');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Search failed';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const applyFilterRule = async (ruleName: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/v1/search/filter/${jobId}/${ruleName}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setResults(data.results);
        onResults?.(data.results);
        message.success(`Filter "${ruleName}" applied successfully`);
      } else {
        setError(data.detail || 'Filter failed');
        message.error(data.detail || 'Filter failed');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Filter failed';
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const addCriteria = () => {
    setSearchQuery(prev => ({
      ...prev,
      criteria: [...prev.criteria, { field: 'src_ip', operator: 'eq', value: '', caseSensitive: false }]
    }));
  };

  const removeCriteria = (index: number) => {
    setSearchQuery(prev => ({
      ...prev,
      criteria: prev.criteria.filter((_, i) => i !== index)
    }));
  };

  const updateCriteria = (index: number, field: keyof SearchCriteria, value: any) => {
    setSearchQuery(prev => ({
      ...prev,
      criteria: prev.criteria.map((criteria, i) => 
        i === index ? { ...criteria, [field]: value } : criteria
      )
    }));
  };

  const resetSearch = () => {
    setSearchQuery({
      criteria: [{ field: 'src_ip', operator: 'eq', value: '', caseSensitive: false }],
      logicalOperator: 'AND',
      sortOrder: 'desc'
    });
    setResults(null);
    setError(null);
  };

  const getAllFields = () => {
    if (!availableFields) return [];
    
    return Object.values(availableFields).flat().map((field: any) => ({
      value: field.name,
      label: field.description,
      type: field.type
    }));
  };

  const getOperatorsForField = (fieldName: string) => {
    const field = getAllFields().find(f => f.value === fieldName);
    if (!field) return operators;
    
    return operators.filter(op => op.types.includes(field.type));
  };

  return (
    <div style={{ padding: '16px 0' }}>
      <Collapse 
        activeKey={activeKey} 
        onChange={setActiveKey}
        ghost
      >
        <Panel 
          header={
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <SearchOutlined />
              <Title level={4} style={{ margin: 0 }}>Advanced Search & Filtering</Title>
              <Text type="secondary" style={{ marginLeft: '16px' }}>
                Search and filter network analysis data with sophisticated criteria
              </Text>
            </div>
          } 
          key="1"
        >
          <Card>
            <Tabs defaultActiveKey="search" type="card">
              <Tabs.TabPane tab="Custom Search" key="search">
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  <Row align="middle" gutter={16}>
                    <Col span={4}>
                      <Text strong>Logical Operator:</Text>
                    </Col>
                    <Col span={6}>
                      <Select
                        value={searchQuery.logicalOperator}
                        onChange={(value) => setSearchQuery(prev => ({ ...prev, logicalOperator: value }))}
                        style={{ width: '100%' }}
                      >
                        <Option value="AND">AND</Option>
                        <Option value="OR">OR</Option>
                      </Select>
                    </Col>
                  </Row>

                  {searchQuery.criteria.map((criteria, index) => (
                    <Card key={index} size="small" style={{ backgroundColor: '#fafafa' }}>
                      <Row gutter={[16, 16]} align="middle">
                        <Col span={6}>
                          <Text strong>Field</Text>
                          <Select
                            value={criteria.field}
                            onChange={(value) => updateCriteria(index, 'field', value)}
                            style={{ width: '100%', marginTop: '4px' }}
                          >
                            {getAllFields().map((field) => (
                              <Option key={field.value} value={field.value}>
                                {field.label}
                              </Option>
                            ))}
                          </Select>
                        </Col>

                        <Col span={4}>
                          <Text strong>Operator</Text>
                          <Select
                            value={criteria.operator}
                            onChange={(value) => updateCriteria(index, 'operator', value)}
                            style={{ width: '100%', marginTop: '4px' }}
                          >
                            {getOperatorsForField(criteria.field).map((op) => (
                              <Option key={op.value} value={op.value}>
                                {op.label}
                              </Option>
                            ))}
                          </Select>
                        </Col>

                        <Col span={8}>
                          <Text strong>Value</Text>
                          <Input
                            value={criteria.value}
                            onChange={(e) => updateCriteria(index, 'value', e.target.value)}
                            placeholder="Enter search value..."
                            style={{ marginTop: '4px' }}
                          />
                        </Col>

                        <Col span={4}>
                          <Text strong>Case Sensitive</Text>
                          <div style={{ marginTop: '8px' }}>
                            <Switch
                              checked={criteria.caseSensitive}
                              onChange={(checked) => updateCriteria(index, 'caseSensitive', checked)}
                            />
                          </div>
                        </Col>

                        <Col span={2}>
                          <Button
                            type="primary"
                            danger
                            size="small"
                            icon={<MinusOutlined />}
                            onClick={() => removeCriteria(index)}
                            disabled={searchQuery.criteria.length === 1}
                            style={{ marginTop: '20px' }}
                          />
                        </Col>
                      </Row>
                    </Card>
                  ))}

                  <Space>
                    <Button icon={<PlusOutlined />} onClick={addCriteria}>
                      Add Criteria
                    </Button>
                    <Button 
                      type="primary" 
                      icon={<SearchOutlined />} 
                      onClick={executeSearch} 
                      loading={loading}
                    >
                      Search
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={resetSearch}>
                      Reset
                    </Button>
                  </Space>
                </Space>
              </Tabs.TabPane>

              <Tabs.TabPane tab="Filter Rules" key="rules">
                <Row gutter={[16, 16]}>
                  {filterRules.map((rule) => (
                    <Col span={8} key={rule.name}>
                      <Card
                        size="small"
                        hoverable
                        title={
                          <Space>
                            <Text strong>{rule.name}</Text>
                            <Badge 
                              status={rule.type === 'predefined' ? 'success' : 'default'} 
                              text={rule.type}
                            />
                          </Space>
                        }
                        actions={[
                          <Button
                            key="apply"
                            type="primary"
                            size="small"
                            icon={<FilterOutlined />}
                            onClick={() => applyFilterRule(rule.name)}
                            disabled={!rule.enabled || loading}
                          >
                            Apply Filter
                          </Button>
                        ]}
                      >
                        <Text type="secondary">{rule.description}</Text>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Tabs.TabPane>

              <Tabs.TabPane tab="Quick Filters" key="quick">
                <Row gutter={[16, 16]}>
                  <Col span={6}>
                    <Card size="small" title={<Space><SecurityScanOutlined style={{ color: '#f5222d' }} />Security Events</Space>}>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Button size="small" block icon={<ExclamationTriangleOutlined />}>
                          Critical Threats
                        </Button>
                        <Button size="small" block>
                          Suspicious IPs
                        </Button>
                        <Button size="small" block>
                          Failed Connections
                        </Button>
                      </Space>
                    </Card>
                  </Col>

                  <Col span={6}>
                    <Card size="small" title={<Space><GlobalOutlined style={{ color: '#1890ff' }} />Network Traffic</Space>}>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Button size="small" block>
                          High Volume
                        </Button>
                        <Button size="small" block>
                          External Connections
                        </Button>
                        <Button size="small" block>
                          Unusual Ports
                        </Button>
                      </Space>
                    </Card>
                  </Col>

                  <Col span={6}>
                    <Card size="small" title={<Space><ClockCircleOutlined style={{ color: '#52c41a' }} />Performance</Space>}>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Button size="small" block>
                          Slow Connections
                        </Button>
                        <Button size="small" block>
                          High Latency
                        </Button>
                        <Button size="small" block>
                          Timeouts
                        </Button>
                      </Space>
                    </Card>
                  </Col>

                  <Col span={6}>
                    <Card size="small" title={<Space><FilterOutlined style={{ color: '#722ed1' }} />Protocol Analysis</Space>}>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Button size="small" block>
                          HTTP Errors
                        </Button>
                        <Button size="small" block>
                          DNS Issues
                        </Button>
                        <Button size="small" block>
                          TCP Problems
                        </Button>
                      </Space>
                    </Card>
                  </Col>
                </Row>
              </Tabs.TabPane>

              <Tabs.TabPane tab="Statistics" key="stats">
                {statistics && (
                  <Row gutter={[16, 16]}>
                    <Col span={6}>
                      <Card size="small" title="Overview">
                        <Statistic title="Total Records" value={statistics.total_records} />
                        <Divider />
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Row justify="space-between">
                            <Text>Unique Source IPs:</Text>
                            <Text strong>{statistics.ips?.unique_src_count}</Text>
                          </Row>
                          <Row justify="space-between">
                            <Text>Unique Dest IPs:</Text>
                            <Text strong>{statistics.ips?.unique_dst_count}</Text>
                          </Row>
                        </Space>
                      </Card>
                    </Col>

                    <Col span={6}>
                      <Card size="small" title="Top Protocols">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          {Object.entries(statistics.protocols || {}).slice(0, 5).map(([protocol, count]) => (
                            <Row key={protocol} justify="space-between">
                              <Text>{protocol}:</Text>
                              <Text strong>{(count as number).toLocaleString()}</Text>
                            </Row>
                          ))}
                        </Space>
                      </Card>
                    </Col>

                    <Col span={6}>
                      <Card size="small" title="Security Stats">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          {Object.entries(statistics.security?.threat_levels || {}).map(([level, count]) => (
                            <Row key={level} justify="space-between">
                              <Text style={{ textTransform: 'capitalize' }}>{level}:</Text>
                              <Text strong>{(count as number).toLocaleString()}</Text>
                            </Row>
                          ))}
                        </Space>
                      </Card>
                    </Col>

                    <Col span={6}>
                      <Card size="small" title="Traffic Stats">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Row justify="space-between">
                            <Text>Max Packets:</Text>
                            <Text strong>{statistics.traffic?.max_packets?.toLocaleString()}</Text>
                          </Row>
                          <Row justify="space-between">
                            <Text>Max Bytes:</Text>
                            <Text strong>{(statistics.traffic?.max_bytes / 1024 / 1024)?.toFixed(1)}MB</Text>
                          </Row>
                          <Row justify="space-between">
                            <Text>Avg Duration:</Text>
                            <Text strong>{statistics.traffic?.avg_duration?.toFixed(2)}s</Text>
                          </Row>
                        </Space>
                      </Card>
                    </Col>
                  </Row>
                )}
              </Tabs.TabPane>
            </Tabs>
          </Card>
        </Panel>
      </Collapse>

      {error && (
        <Alert
          message="Search Error"
          description={error}
          type="error"
          showIcon
          style={{ marginTop: '16px' }}
        />
      )}

      {results && (
        <Card 
          title={
            <Row justify="space-between" align="middle">
              <Text strong>Search Results</Text>
              <Space>
                <Text type="secondary">
                  {results.filteredCount} of {results.totalCount} results ({results.queryTimeMs.toFixed(1)}ms)
                </Text>
                <Button icon={<DownloadOutlined />} size="small">
                  Export
                </Button>
              </Space>
            </Row>
          }
          style={{ marginTop: '16px' }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            {results.matches.slice(0, 10).map((match, index) => (
              <Card key={index} size="small" style={{ backgroundColor: '#fafafa' }}>
                <Row gutter={[16, 8]}>
                  <Col span={6}>
                    <Text type="secondary">Type</Text>
                    <div><Text code>{match.type}</Text></div>
                  </Col>
                  {match.src_ip && (
                    <Col span={6}>
                      <Text type="secondary">Source</Text>
                      <div><Text code>{match.src_ip}:{match.src_port}</Text></div>
                    </Col>
                  )}
                  {match.dst_ip && (
                    <Col span={6}>
                      <Text type="secondary">Destination</Text>
                      <div><Text code>{match.dst_ip}:{match.dst_port}</Text></div>
                    </Col>
                  )}
                  {match.protocol && (
                    <Col span={6}>
                      <Text type="secondary">Protocol</Text>
                      <div><Text code>{match.protocol}</Text></div>
                    </Col>
                  )}
                </Row>
                {match.description && (
                  <div style={{ marginTop: '8px' }}>
                    <Text type="secondary">{match.description}</Text>
                  </div>
                )}
              </Card>
            ))}
            {results.matches.length > 10 && (
              <div style={{ textAlign: 'center', padding: '16px' }}>
                <Button>
                  Load More Results ({results.matches.length - 10} remaining)
                </Button>
              </div>
            )}
          </Space>
        </Card>
      )}
    </div>
  );
};

export default AdvancedSearch;
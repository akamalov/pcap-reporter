/**
 * Advanced Search Component
 * 
 * Provides sophisticated search and filtering capabilities for network analysis data.
 * Supports multiple search criteria, operators, and predefined filter rules.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { 
  Search, 
  Filter, 
  Plus, 
  Minus, 
  RotateCcw, 
  Download,
  Clock,
  Shield,
  Network,
  ChevronDown,
  ChevronUp,
  AlertTriangle
} from 'lucide-react';

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
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isCollapsed, setIsCollapsed] = useState(false);

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
      } else {
        setError(data.detail || 'Search failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
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
      } else {
        setError(data.detail || 'Filter failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Filter failed');
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
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Search className="w-5 h-5" />
                Advanced Search & Filtering
              </CardTitle>
              <CardDescription>
                Search and filter network analysis data with sophisticated criteria
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsCollapsed(!isCollapsed)}
            >
              {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
            </Button>
          </div>
        </CardHeader>
        
        <Collapsible open={!isCollapsed}>
          <CollapsibleContent>
            <CardContent>
              <Tabs defaultValue="search" className="w-full">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="search">Custom Search</TabsTrigger>
                  <TabsTrigger value="rules">Filter Rules</TabsTrigger>
                  <TabsTrigger value="quick">Quick Filters</TabsTrigger>
                  <TabsTrigger value="stats">Statistics</TabsTrigger>
                </TabsList>

                <TabsContent value="search" className="space-y-4">
                  <div className="space-y-4">
                    <div className="flex items-center gap-4">
                      <Label htmlFor="logicalOp">Logical Operator:</Label>
                      <Select
                        value={searchQuery.logicalOperator}
                        onValueChange={(value) => setSearchQuery(prev => ({ ...prev, logicalOperator: value }))}
                      >
                        <SelectTrigger className="w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="AND">AND</SelectItem>
                          <SelectItem value="OR">OR</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {searchQuery.criteria.map((criteria, index) => (
                      <Card key={index} className="p-4">
                        <div className="grid grid-cols-12 gap-2 items-end">
                          <div className="col-span-3">
                            <Label>Field</Label>
                            <Select
                              value={criteria.field}
                              onValueChange={(value) => updateCriteria(index, 'field', value)}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {getAllFields().map((field) => (
                                  <SelectItem key={field.value} value={field.value}>
                                    {field.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="col-span-2">
                            <Label>Operator</Label>
                            <Select
                              value={criteria.operator}
                              onValueChange={(value) => updateCriteria(index, 'operator', value)}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {getOperatorsForField(criteria.field).map((op) => (
                                  <SelectItem key={op.value} value={op.value}>
                                    {op.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>

                          <div className="col-span-4">
                            <Label>Value</Label>
                            <Input
                              value={criteria.value}
                              onChange={(e) => updateCriteria(index, 'value', e.target.value)}
                              placeholder="Enter search value..."
                            />
                          </div>

                          <div className="col-span-2">
                            <div className="flex items-center space-x-2">
                              <Switch
                                checked={criteria.caseSensitive}
                                onCheckedChange={(checked) => updateCriteria(index, 'caseSensitive', checked)}
                              />
                              <Label className="text-sm">Case Sensitive</Label>
                            </div>
                          </div>

                          <div className="col-span-1">
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => removeCriteria(index)}
                              disabled={searchQuery.criteria.length === 1}
                            >
                              <Minus className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </Card>
                    ))}

                    <div className="flex gap-2">
                      <Button variant="outline" onClick={addCriteria}>
                        <Plus className="w-4 h-4 mr-2" />
                        Add Criteria
                      </Button>
                      <Button onClick={executeSearch} disabled={loading}>
                        <Search className="w-4 h-4 mr-2" />
                        {loading ? 'Searching...' : 'Search'}
                      </Button>
                      <Button variant="outline" onClick={resetSearch}>
                        <RotateCcw className="w-4 h-4 mr-2" />
                        Reset
                      </Button>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="rules" className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filterRules.map((rule) => (
                      <Card key={rule.name} className="cursor-pointer hover:shadow-md transition-shadow">
                        <CardHeader className="pb-3">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-sm">{rule.name}</CardTitle>
                            <Badge variant={rule.type === 'predefined' ? 'default' : 'secondary'}>
                              {rule.type}
                            </Badge>
                          </div>
                          <CardDescription className="text-xs">
                            {rule.description}
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="pt-0">
                          <Button
                            size="sm"
                            className="w-full"
                            onClick={() => applyFilterRule(rule.name)}
                            disabled={!rule.enabled || loading}
                          >
                            <Filter className="w-4 h-4 mr-2" />
                            Apply Filter
                          </Button>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </TabsContent>

                <TabsContent value="quick" className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <Card className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Shield className="w-5 h-5 text-red-500" />
                        <h3 className="font-semibold">Security Events</h3>
                      </div>
                      <div className="space-y-2">
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          <AlertTriangle className="w-4 h-4 mr-2" />
                          Critical Threats
                        </Button>
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          Suspicious IPs
                        </Button>
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          Failed Connections
                        </Button>
                      </div>
                    </Card>

                    <Card className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Network className="w-5 h-5 text-blue-500" />
                        <h3 className="font-semibold">Network Traffic</h3>
                      </div>
                      <div className="space-y-2">
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          High Volume
                        </Button>
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          External Connections
                        </Button>
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          Unusual Ports
                        </Button>
                      </div>
                    </Card>

                    <Card className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Clock className="w-5 h-5 text-green-500" />
                        <h3 className="font-semibold">Performance</h3>
                      </div>
                      <div className="space-y-2">
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          Slow Connections
                        </Button>
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          High Latency
                        </Button>
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          Timeouts
                        </Button>
                      </div>
                    </Card>

                    <Card className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Filter className="w-5 h-5 text-purple-500" />
                        <h3 className="font-semibold">Protocol Analysis</h3>
                      </div>
                      <div className="space-y-2">
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          HTTP Errors
                        </Button>
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          DNS Issues
                        </Button>
                        <Button size="sm" variant="outline" className="w-full justify-start">
                          TCP Problems
                        </Button>
                      </div>
                    </Card>
                  </div>
                </TabsContent>

                <TabsContent value="stats" className="space-y-4">
                  {statistics && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      <Card className="p-4">
                        <h3 className="font-semibold mb-2">Overview</h3>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span>Total Records:</span>
                            <span className="font-mono">{statistics.total_records?.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Unique Source IPs:</span>
                            <span className="font-mono">{statistics.ips?.unique_src_count}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Unique Dest IPs:</span>
                            <span className="font-mono">{statistics.ips?.unique_dst_count}</span>
                          </div>
                        </div>
                      </Card>

                      <Card className="p-4">
                        <h3 className="font-semibold mb-2">Top Protocols</h3>
                        <div className="space-y-1 text-sm">
                          {Object.entries(statistics.protocols || {}).slice(0, 5).map(([protocol, count]) => (
                            <div key={protocol} className="flex justify-between">
                              <span>{protocol}:</span>
                              <span className="font-mono">{(count as number).toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      </Card>

                      <Card className="p-4">
                        <h3 className="font-semibold mb-2">Security Stats</h3>
                        <div className="space-y-1 text-sm">
                          {Object.entries(statistics.security?.threat_levels || {}).map(([level, count]) => (
                            <div key={level} className="flex justify-between">
                              <span className="capitalize">{level}:</span>
                              <span className="font-mono">{(count as number).toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      </Card>

                      <Card className="p-4">
                        <h3 className="font-semibold mb-2">Traffic Stats</h3>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span>Max Packets:</span>
                            <span className="font-mono">{statistics.traffic?.max_packets?.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Max Bytes:</span>
                            <span className="font-mono">{(statistics.traffic?.max_bytes / 1024 / 1024)?.toFixed(1)}MB</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Avg Duration:</span>
                            <span className="font-mono">{statistics.traffic?.avg_duration?.toFixed(2)}s</span>
                          </div>
                        </div>
                      </Card>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {results && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Search Results</span>
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span>{results.filteredCount} of {results.totalCount} results</span>
                <span>({results.queryTimeMs.toFixed(1)}ms)</span>
                <Button size="sm" variant="outline">
                  <Download className="w-4 h-4 mr-2" />
                  Export
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {results.matches.slice(0, 10).map((match, index) => (
                <Card key={index} className="p-3">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <Label className="text-xs text-gray-500">Type</Label>
                      <p className="font-mono">{match.type}</p>
                    </div>
                    {match.src_ip && (
                      <div>
                        <Label className="text-xs text-gray-500">Source</Label>
                        <p className="font-mono">{match.src_ip}:{match.src_port}</p>
                      </div>
                    )}
                    {match.dst_ip && (
                      <div>
                        <Label className="text-xs text-gray-500">Destination</Label>
                        <p className="font-mono">{match.dst_ip}:{match.dst_port}</p>
                      </div>
                    )}
                    {match.protocol && (
                      <div>
                        <Label className="text-xs text-gray-500">Protocol</Label>
                        <p className="font-mono">{match.protocol}</p>
                      </div>
                    )}
                  </div>
                  {match.description && (
                    <p className="text-sm text-gray-600 mt-2">{match.description}</p>
                  )}
                </Card>
              ))}
              {results.matches.length > 10 && (
                <div className="text-center py-4">
                  <Button variant="outline">
                    Load More Results ({results.matches.length - 10} remaining)
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AdvancedSearch;
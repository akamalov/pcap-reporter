"""
Advanced Search and Filtering Service.

Provides sophisticated search and filtering capabilities for network analysis data,
including protocol-based searches, IP range filters, temporal queries, and advanced
pattern matching for security analysis.
"""

import asyncio
import logging
import re
import ipaddress
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from models.analysis_results import AnalysisResults, NetworkIssue, SeverityLevel

logger = logging.getLogger(__name__)


class SearchOperator(Enum):
    """Search operators for advanced queries."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    REGEX = "regex"
    BETWEEN = "between"


class SearchField(Enum):
    """Searchable fields in network data."""
    # IP addresses
    SOURCE_IP = "src_ip"
    DESTINATION_IP = "dst_ip"
    ANY_IP = "any_ip"
    
    # Ports
    SOURCE_PORT = "src_port"
    DESTINATION_PORT = "dst_port"
    ANY_PORT = "any_port"
    
    # Protocols
    PROTOCOL = "protocol"
    PROTOCOL_LAYER = "protocol_layer"
    
    # Traffic metrics
    PACKET_COUNT = "packet_count"
    BYTE_COUNT = "byte_count"
    DURATION = "duration"
    PACKETS_PER_SECOND = "pps"
    BYTES_PER_SECOND = "bps"
    
    # Timestamps
    START_TIME = "start_time"
    END_TIME = "end_time"
    TIMESTAMP = "timestamp"
    
    # Security
    THREAT_LEVEL = "threat_level"
    SECURITY_CATEGORY = "security_category"
    ANOMALY_SCORE = "anomaly_score"
    
    # Application layer
    HTTP_METHOD = "http_method"
    HTTP_STATUS = "http_status"
    DNS_QUERY = "dns_query"
    DNS_RESPONSE = "dns_response"
    
    # TCP specifics
    TCP_FLAGS = "tcp_flags"
    TCP_STATE = "tcp_state"
    
    # Custom fields
    CUSTOM = "custom"


@dataclass
class SearchCriteria:
    """Represents a single search criterion."""
    field: SearchField
    operator: SearchOperator
    value: Any
    case_sensitive: bool = False


@dataclass
class SearchQuery:
    """Represents a complex search query."""
    criteria: List[SearchCriteria] = field(default_factory=list)
    logical_operator: str = "AND"  # AND, OR
    limit: Optional[int] = None
    offset: Optional[int] = 0
    sort_by: Optional[str] = None
    sort_order: str = "desc"  # asc, desc
    group_by: Optional[str] = None


@dataclass
class FilterRule:
    """Represents a filtering rule."""
    name: str
    description: str
    query: SearchQuery
    enabled: bool = True
    priority: int = 0


@dataclass
class SearchResult:
    """Represents search results."""
    matches: List[Dict[str, Any]]
    total_count: int
    filtered_count: int
    query_time_ms: float
    aggregations: Optional[Dict[str, Any]] = None


class AdvancedSearchService:
    """Service for advanced search and filtering of network data."""
    
    def __init__(self):
        """Initialize the search service."""
        self.logger = logging.getLogger(__name__)
        
        # Predefined filter rules
        self.predefined_rules = self._create_predefined_rules()
        
        # Custom filter rules
        self.custom_rules: List[FilterRule] = []
        
        # Search index for performance optimization
        self.search_index = {}
        
        self.logger.info("Advanced search service initialized")
    
    def _create_predefined_rules(self) -> List[FilterRule]:
        """Create predefined filtering rules for common scenarios."""
        rules = []
        
        # Security-focused rules
        rules.append(FilterRule(
            name="suspicious_ports",
            description="Filter connections to suspicious ports",
            query=SearchQuery(criteria=[
                SearchCriteria(
                    field=SearchField.DESTINATION_PORT,
                    operator=SearchOperator.IN,
                    value=[23, 135, 139, 445, 1433, 3389, 5900, 6667]
                )
            ])
        ))
        
        rules.append(FilterRule(
            name="high_volume_connections",
            description="Filter high-volume network connections",
            query=SearchQuery(criteria=[
                SearchCriteria(
                    field=SearchField.PACKET_COUNT,
                    operator=SearchOperator.GREATER_THAN,
                    value=10000
                )
            ])
        ))
        
        rules.append(FilterRule(
            name="external_connections",
            description="Filter connections to external IP addresses",
            query=SearchQuery(criteria=[
                SearchCriteria(
                    field=SearchField.DESTINATION_IP,
                    operator=SearchOperator.REGEX,
                    value=r"^(?!10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)"
                )
            ])
        ))
        
        rules.append(FilterRule(
            name="dns_tunneling",
            description="Detect potential DNS tunneling",
            query=SearchQuery(criteria=[
                SearchCriteria(
                    field=SearchField.PROTOCOL,
                    operator=SearchOperator.EQUALS,
                    value="DNS"
                ),
                SearchCriteria(
                    field=SearchField.PACKET_COUNT,
                    operator=SearchOperator.GREATER_THAN,
                    value=100
                )
            ])
        ))
        
        # Performance-focused rules
        rules.append(FilterRule(
            name="slow_connections",
            description="Filter slow network connections",
            query=SearchQuery(criteria=[
                SearchCriteria(
                    field=SearchField.DURATION,
                    operator=SearchOperator.GREATER_THAN,
                    value=30.0
                ),
                SearchCriteria(
                    field=SearchField.PACKETS_PER_SECOND,
                    operator=SearchOperator.LESS_THAN,
                    value=10
                )
            ])
        ))
        
        rules.append(FilterRule(
            name="failed_connections",
            description="Filter failed TCP connections",
            query=SearchQuery(criteria=[
                SearchCriteria(
                    field=SearchField.TCP_FLAGS,
                    operator=SearchOperator.CONTAINS,
                    value="RST"
                )
            ])
        ))
        
        # Protocol-specific rules
        rules.append(FilterRule(
            name="http_errors",
            description="Filter HTTP error responses",
            query=SearchQuery(criteria=[
                SearchCriteria(
                    field=SearchField.HTTP_STATUS,
                    operator=SearchOperator.GREATER_EQUAL,
                    value=400
                )
            ])
        ))
        
        rules.append(FilterRule(
            name="large_downloads",
            description="Filter large file downloads",
            query=SearchQuery(criteria=[
                SearchCriteria(
                    field=SearchField.BYTE_COUNT,
                    operator=SearchOperator.GREATER_THAN,
                    value=100000000  # 100MB
                )
            ])
        ))
        
        return rules
    
    async def search(self, analysis_data: Dict[str, Any], query: SearchQuery) -> SearchResult:
        """
        Execute a search query against network analysis data.
        
        Args:
            analysis_data: Network analysis data to search
            query: Search query to execute
            
        Returns:
            SearchResult containing matches and metadata
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Extract searchable data
            searchable_data = await self._extract_searchable_data(analysis_data)
            
            # Apply search criteria
            matches = await self._apply_search_criteria(searchable_data, query.criteria, query.logical_operator)
            
            # Apply sorting
            if query.sort_by:
                matches = await self._sort_results(matches, query.sort_by, query.sort_order)
            
            # Apply pagination
            total_count = len(matches)
            if query.offset:
                matches = matches[query.offset:]
            if query.limit:
                matches = matches[:query.limit]
            
            # Apply grouping if specified
            aggregations = None
            if query.group_by:
                aggregations = await self._group_results(matches, query.group_by)
            
            query_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return SearchResult(
                matches=matches,
                total_count=total_count,
                filtered_count=len(matches),
                query_time_ms=query_time,
                aggregations=aggregations
            )
            
        except Exception as e:
            self.logger.error(f"Error executing search query: {e}")
            raise
    
    async def apply_filter_rule(self, analysis_data: Dict[str, Any], rule_name: str) -> SearchResult:
        """
        Apply a predefined filter rule to analysis data.
        
        Args:
            analysis_data: Network analysis data to filter
            rule_name: Name of the filter rule to apply
            
        Returns:
            SearchResult containing filtered data
        """
        try:
            # Find the filter rule
            rule = self._find_filter_rule(rule_name)
            if not rule:
                raise ValueError(f"Filter rule '{rule_name}' not found")
            
            if not rule.enabled:
                raise ValueError(f"Filter rule '{rule_name}' is disabled")
            
            # Execute the rule's query
            return await self.search(analysis_data, rule.query)
            
        except Exception as e:
            self.logger.error(f"Error applying filter rule '{rule_name}': {e}")
            raise
    
    async def create_custom_rule(self, rule: FilterRule) -> bool:
        """
        Create a custom filter rule.
        
        Args:
            rule: Filter rule to create
            
        Returns:
            True if successful
        """
        try:
            # Validate rule
            if not rule.name or not rule.query.criteria:
                raise ValueError("Rule must have a name and at least one criterion")
            
            # Check for duplicate names
            if self._find_filter_rule(rule.name):
                raise ValueError(f"Filter rule '{rule.name}' already exists")
            
            # Add to custom rules
            self.custom_rules.append(rule)
            
            self.logger.info(f"Created custom filter rule: {rule.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating custom rule: {e}")
            raise
    
    async def search_by_ip_range(self, analysis_data: Dict[str, Any], 
                                ip_range: str, field: str = "any") -> SearchResult:
        """
        Search for connections within a specific IP range.
        
        Args:
            analysis_data: Network analysis data to search
            ip_range: IP range in CIDR notation (e.g., "192.168.1.0/24")
            field: Which IP field to search ("src", "dst", "any")
            
        Returns:
            SearchResult containing matches
        """
        try:
            network = ipaddress.ip_network(ip_range, strict=False)
            
            criteria = []
            if field in ["src", "any"]:
                criteria.append(SearchCriteria(
                    field=SearchField.SOURCE_IP,
                    operator=SearchOperator.REGEX,
                    value=self._ip_network_to_regex(network)
                ))
            
            if field in ["dst", "any"]:
                criteria.append(SearchCriteria(
                    field=SearchField.DESTINATION_IP,
                    operator=SearchOperator.REGEX,
                    value=self._ip_network_to_regex(network)
                ))
            
            logical_op = "OR" if field == "any" and len(criteria) > 1 else "AND"
            
            query = SearchQuery(
                criteria=criteria,
                logical_operator=logical_op
            )
            
            return await self.search(analysis_data, query)
            
        except Exception as e:
            self.logger.error(f"Error searching IP range {ip_range}: {e}")
            raise
    
    async def search_by_time_window(self, analysis_data: Dict[str, Any],
                                  start_time: datetime, end_time: datetime) -> SearchResult:
        """
        Search for connections within a specific time window.
        
        Args:
            analysis_data: Network analysis data to search
            start_time: Start of time window
            end_time: End of time window
            
        Returns:
            SearchResult containing matches
        """
        try:
            query = SearchQuery(criteria=[
                SearchCriteria(
                    field=SearchField.TIMESTAMP,
                    operator=SearchOperator.BETWEEN,
                    value=[start_time, end_time]
                )
            ])
            
            return await self.search(analysis_data, query)
            
        except Exception as e:
            self.logger.error(f"Error searching time window: {e}")
            raise
    
    async def search_security_events(self, analysis_data: Dict[str, Any],
                                   severity: Optional[str] = None) -> SearchResult:
        """
        Search for security-related events and anomalies.
        
        Args:
            analysis_data: Network analysis data to search
            severity: Optional severity filter (critical, high, medium, low)
            
        Returns:
            SearchResult containing security events
        """
        try:
            criteria = []
            
            # Search for security-related patterns
            criteria.append(SearchCriteria(
                field=SearchField.SECURITY_CATEGORY,
                operator=SearchOperator.NOT_EQUALS,
                value="normal"
            ))
            
            if severity:
                criteria.append(SearchCriteria(
                    field=SearchField.THREAT_LEVEL,
                    operator=SearchOperator.EQUALS,
                    value=severity.lower()
                ))
            
            query = SearchQuery(
                criteria=criteria,
                sort_by="anomaly_score",
                sort_order="desc"
            )
            
            return await self.search(analysis_data, query)
            
        except Exception as e:
            self.logger.error(f"Error searching security events: {e}")
            raise
    
    async def get_search_suggestions(self, analysis_data: Dict[str, Any],
                                   field: SearchField, partial_value: str) -> List[str]:
        """
        Get search suggestions for a field based on partial input.
        
        Args:
            analysis_data: Network analysis data to search
            field: Field to get suggestions for
            partial_value: Partial value for autocomplete
            
        Returns:
            List of suggested values
        """
        try:
            searchable_data = await self._extract_searchable_data(analysis_data)
            
            suggestions = set()
            field_name = field.value
            
            for item in searchable_data:
                if field_name in item:
                    value = str(item[field_name])
                    if partial_value.lower() in value.lower():
                        suggestions.add(value)
            
            return sorted(list(suggestions))[:20]  # Limit to 20 suggestions
            
        except Exception as e:
            self.logger.error(f"Error getting search suggestions: {e}")
            return []
    
    async def get_filter_statistics(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about filterable data for UI controls.
        
        Args:
            analysis_data: Network analysis data to analyze
            
        Returns:
            Dict containing statistics for various fields
        """
        try:
            searchable_data = await self._extract_searchable_data(analysis_data)
            
            stats = {
                "total_records": len(searchable_data),
                "protocols": {},
                "ports": {"top_src": {}, "top_dst": {}},
                "ips": {"unique_src": set(), "unique_dst": set()},
                "time_range": {"start": None, "end": None},
                "security": {"threat_levels": {}, "categories": {}},
                "traffic": {
                    "max_packets": 0,
                    "max_bytes": 0,
                    "avg_duration": 0
                }
            }
            
            # Collect statistics
            durations = []
            for item in searchable_data:
                # Protocol stats
                protocol = item.get("protocol", "unknown")
                stats["protocols"][protocol] = stats["protocols"].get(protocol, 0) + 1
                
                # Port stats
                src_port = item.get("src_port")
                dst_port = item.get("dst_port")
                if src_port:
                    stats["ports"]["top_src"][src_port] = stats["ports"]["top_src"].get(src_port, 0) + 1
                if dst_port:
                    stats["ports"]["top_dst"][dst_port] = stats["ports"]["top_dst"].get(dst_port, 0) + 1
                
                # IP stats
                src_ip = item.get("src_ip")
                dst_ip = item.get("dst_ip")
                if src_ip:
                    stats["ips"]["unique_src"].add(src_ip)
                if dst_ip:
                    stats["ips"]["unique_dst"].add(dst_ip)
                
                # Traffic stats
                packet_count = item.get("packet_count", 0)
                byte_count = item.get("byte_count", 0)
                duration = item.get("duration", 0)
                
                stats["traffic"]["max_packets"] = max(stats["traffic"]["max_packets"], packet_count)
                stats["traffic"]["max_bytes"] = max(stats["traffic"]["max_bytes"], byte_count)
                if duration > 0:
                    durations.append(duration)
                
                # Security stats
                threat_level = item.get("threat_level", "normal")
                security_cat = item.get("security_category", "normal")
                
                stats["security"]["threat_levels"][threat_level] = stats["security"]["threat_levels"].get(threat_level, 0) + 1
                stats["security"]["categories"][security_cat] = stats["security"]["categories"].get(security_cat, 0) + 1
            
            # Calculate averages
            if durations:
                stats["traffic"]["avg_duration"] = sum(durations) / len(durations)
            
            # Convert sets to counts
            stats["ips"]["unique_src_count"] = len(stats["ips"]["unique_src"])
            stats["ips"]["unique_dst_count"] = len(stats["ips"]["unique_dst"])
            del stats["ips"]["unique_src"]
            del stats["ips"]["unique_dst"]
            
            # Sort top items
            stats["protocols"] = dict(sorted(stats["protocols"].items(), key=lambda x: x[1], reverse=True)[:10])
            stats["ports"]["top_src"] = dict(sorted(stats["ports"]["top_src"].items(), key=lambda x: x[1], reverse=True)[:10])
            stats["ports"]["top_dst"] = dict(sorted(stats["ports"]["top_dst"].items(), key=lambda x: x[1], reverse=True)[:10])
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error generating filter statistics: {e}")
            return {}
    
    def get_available_rules(self) -> List[Dict[str, Any]]:
        """Get all available filter rules."""
        all_rules = self.predefined_rules + self.custom_rules
        
        return [{
            "name": rule.name,
            "description": rule.description,
            "enabled": rule.enabled,
            "priority": rule.priority,
            "type": "predefined" if rule in self.predefined_rules else "custom"
        } for rule in all_rules]
    
    async def _extract_searchable_data(self, analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract searchable data from analysis results."""
        searchable_data = []
        
        # Extract from conversations
        conversations = analysis_data.get("conversations", [])
        for conv in conversations:
            searchable_data.append({
                "type": "conversation",
                "src_ip": conv.get("src_ip"),
                "dst_ip": conv.get("dst_ip"),
                "src_port": conv.get("src_port"),
                "dst_port": conv.get("dst_port"),
                "protocol": conv.get("protocol"),
                "packet_count": conv.get("packet_count", 0),
                "byte_count": conv.get("byte_count", 0),
                "duration": conv.get("duration", 0),
                "pps": conv.get("packets_per_second", 0),
                "bps": conv.get("bytes_per_second", 0),
                "threat_level": conv.get("threat_level", "normal"),
                "security_category": conv.get("security_category", "normal"),
                "anomaly_score": conv.get("anomaly_score", 0)
            })
        
        # Extract from security alerts
        security_analysis = analysis_data.get("security_analysis", {})
        security_alerts = security_analysis.get("security_alerts", [])
        for alert in security_alerts:
            searchable_data.append({
                "type": "security_alert",
                "security_category": alert.get("type", "unknown"),
                "threat_level": alert.get("severity", "medium"),
                "description": alert.get("description", ""),
                "anomaly_score": 0.8 if alert.get("severity") == "high" else 0.5
            })
        
        # Extract from performance issues
        performance_analysis = analysis_data.get("performance_analysis", {})
        performance_issues = performance_analysis.get("performance_issues", [])
        for issue in performance_issues:
            searchable_data.append({
                "type": "performance_issue",
                "security_category": "performance",
                "threat_level": issue.get("severity", "medium"),
                "description": issue.get("description", ""),
                "anomaly_score": 0.3
            })
        
        return searchable_data
    
    async def _apply_search_criteria(self, data: List[Dict[str, Any]], 
                                   criteria: List[SearchCriteria],
                                   logical_operator: str) -> List[Dict[str, Any]]:
        """Apply search criteria to data."""
        if not criteria:
            return data
        
        results = []
        
        for item in data:
            if logical_operator.upper() == "AND":
                matches = all(await self._evaluate_criterion(item, criterion) for criterion in criteria)
            else:  # OR
                matches = any(await self._evaluate_criterion(item, criterion) for criterion in criteria)
            
            if matches:
                results.append(item)
        
        return results
    
    async def _evaluate_criterion(self, item: Dict[str, Any], criterion: SearchCriteria) -> bool:
        """Evaluate a single search criterion against an item."""
        field_value = item.get(criterion.field.value)
        
        if field_value is None:
            return False
        
        # Handle case sensitivity
        if isinstance(field_value, str) and not criterion.case_sensitive:
            field_value = field_value.lower()
            if isinstance(criterion.value, str):
                criterion.value = criterion.value.lower()
        
        # Apply operator
        if criterion.operator == SearchOperator.EQUALS:
            return field_value == criterion.value
        elif criterion.operator == SearchOperator.NOT_EQUALS:
            return field_value != criterion.value
        elif criterion.operator == SearchOperator.CONTAINS:
            return str(criterion.value) in str(field_value)
        elif criterion.operator == SearchOperator.NOT_CONTAINS:
            return str(criterion.value) not in str(field_value)
        elif criterion.operator == SearchOperator.GREATER_THAN:
            return float(field_value) > float(criterion.value)
        elif criterion.operator == SearchOperator.LESS_THAN:
            return float(field_value) < float(criterion.value)
        elif criterion.operator == SearchOperator.GREATER_EQUAL:
            return float(field_value) >= float(criterion.value)
        elif criterion.operator == SearchOperator.LESS_EQUAL:
            return float(field_value) <= float(criterion.value)
        elif criterion.operator == SearchOperator.IN:
            return field_value in criterion.value
        elif criterion.operator == SearchOperator.NOT_IN:
            return field_value not in criterion.value
        elif criterion.operator == SearchOperator.REGEX:
            return bool(re.search(criterion.value, str(field_value)))
        elif criterion.operator == SearchOperator.BETWEEN:
            if isinstance(criterion.value, list) and len(criterion.value) == 2:
                return criterion.value[0] <= field_value <= criterion.value[1]
        
        return False
    
    async def _sort_results(self, results: List[Dict[str, Any]], 
                          sort_by: str, sort_order: str) -> List[Dict[str, Any]]:
        """Sort search results."""
        reverse = sort_order.lower() == "desc"
        
        try:
            return sorted(results, key=lambda x: x.get(sort_by, 0), reverse=reverse)
        except Exception as e:
            self.logger.warning(f"Error sorting results by {sort_by}: {e}")
            return results
    
    async def _group_results(self, results: List[Dict[str, Any]], 
                           group_by: str) -> Dict[str, Any]:
        """Group search results by a field."""
        groups = {}
        
        for item in results:
            group_value = item.get(group_by, "unknown")
            if group_value not in groups:
                groups[group_value] = []
            groups[group_value].append(item)
        
        return {
            "groups": groups,
            "group_counts": {k: len(v) for k, v in groups.items()}
        }
    
    def _find_filter_rule(self, rule_name: str) -> Optional[FilterRule]:
        """Find a filter rule by name."""
        all_rules = self.predefined_rules + self.custom_rules
        return next((rule for rule in all_rules if rule.name == rule_name), None)
    
    def _ip_network_to_regex(self, network: ipaddress.IPv4Network) -> str:
        """Convert IP network to regex pattern."""
        # Simple implementation - could be optimized
        network_str = str(network.network_address)
        prefix_len = network.prefixlen
        
        if prefix_len == 32:
            return f"^{re.escape(network_str)}$"
        elif prefix_len >= 24:
            base = ".".join(network_str.split(".")[:-1])
            return f"^{re.escape(base)}\\."
        elif prefix_len >= 16:
            base = ".".join(network_str.split(".")[:-2])
            return f"^{re.escape(base)}\\."
        else:
            base = network_str.split(".")[0]
            return f"^{re.escape(base)}\\."


# Global instance
advanced_search_service = AdvancedSearchService()
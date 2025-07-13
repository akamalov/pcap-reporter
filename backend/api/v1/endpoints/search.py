"""
Advanced Search and Filtering API Endpoints.

Provides sophisticated search and filtering capabilities for network analysis data.
"""

import logging
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from core.database import get_database
from services.advanced_search_service import (
    advanced_search_service, SearchQuery, SearchCriteria, SearchField, 
    SearchOperator, FilterRule
)

logger = logging.getLogger(__name__)
router = APIRouter()


class SearchCriteriaModel(BaseModel):
    """Pydantic model for search criteria."""
    field: str
    operator: str
    value: Any
    case_sensitive: bool = False


class SearchQueryModel(BaseModel):
    """Pydantic model for search queries."""
    criteria: List[SearchCriteriaModel]
    logical_operator: str = "AND"
    limit: Optional[int] = None
    offset: Optional[int] = 0
    sort_by: Optional[str] = None
    sort_order: str = "desc"
    group_by: Optional[str] = None


class FilterRuleModel(BaseModel):
    """Pydantic model for filter rules."""
    name: str
    description: str
    query: SearchQueryModel
    enabled: bool = True
    priority: int = 0


@router.post("/query/{job_id}")
async def execute_search_query(
    job_id: str,
    query: SearchQueryModel
) -> Dict[str, Any]:
    """
    Execute a complex search query against analysis results.
    
    Args:
        job_id: The analysis job ID
        query: Search query to execute
        
    Returns:
        Search results with matches and metadata
    """
    try:
        logger.info(f"Executing search query for job {job_id}")
        
        # Get analysis data
        analysis_data = await _get_analysis_data(job_id)
        
        # Convert Pydantic models to internal models
        search_criteria = []
        for criteria in query.criteria:
            search_criteria.append(SearchCriteria(
                field=SearchField(criteria.field),
                operator=SearchOperator(criteria.operator),
                value=criteria.value,
                case_sensitive=criteria.case_sensitive
            ))
        
        search_query = SearchQuery(
            criteria=search_criteria,
            logical_operator=query.logical_operator,
            limit=query.limit,
            offset=query.offset,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            group_by=query.group_by
        )
        
        # Execute search
        results = await advanced_search_service.search(analysis_data, search_query)
        
        return {
            "status": "success",
            "job_id": job_id,
            "results": {
                "matches": results.matches,
                "total_count": results.total_count,
                "filtered_count": results.filtered_count,
                "query_time_ms": results.query_time_ms,
                "aggregations": results.aggregations
            }
        }
        
    except Exception as e:
        logger.error(f"Error executing search query for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search query failed: {str(e)}"
        )


@router.get("/filter/{job_id}/{rule_name}")
async def apply_filter_rule(
    job_id: str,
    rule_name: str
) -> Dict[str, Any]:
    """
    Apply a predefined filter rule to analysis results.
    
    Args:
        job_id: The analysis job ID
        rule_name: Name of the filter rule to apply
        
    Returns:
        Filtered results
    """
    try:
        logger.info(f"Applying filter rule '{rule_name}' to job {job_id}")
        
        # Get analysis data
        analysis_data = await _get_analysis_data(job_id)
        
        # Apply filter rule
        results = await advanced_search_service.apply_filter_rule(analysis_data, rule_name)
        
        return {
            "status": "success",
            "job_id": job_id,
            "rule_name": rule_name,
            "results": {
                "matches": results.matches,
                "total_count": results.total_count,
                "filtered_count": results.filtered_count,
                "query_time_ms": results.query_time_ms
            }
        }
        
    except Exception as e:
        logger.error(f"Error applying filter rule '{rule_name}' for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Filter rule application failed: {str(e)}"
        )


@router.get("/ip-range/{job_id}")
async def search_by_ip_range(
    job_id: str,
    ip_range: str = Query(..., description="IP range in CIDR notation (e.g., 192.168.1.0/24)"),
    field: str = Query("any", description="IP field to search (src, dst, any)")
) -> Dict[str, Any]:
    """
    Search for connections within a specific IP range.
    
    Args:
        job_id: The analysis job ID
        ip_range: IP range in CIDR notation
        field: Which IP field to search
        
    Returns:
        Search results for the IP range
    """
    try:
        logger.info(f"Searching IP range {ip_range} in job {job_id}")
        
        # Get analysis data
        analysis_data = await _get_analysis_data(job_id)
        
        # Execute IP range search
        results = await advanced_search_service.search_by_ip_range(analysis_data, ip_range, field)
        
        return {
            "status": "success",
            "job_id": job_id,
            "ip_range": ip_range,
            "field": field,
            "results": {
                "matches": results.matches,
                "total_count": results.total_count,
                "filtered_count": results.filtered_count,
                "query_time_ms": results.query_time_ms
            }
        }
        
    except Exception as e:
        logger.error(f"Error searching IP range {ip_range} for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"IP range search failed: {str(e)}"
        )


@router.get("/time-window/{job_id}")
async def search_by_time_window(
    job_id: str,
    start_time: datetime = Query(..., description="Start time (ISO format)"),
    end_time: datetime = Query(..., description="End time (ISO format)")
) -> Dict[str, Any]:
    """
    Search for connections within a specific time window.
    
    Args:
        job_id: The analysis job ID
        start_time: Start of time window
        end_time: End of time window
        
    Returns:
        Search results for the time window
    """
    try:
        logger.info(f"Searching time window {start_time} to {end_time} in job {job_id}")
        
        # Get analysis data
        analysis_data = await _get_analysis_data(job_id)
        
        # Execute time window search
        results = await advanced_search_service.search_by_time_window(analysis_data, start_time, end_time)
        
        return {
            "status": "success",
            "job_id": job_id,
            "time_window": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "results": {
                "matches": results.matches,
                "total_count": results.total_count,
                "filtered_count": results.filtered_count,
                "query_time_ms": results.query_time_ms
            }
        }
        
    except Exception as e:
        logger.error(f"Error searching time window for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Time window search failed: {str(e)}"
        )


@router.get("/security/{job_id}")
async def search_security_events(
    job_id: str,
    severity: Optional[str] = Query(None, description="Severity filter (critical, high, medium, low)")
) -> Dict[str, Any]:
    """
    Search for security-related events and anomalies.
    
    Args:
        job_id: The analysis job ID
        severity: Optional severity filter
        
    Returns:
        Security events and anomalies
    """
    try:
        logger.info(f"Searching security events in job {job_id}, severity: {severity}")
        
        # Get analysis data
        analysis_data = await _get_analysis_data(job_id)
        
        # Execute security events search
        results = await advanced_search_service.search_security_events(analysis_data, severity)
        
        return {
            "status": "success",
            "job_id": job_id,
            "severity_filter": severity,
            "results": {
                "matches": results.matches,
                "total_count": results.total_count,
                "filtered_count": results.filtered_count,
                "query_time_ms": results.query_time_ms
            }
        }
        
    except Exception as e:
        logger.error(f"Error searching security events for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Security events search failed: {str(e)}"
        )


@router.get("/suggestions/{job_id}")
async def get_search_suggestions(
    job_id: str,
    field: str = Query(..., description="Field to get suggestions for"),
    partial_value: str = Query(..., description="Partial value for autocomplete")
) -> Dict[str, Any]:
    """
    Get search suggestions for autocomplete functionality.
    
    Args:
        job_id: The analysis job ID
        field: Field to get suggestions for
        partial_value: Partial value for autocomplete
        
    Returns:
        List of suggested values
    """
    try:
        # Get analysis data
        analysis_data = await _get_analysis_data(job_id)
        
        # Get suggestions
        suggestions = await advanced_search_service.get_search_suggestions(
            analysis_data, SearchField(field), partial_value
        )
        
        return {
            "status": "success",
            "job_id": job_id,
            "field": field,
            "partial_value": partial_value,
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"Error getting search suggestions for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search suggestions failed: {str(e)}"
        )


@router.get("/statistics/{job_id}")
async def get_filter_statistics(job_id: str) -> Dict[str, Any]:
    """
    Get statistics about filterable data for UI controls.
    
    Args:
        job_id: The analysis job ID
        
    Returns:
        Statistics for various filterable fields
    """
    try:
        logger.info(f"Getting filter statistics for job {job_id}")
        
        # Get analysis data
        analysis_data = await _get_analysis_data(job_id)
        
        # Get statistics
        stats = await advanced_search_service.get_filter_statistics(analysis_data)
        
        return {
            "status": "success",
            "job_id": job_id,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting filter statistics for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Filter statistics failed: {str(e)}"
        )


@router.get("/rules")
async def get_available_filter_rules() -> Dict[str, Any]:
    """
    Get all available filter rules.
    
    Returns:
        List of available filter rules
    """
    try:
        rules = advanced_search_service.get_available_rules()
        
        return {
            "status": "success",
            "rules": rules,
            "total_rules": len(rules)
        }
        
    except Exception as e:
        logger.error(f"Error getting filter rules: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get filter rules: {str(e)}"
        )


@router.post("/rules/custom")
async def create_custom_filter_rule(rule: FilterRuleModel) -> Dict[str, Any]:
    """
    Create a custom filter rule.
    
    Args:
        rule: Filter rule to create
        
    Returns:
        Success status and rule details
    """
    try:
        logger.info(f"Creating custom filter rule: {rule.name}")
        
        # Convert Pydantic model to internal model
        search_criteria = []
        for criteria in rule.query.criteria:
            search_criteria.append(SearchCriteria(
                field=SearchField(criteria.field),
                operator=SearchOperator(criteria.operator),
                value=criteria.value,
                case_sensitive=criteria.case_sensitive
            ))
        
        search_query = SearchQuery(
            criteria=search_criteria,
            logical_operator=rule.query.logical_operator,
            limit=rule.query.limit,
            offset=rule.query.offset,
            sort_by=rule.query.sort_by,
            sort_order=rule.query.sort_order,
            group_by=rule.query.group_by
        )
        
        filter_rule = FilterRule(
            name=rule.name,
            description=rule.description,
            query=search_query,
            enabled=rule.enabled,
            priority=rule.priority
        )
        
        # Create the rule
        success = await advanced_search_service.create_custom_rule(filter_rule)
        
        if success:
            return {
                "status": "success",
                "message": f"Custom filter rule '{rule.name}' created successfully",
                "rule": {
                    "name": rule.name,
                    "description": rule.description,
                    "enabled": rule.enabled,
                    "priority": rule.priority
                }
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to create custom filter rule"
            )
        
    except Exception as e:
        logger.error(f"Error creating custom filter rule: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Custom rule creation failed: {str(e)}"
        )


@router.get("/fields")
async def get_searchable_fields() -> Dict[str, Any]:
    """
    Get information about searchable fields and operators.
    
    Returns:
        Available fields and operators for search
    """
    try:
        fields = {
            "ip_fields": [
                {"name": "src_ip", "description": "Source IP address", "type": "string"},
                {"name": "dst_ip", "description": "Destination IP address", "type": "string"},
                {"name": "any_ip", "description": "Any IP address (source or destination)", "type": "string"}
            ],
            "port_fields": [
                {"name": "src_port", "description": "Source port", "type": "integer"},
                {"name": "dst_port", "description": "Destination port", "type": "integer"},
                {"name": "any_port", "description": "Any port (source or destination)", "type": "integer"}
            ],
            "protocol_fields": [
                {"name": "protocol", "description": "Network protocol", "type": "string"},
                {"name": "protocol_layer", "description": "Protocol layer", "type": "string"}
            ],
            "traffic_fields": [
                {"name": "packet_count", "description": "Number of packets", "type": "integer"},
                {"name": "byte_count", "description": "Number of bytes", "type": "integer"},
                {"name": "duration", "description": "Connection duration", "type": "float"},
                {"name": "pps", "description": "Packets per second", "type": "float"},
                {"name": "bps", "description": "Bytes per second", "type": "float"}
            ],
            "security_fields": [
                {"name": "threat_level", "description": "Security threat level", "type": "string"},
                {"name": "security_category", "description": "Security category", "type": "string"},
                {"name": "anomaly_score", "description": "ML anomaly score", "type": "float"}
            ],
            "time_fields": [
                {"name": "start_time", "description": "Connection start time", "type": "datetime"},
                {"name": "end_time", "description": "Connection end time", "type": "datetime"},
                {"name": "timestamp", "description": "Event timestamp", "type": "datetime"}
            ]
        }
        
        operators = [
            {"name": "eq", "description": "Equals", "types": ["string", "integer", "float"]},
            {"name": "ne", "description": "Not equals", "types": ["string", "integer", "float"]},
            {"name": "contains", "description": "Contains", "types": ["string"]},
            {"name": "not_contains", "description": "Does not contain", "types": ["string"]},
            {"name": "gt", "description": "Greater than", "types": ["integer", "float", "datetime"]},
            {"name": "lt", "description": "Less than", "types": ["integer", "float", "datetime"]},
            {"name": "gte", "description": "Greater than or equal", "types": ["integer", "float", "datetime"]},
            {"name": "lte", "description": "Less than or equal", "types": ["integer", "float", "datetime"]},
            {"name": "in", "description": "In list", "types": ["string", "integer"]},
            {"name": "not_in", "description": "Not in list", "types": ["string", "integer"]},
            {"name": "regex", "description": "Regular expression", "types": ["string"]},
            {"name": "between", "description": "Between two values", "types": ["integer", "float", "datetime"]}
        ]
        
        return {
            "status": "success",
            "fields": fields,
            "operators": operators
        }
        
    except Exception as e:
        logger.error(f"Error getting searchable fields: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get searchable fields: {str(e)}"
        )


async def _get_analysis_data(job_id: str) -> Dict[str, Any]:
    """Get analysis data for a job ID."""
    try:
        # Get database connection
        db = get_database()
        reports_collection = db["reports"]
        
        # Find the analysis results
        report = reports_collection.find_one({"job_id": job_id})
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Analysis results not found"
            )
        
        if report.get("status") != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Analysis is not completed. Status: {report.get('status')}"
            )
        
        # Convert to analysis data format
        analysis_results = report.get("analysis_results", {})
        
        # Build analysis data dictionary
        analysis_data = {
            "conversations": [],
            "security_analysis": {"security_alerts": []},
            "performance_analysis": {"performance_issues": []}
        }
        
        # Extract conversations from TCP conversations
        tcp_conversations = analysis_results.get("top_tcp_conversations", [])
        for conv in tcp_conversations:
            analysis_data["conversations"].append({
                "src_ip": conv.get("src_ip"),
                "dst_ip": conv.get("dst_ip"),
                "src_port": conv.get("src_port"),
                "dst_port": conv.get("dst_port"),
                "protocol": "TCP",
                "packet_count": conv.get("packet_count", 0),
                "byte_count": conv.get("bytes", 0),
                "duration": 0,  # Not available in current format
                "threat_level": "normal",
                "security_category": "normal",
                "anomaly_score": 0
            })
        
        # Extract security alerts from network issues
        network_issues = analysis_results.get("network_issues", [])
        for issue in network_issues:
            if "security" in issue.get("type", "").lower() or "suspicious" in issue.get("description", "").lower():
                analysis_data["security_analysis"]["security_alerts"].append({
                    "type": issue.get("type", "UNKNOWN"),
                    "severity": issue.get("severity", "MEDIUM"),
                    "description": issue.get("description", "")
                })
            else:
                analysis_data["performance_analysis"]["performance_issues"].append({
                    "type": issue.get("type", "PERFORMANCE"),
                    "severity": issue.get("severity", "MEDIUM"),
                    "description": issue.get("description", "")
                })
        
        return analysis_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis data for job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis data: {str(e)}"
        )
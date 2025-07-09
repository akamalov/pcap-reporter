"""
Main API router for version 1 of the MCP PCAP Reporter API.
"""

from fastapi import APIRouter

from api.v1.endpoints import analysis, reports, health

# Create the main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"]) 
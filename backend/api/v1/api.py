"""
Main API router for version 1 of the MCP PCAP Reporter API.
"""

from fastapi import APIRouter

from api.v1.endpoints import analysis, reports, health, export, realtime, ml_analysis, diagrams, search

# Create the main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(realtime.router, prefix="/realtime", tags=["realtime"])
api_router.include_router(ml_analysis.router, prefix="/ml", tags=["machine-learning"])
api_router.include_router(diagrams.router, prefix="/diagrams", tags=["network-diagrams"])
api_router.include_router(search.router, prefix="/search", tags=["advanced-search"]) 
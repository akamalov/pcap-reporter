#!/usr/bin/env python3
"""
Basic test script to verify backend setup and functionality.
This can be run to test the basic components before full Docker deployment.
"""

import asyncio
import sys
import os
from pathlib import Path
import pytest
from httpx import AsyncClient
from main import app
from core.config import get_settings

settings = get_settings()

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def test_imports():
    """Test that all major imports work."""
    print("Testing imports...")
    
    try:
        # Test FastAPI imports
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        print("✓ FastAPI imports successful")
        
        # Test database imports
        from beanie import init_beanie
        from motor.motor_asyncio import AsyncIOMotorClient
        print("✓ Database imports successful")
        
        # Test Celery imports
        from celery import Celery
        print("✓ Celery imports successful")
        
        # Test our models
        from models.report import Report, ReportStatus, AnalysisResults
        from models.analysis_job import AnalysisJob, JobStatus
        from models.user import User
        print("✓ Model imports successful")
        
        # Test our services
        from services.pcap_analyzer import PCAPAnalyzer, analyzer
        print("✓ Service imports successful")
        
        # Test our API endpoints
        from api.v1.endpoints import health, analysis, reports
        print("✓ API endpoint imports successful")
        
        # Test our tasks
        from tasks.analysis_tasks import analyze_pcap_file, validate_pcap_file
        print("✓ Task imports successful")
        
        # Test core modules
        from core.config import Settings
        from core.celery_app import celery_app
        print("✓ Core module imports successful")
        
        print("✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        print(f"✓ Database URL: {settings.database_url}")
        print(f"✓ Redis URL: {settings.redis_url}")
        print(f"✓ Environment: {settings.environment}")
        print(f"✓ Debug mode: {settings.debug}")
        print("✅ Configuration loaded successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_analyzer():
    """Test PCAP analyzer initialization."""
    print("\nTesting PCAP analyzer...")
    
    try:
        from services.pcap_analyzer import analyzer
        print(f"✓ Analyzer initialized")
        print(f"✓ Scapy available: {analyzer.scapy_available}")
        print(f"✓ tshark path: {analyzer.tshark_path or 'Not found'}")
        print("✅ PCAP analyzer ready!")
        return True
        
    except Exception as e:
        print(f"❌ Analyzer error: {e}")
        return False

def test_fastapi_app():
    """Test FastAPI application creation."""
    print("\nTesting FastAPI application...")
    
    try:
        print(f"✓ FastAPI app created")
        print(f"✓ App title: {app.title}")
        print(f"✓ Routes count: {len(app.routes)}")
        print("✅ FastAPI application ready!")
        return True
        
    except Exception as e:
        print(f"❌ FastAPI error: {e}")
        return False

def test_celery_app():
    """Test Celery application."""
    print("\nTesting Celery application...")
    
    try:
        from core.celery_app import celery_app
        print(f"✓ Celery app created")
        print(f"✓ Broker URL: {celery_app.conf.broker_url}")
        print(f"✓ Result backend: {celery_app.conf.result_backend}")
        
        # Test task registration
        task_names = list(celery_app.tasks.keys())
        print(f"✓ Registered tasks: {len(task_names)}")
        for task_name in task_names:
            if not task_name.startswith('celery.'):
                print(f"  - {task_name}")
        
        print("✅ Celery application ready!")
        return True
        
    except Exception as e:
        print(f"❌ Celery error: {e}")
        return False

def test_mcp_server():
    """Test MCP server."""
    print("\nTesting MCP server...")
    
    try:
        from mcp_server import app as mcp_app
        print(f"✓ MCP server created")
        print(f"✓ Server name: {mcp_app.name}")
        print("✅ MCP server ready!")
        return True
        
    except Exception as e:
        print(f"❌ MCP server error: {e}")
        return False

async def main():
    """Run all tests."""
    print("🧪 PCAP Reporter Backend Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_analyzer,
        test_fastapi_app,
        test_celery_app,
        test_mcp_server,
    ]
    
    results = []
    for test in tests:
        if asyncio.iscoroutinefunction(test):
            result = await test()
        else:
            result = test()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Backend setup is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main()) 
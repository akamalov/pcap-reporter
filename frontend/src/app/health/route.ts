import { NextResponse } from 'next/server';

/**
 * Comprehensive health check endpoint for container health monitoring
 * 
 * This endpoint is used by Docker health checks and load balancers
 * to verify that the frontend service is running and responsive.
 * 
 * Enhanced features:
 * - Backend API connectivity check
 * - Memory usage monitoring
 * - Performance metrics
 * - Service dependency verification
 * 
 * Returns:
 * - 200 OK with service status information
 * - 503 Service Unavailable if critical checks fail
 */
export async function GET() {
  const startTime = Date.now();
  
  try {
    // Initialize health check data
    const healthData: any = {
      status: 'healthy',
      service: 'pcap-reporter-frontend',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      environment: process.env.NODE_ENV || 'development',
      version: process.env.npm_package_version || '1.0.0',
      checks: {
        server: 'ok',
        memory: {
          used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024), // MB
          total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024), // MB
          external: Math.round(process.memoryUsage().external / 1024 / 1024), // MB
          rss: Math.round(process.memoryUsage().rss / 1024 / 1024) // MB
        },
        backend: {
          status: 'unchecked',
          responseTime: null,
          lastCheck: null
        }
      }
    };

    // Check backend API connectivity (optional, non-blocking)
    try {
      const backendUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const backendHealthUrl = `${backendUrl}/health`;
      
      const backendStartTime = Date.now();
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout
      
      const backendResponse = await fetch(backendHealthUrl, {
        signal: controller.signal,
        headers: {
          'User-Agent': 'pcap-reporter-frontend/health-check'
        }
      });
      
      clearTimeout(timeoutId);
      const backendResponseTime = Date.now() - backendStartTime;
      
      if (backendResponse.ok) {
        healthData.checks.backend = {
          status: 'healthy',
          responseTime: backendResponseTime,
          lastCheck: new Date().toISOString()
        };
      } else {
        healthData.checks.backend = {
          status: 'degraded',
          responseTime: backendResponseTime,
          lastCheck: new Date().toISOString(),
          statusCode: backendResponse.status
        };
      }
    } catch (backendError) {
      // Backend connectivity issues don't fail the frontend health check
      healthData.checks.backend = {
        status: 'unreachable',
        responseTime: null,
        lastCheck: new Date().toISOString(),
        error: backendError instanceof Error ? backendError.message : 'Connection failed'
      };
    }

    // Add performance metrics
    const responseTime = Date.now() - startTime;
    healthData.performance = {
      responseTime,
      memoryUsagePercent: Math.round(
        (process.memoryUsage().heapUsed / process.memoryUsage().heapTotal) * 100
      )
    };

    // Determine overall health status
    let overallStatus = 'healthy';
    let httpStatus = 200;

    // Check for critical issues
    if (healthData.checks.memory.used > 1024) { // More than 1GB
      overallStatus = 'degraded';
      healthData.warnings = healthData.warnings || [];
      healthData.warnings.push('High memory usage detected');
    }

    if (responseTime > 5000) { // More than 5 seconds
      overallStatus = 'degraded';
      healthData.warnings = healthData.warnings || [];
      healthData.warnings.push('Slow response time detected');
    }

    healthData.status = overallStatus;

    return NextResponse.json(healthData, { 
      status: httpStatus,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'X-Response-Time': `${responseTime}ms`
      }
    });

  } catch (error) {
    // If health check fails, return error status
    const responseTime = Date.now() - startTime;
    
    return NextResponse.json(
      { 
        status: 'unhealthy', 
        service: 'pcap-reporter-frontend',
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error',
        performance: {
          responseTime
        }
      }, 
      { 
        status: 503,
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache', 
          'Expires': '0',
          'X-Response-Time': `${responseTime}ms`
        }
      }
    );
  }
}

/**
 * HEAD request handler for simple health checks
 * Used by some monitoring systems that only need status code
 */
export async function HEAD() {
  try {
    return new NextResponse(null, { 
      status: 200,
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate'
      }
    });
  } catch (error) {
    return new NextResponse(null, { status: 503 });
  }
}
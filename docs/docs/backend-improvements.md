# Backend Improvements and Enhancements

## Overview
This document outlines comprehensive improvements for the FastAPI backend to enhance performance, reliability, and functionality.

## 🔄 CORE ENGINE IMPROVEMENTS

### 1. Real PCAP Analysis Engine Implementation
**Priority**: Critical  
**Impact**: Replaces mock data with actual PCAP analysis

#### Current Mock Implementation Problem
```python
# backend/services/pcap_analyzer.py - CURRENT MOCK
def analyze_pcap_file(self, file_path: str) -> dict:
    return {
        "executive_summary": {
            "total_packets": 15420,  # Hardcoded mock data
            "total_bytes": 12458752,
            # ... more fake data
        }
    }
```

#### Real Implementation Solution
```python
# backend/services/pcap_analyzer.py - REAL IMPLEMENTATION
import pyshark
import scapy.all as scapy
from collections import defaultdict, Counter
import asyncio
from typing import Dict, List, Any
import subprocess
import json

class RealPCAPAnalyzer:
    def __init__(self):
        self.stats = defaultdict(int)
        self.conversations = defaultdict(int)
        self.protocols = Counter()
        self.timeline = []
        self.security_events = []

    async def analyze_pcap_file(self, file_path: str) -> Dict[str, Any]:
        """Perform comprehensive PCAP analysis using hybrid approach"""
        
        # Phase 1: High-speed triage with tshark
        basic_stats = await self._tshark_analysis(file_path)
        
        # Phase 2: Deep inspection with Scapy
        deep_analysis = await self._scapy_analysis(file_path, basic_stats)
        
        # Phase 3: Security analysis
        security_analysis = await self._security_analysis(file_path)
        
        # Phase 4: Generate network topology
        network_topology = await self._generate_topology(basic_stats, deep_analysis)
        
        return {
            "executive_summary": basic_stats,
            "protocol_analysis": deep_analysis,
            "security_analysis": security_analysis,
            "network_topology": network_topology,
            "metadata": {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "file_size": os.path.getsize(file_path),
                "analysis_duration": time.time() - start_time
            }
        }

    async def _tshark_analysis(self, file_path: str) -> Dict[str, Any]:
        """High-speed basic statistics using tshark"""
        
        # Get basic statistics
        tshark_cmd = [
            'tshark', '-r', file_path, '-q', '-z', 'conv,ip', '-z', 'prot-h'
        ]
        
        result = await asyncio.create_subprocess_exec(
            *tshark_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await result.communicate()
        
        if result.returncode != 0:
            raise ValueError(f"tshark analysis failed: {stderr.decode()}")
        
        # Parse tshark output
        return self._parse_tshark_output(stdout.decode())

    async def _scapy_analysis(self, file_path: str, basic_stats: Dict) -> Dict[str, Any]:
        """Deep packet inspection using Scapy"""
        
        packets = scapy.rdpcap(file_path)
        
        protocol_details = defaultdict(lambda: {
            'packet_count': 0,
            'byte_count': 0,
            'unique_flows': set(),
            'anomalies': []
        })
        
        for packet in packets:
            # Analyze each protocol layer
            for layer in packet.layers():
                protocol_name = layer.__name__
                protocol_details[protocol_name]['packet_count'] += 1
                protocol_details[protocol_name]['byte_count'] += len(packet)
                
                # Extract flow information
                if hasattr(packet, 'src') and hasattr(packet, 'dst'):
                    flow = f"{packet.src}->{packet.dst}"
                    protocol_details[protocol_name]['unique_flows'].add(flow)
                
                # Detect anomalies
                anomalies = self._detect_protocol_anomalies(packet, layer)
                protocol_details[protocol_name]['anomalies'].extend(anomalies)
        
        # Convert sets to lists for JSON serialization
        for protocol in protocol_details:
            protocol_details[protocol]['unique_flows'] = list(
                protocol_details[protocol]['unique_flows']
            )
        
        return dict(protocol_details)

    async def _security_analysis(self, file_path: str) -> Dict[str, Any]:
        """Security-focused analysis"""
        
        security_findings = {
            'threats_detected': [],
            'suspicious_patterns': [],
            'port_scanning': [],
            'dns_anomalies': [],
            'risk_score': 0
        }
        
        packets = scapy.rdpcap(file_path)
        
        # Track connection patterns for port scanning detection
        connection_tracker = defaultdict(set)
        dns_queries = []
        
        for packet in packets:
            # Port scanning detection
            if packet.haslayer(scapy.TCP):
                src = packet[scapy.IP].src
                dst_port = packet[scapy.TCP].dport
                connection_tracker[src].add(dst_port)
            
            # DNS analysis
            if packet.haslayer(scapy.DNS):
                dns_queries.append({
                    'query': packet[scapy.DNS].qd.qname.decode(),
                    'timestamp': packet.time,
                    'src': packet[scapy.IP].src
                })
        
        # Analyze patterns
        for src_ip, ports in connection_tracker.items():
            if len(ports) > 100:  # Potential port scan
                security_findings['port_scanning'].append({
                    'source_ip': src_ip,
                    'ports_contacted': len(ports),
                    'severity': 'high' if len(ports) > 500 else 'medium'
                })
        
        # DNS anomaly detection
        dns_domains = [q['query'] for q in dns_queries]
        suspicious_domains = self._detect_suspicious_domains(dns_domains)
        security_findings['dns_anomalies'] = suspicious_domains
        
        # Calculate risk score
        risk_score = 0
        risk_score += len(security_findings['port_scanning']) * 10
        risk_score += len(security_findings['dns_anomalies']) * 5
        security_findings['risk_score'] = min(risk_score, 100)
        
        return security_findings

    async def _generate_topology(self, basic_stats: Dict, deep_analysis: Dict) -> Dict[str, Any]:
        """Generate network topology diagram"""
        
        # Extract unique hosts and connections
        hosts = set()
        connections = []
        
        # Parse from basic stats and deep analysis
        for protocol, details in deep_analysis.items():
            for flow in details.get('unique_flows', []):
                src, dst = flow.split('->')
                hosts.add(src)
                hosts.add(dst)
                connections.append({
                    'source': src,
                    'target': dst,
                    'protocol': protocol,
                    'packets': details['packet_count']
                })
        
        # Generate Mermaid diagram
        mermaid_diagram = self._generate_mermaid_diagram(hosts, connections)
        
        return {
            'hosts': list(hosts),
            'connections': connections,
            'diagram': mermaid_diagram,
            'statistics': {
                'total_hosts': len(hosts),
                'total_connections': len(connections)
            }
        }

    def _generate_mermaid_diagram(self, hosts: set, connections: List[Dict]) -> str:
        """Generate Mermaid.js network diagram"""
        
        diagram = ["graph TD"]
        
        # Add nodes
        for i, host in enumerate(hosts):
            node_id = f"host{i}"
            diagram.append(f"    {node_id}[{host}]")
        
        # Add connections
        host_to_id = {host: f"host{i}" for i, host in enumerate(hosts)}
        
        for conn in connections[:50]:  # Limit to 50 connections for readability
            src_id = host_to_id[conn['source']]
            dst_id = host_to_id[conn['target']]
            protocol = conn['protocol']
            diagram.append(f"    {src_id} -->|{protocol}| {dst_id}")
        
        return "\n".join(diagram)

    def _detect_protocol_anomalies(self, packet, layer) -> List[Dict]:
        """Detect protocol-specific anomalies"""
        anomalies = []
        
        # TCP anomalies
        if layer.__name__ == 'TCP':
            tcp_layer = packet[scapy.TCP]
            
            # Check for unusual flag combinations
            if tcp_layer.flags & 0x3f == 0:  # No flags set
                anomalies.append({
                    'type': 'tcp_no_flags',
                    'description': 'TCP packet with no flags set',
                    'severity': 'medium'
                })
            
            # Check for Christmas tree attack
            if tcp_layer.flags & 0x3f == 0x3f:  # All flags set
                anomalies.append({
                    'type': 'tcp_christmas_tree',
                    'description': 'TCP Christmas tree attack detected',
                    'severity': 'high'
                })
        
        # HTTP anomalies
        if packet.haslayer(scapy.Raw):
            payload = packet[scapy.Raw].load.decode('utf-8', errors='ignore')
            
            # Check for SQL injection patterns
            sql_patterns = ['SELECT', 'UNION', 'DROP TABLE', '--', 'OR 1=1']
            if any(pattern in payload.upper() for pattern in sql_patterns):
                anomalies.append({
                    'type': 'potential_sql_injection',
                    'description': 'Potential SQL injection detected in payload',
                    'severity': 'high'
                })
        
        return anomalies

    def _detect_suspicious_domains(self, domains: List[str]) -> List[Dict]:
        """Detect suspicious DNS queries"""
        suspicious = []
        
        # Known suspicious patterns
        suspicious_patterns = [
            r'.*\.tk$',  # Free domains often used maliciously
            r'.*\.ml$',
            r'.*\.ga$',
            r'[0-9]{8,}\..*',  # Very long numeric subdomains
            r'.*[0-9a-f]{32,}.*',  # Hex strings (potential C2)
        ]
        
        for domain in domains:
            for pattern in suspicious_patterns:
                if re.match(pattern, domain):
                    suspicious.append({
                        'domain': domain,
                        'pattern': pattern,
                        'risk': 'medium'
                    })
                    break
        
        return suspicious
```

### 2. Streaming for Large Files
**Priority**: High  
**Impact**: Handle files >100MB efficiently

```python
# backend/services/streaming_analyzer.py
import asyncio
from typing import AsyncGenerator
import aiofiles

class StreamingPCAPAnalyzer:
    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB chunks
        self.chunk_size = chunk_size
        
    async def stream_analyze(self, file_path: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream analysis results as they become available"""
        
        file_size = os.path.getsize(file_path)
        processed_bytes = 0
        
        async with aiofiles.open(file_path, 'rb') as file:
            while chunk := await file.read(self.chunk_size):
                # Process chunk
                chunk_analysis = await self._analyze_chunk(chunk)
                
                processed_bytes += len(chunk)
                progress = (processed_bytes / file_size) * 100
                
                yield {
                    'type': 'progress',
                    'progress': progress,
                    'processed_bytes': processed_bytes,
                    'total_bytes': file_size,
                    'chunk_analysis': chunk_analysis
                }
        
        # Final aggregated results
        yield {
            'type': 'complete',
            'final_analysis': await self._aggregate_results()
        }

    async def _analyze_chunk(self, chunk: bytes) -> Dict[str, Any]:
        """Analyze a single chunk of PCAP data"""
        # Implement chunk-based analysis
        return {
            'chunk_size': len(chunk),
            'packets_in_chunk': self._count_packets_in_chunk(chunk),
            'protocols_detected': self._detect_protocols_in_chunk(chunk)
        }
```

### 3. Database Optimization
**Priority**: Medium  
**Impact**: Better performance for large datasets

```python
# backend/database/optimized_models.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, TEXT, ASCENDING, DESCENDING
import asyncio

class OptimizedDatabase:
    def __init__(self, connection_string: str):
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client.pcap_reporter
        
    async def setup_indexes(self):
        """Create optimized indexes for better query performance"""
        
        # Analysis results collection
        analysis_indexes = [
            IndexModel([("job_id", ASCENDING)], unique=True),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("file_size", ASCENDING)]),
            IndexModel([("protocols", ASCENDING)]),
            IndexModel([("security_score", DESCENDING)]),
            # Compound indexes
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)])
        ]
        
        await self.db.analysis_results.create_indexes(analysis_indexes)
        
        # Full-text search on analysis content
        text_indexes = [
            IndexModel([("executive_summary", TEXT), ("findings", TEXT)])
        ]
        
        await self.db.analysis_results.create_indexes(text_indexes)

    async def get_analysis_with_pagination(
        self, 
        page: int = 1, 
        page_size: int = 20,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Optimized pagination with filtering"""
        
        skip = (page - 1) * page_size
        query = filters or {}
        
        # Use aggregation pipeline for complex queries
        pipeline = [
            {"$match": query},
            {"$sort": {"created_at": -1}},
            {"$facet": {
                "data": [
                    {"$skip": skip},
                    {"$limit": page_size}
                ],
                "total": [
                    {"$count": "count"}
                ]
            }}
        ]
        
        result = await self.db.analysis_results.aggregate(pipeline).to_list(1)
        
        data = result[0]["data"] if result else []
        total = result[0]["total"][0]["count"] if result and result[0]["total"] else 0
        
        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }

    async def bulk_insert_analysis_data(self, data: List[Dict[str, Any]]):
        """Optimized bulk insert for large datasets"""
        
        if not data:
            return
        
        # Use bulk operations for better performance
        from pymongo import InsertOne
        
        operations = [InsertOne(doc) for doc in data]
        
        # Insert in batches to avoid memory issues
        batch_size = 1000
        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            await self.db.analysis_results.bulk_write(batch, ordered=False)
```

### 4. Enhanced Caching Layer
**Priority**: Medium  
**Impact**: Reduced computation and faster response times

```python
# backend/cache/redis_cache.py
import redis.asyncio as redis
import json
import pickle
from typing import Any, Optional, Union
import hashlib

class EnhancedCache:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.default_ttl = 3600  # 1 hour
        
    async def get_analysis_cache(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis results by file hash"""
        
        cache_key = f"analysis:{file_hash}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        return None
    
    async def set_analysis_cache(
        self, 
        file_hash: str, 
        analysis_result: Dict[str, Any],
        ttl: int = None
    ):
        """Cache analysis results"""
        
        cache_key = f"analysis:{file_hash}"
        serialized_data = json.dumps(analysis_result, default=str)
        
        await self.redis.setex(
            cache_key, 
            ttl or self.default_ttl, 
            serialized_data
        )
    
    async def cache_large_object(self, key: str, obj: Any, ttl: int = None):
        """Cache large objects using pickle for complex data types"""
        
        serialized = pickle.dumps(obj)
        compressed = gzip.compress(serialized)
        
        await self.redis.setex(
            f"large:{key}",
            ttl or self.default_ttl,
            compressed
        )
    
    async def get_large_object(self, key: str) -> Optional[Any]:
        """Retrieve large cached objects"""
        
        compressed_data = await self.redis.get(f"large:{key}")
        if compressed_data:
            serialized = gzip.decompress(compressed_data)
            return pickle.loads(serialized)
        return None
    
    def generate_file_hash(self, file_path: str) -> str:
        """Generate hash for PCAP file caching"""
        
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

# Usage in analysis service
class CachedPCAPAnalyzer:
    def __init__(self, cache: EnhancedCache):
        self.cache = cache
        self.analyzer = RealPCAPAnalyzer()
    
    async def analyze_with_cache(self, file_path: str) -> Dict[str, Any]:
        """Analyze PCAP with intelligent caching"""
        
        # Generate file hash for caching
        file_hash = self.cache.generate_file_hash(file_path)
        
        # Check cache first
        cached_result = await self.cache.get_analysis_cache(file_hash)
        if cached_result:
            return {
                **cached_result,
                "cache_hit": True,
                "cached_at": cached_result.get("analyzed_at")
            }
        
        # Perform analysis if not cached
        analysis_result = await self.analyzer.analyze_pcap_file(file_path)
        
        # Cache the result
        await self.cache.set_analysis_cache(file_hash, analysis_result)
        
        return {
            **analysis_result,
            "cache_hit": False
        }
```

---

## 🔄 API IMPROVEMENTS

### 5. WebSocket Real-time Updates
**Priority**: High  
**Impact**: Live progress updates during analysis

```python
# backend/websocket/progress_manager.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import asyncio
import json

class ProgressManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, job_id: str):
        """Connect client to job progress updates"""
        
        await websocket.accept()
        
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        
        self.active_connections[job_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, job_id: str):
        """Disconnect client from updates"""
        
        if job_id in self.active_connections:
            if websocket in self.active_connections[job_id]:
                self.active_connections[job_id].remove(websocket)
            
            # Clean up empty connection lists
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
    
    async def send_progress_update(self, job_id: str, progress_data: Dict[str, Any]):
        """Send progress update to all connected clients for a job"""
        
        if job_id not in self.active_connections:
            return
        
        message = json.dumps({
            "type": "progress_update",
            "job_id": job_id,
            "data": progress_data
        })
        
        # Send to all connected clients
        disconnected = []
        for websocket in self.active_connections[job_id]:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, job_id)

# WebSocket endpoint
@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    progress_manager = get_progress_manager()
    
    await progress_manager.connect(websocket, job_id)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        progress_manager.disconnect(websocket, job_id)

# Integration with Celery tasks
@celery_app.task(bind=True)
def analyze_pcap_with_progress(self, file_path: str, job_id: str):
    """Celery task with progress updates"""
    
    progress_manager = get_progress_manager()
    
    # Stage 1: File parsing
    asyncio.run(progress_manager.send_progress_update(job_id, {
        "stage": "parsing",
        "progress": 10,
        "message": "Parsing PCAP file structure..."
    }))
    
    # Stage 2: Basic analysis
    asyncio.run(progress_manager.send_progress_update(job_id, {
        "stage": "basic_analysis",
        "progress": 30,
        "message": "Performing basic packet analysis..."
    }))
    
    # Continue with other stages...
```

### 6. Advanced API Features
**Priority**: Medium  
**Impact**: Better developer experience and functionality

```python
# backend/api/enhanced_endpoints.py
from fastapi import FastAPI, Query, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional, List
import asyncio

@app.get("/api/reports/search")
async def search_reports(
    q: str = Query(..., description="Search query"),
    protocols: Optional[List[str]] = Query(None, description="Filter by protocols"),
    date_from: Optional[datetime] = Query(None, description="Start date"),
    date_to: Optional[datetime] = Query(None, description="End date"),
    min_size: Optional[int] = Query(None, description="Minimum file size"),
    max_size: Optional[int] = Query(None, description="Maximum file size"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """Advanced search with multiple filters"""
    
    # Build search query
    search_filters = {}
    
    if protocols:
        search_filters["protocols"] = {"$in": protocols}
    
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        search_filters["created_at"] = date_filter
    
    if min_size or max_size:
        size_filter = {}
        if min_size:
            size_filter["$gte"] = min_size
        if max_size:
            size_filter["$lte"] = max_size
        search_filters["file_size"] = size_filter
    
    # Full-text search
    if q:
        search_filters["$text"] = {"$search": q}
    
    # Execute search with pagination
    database = get_database()
    results = await database.get_analysis_with_pagination(
        page=page,
        page_size=page_size,
        filters=search_filters
    )
    
    return results

@app.get("/api/reports/{job_id}/stream")
async def stream_analysis_progress(job_id: str):
    """Stream analysis progress as Server-Sent Events"""
    
    async def event_stream():
        # Check if job exists
        job = await get_job_status(job_id)
        if not job:
            yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
            return
        
        # Stream progress updates
        while job["status"] not in ["completed", "failed"]:
            job = await get_job_status(job_id)
            
            yield f"data: {json.dumps({
                'job_id': job_id,
                'status': job['status'],
                'progress': job.get('progress', 0),
                'stage': job.get('current_stage', 'unknown'),
                'timestamp': datetime.utcnow().isoformat()
            })}\n\n"
            
            await asyncio.sleep(1)  # Update every second
        
        # Final status
        yield f"data: {json.dumps({
            'job_id': job_id,
            'status': job['status'],
            'progress': 100,
            'completed_at': job.get('completed_at')
        })}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.post("/api/reports/batch")
async def batch_analyze(
    files: List[UploadFile],
    background_tasks: BackgroundTasks,
    priority: str = "normal"
):
    """Batch upload and analysis of multiple PCAP files"""
    
    if len(files) > 10:
        raise HTTPException(400, "Maximum 10 files per batch")
    
    batch_id = str(uuid.uuid4())
    job_ids = []
    
    for file in files:
        # Validate each file
        await validate_pcap_file(file)
        
        # Save file
        file_path = await save_uploaded_file(file)
        
        # Queue analysis job
        job_id = str(uuid.uuid4())
        
        if priority == "high":
            # High priority queue
            analyze_pcap_high_priority.delay(file_path, job_id)
        else:
            # Normal priority queue
            analyze_pcap_with_progress.delay(file_path, job_id)
        
        job_ids.append(job_id)
    
    # Track batch
    await store_batch_info(batch_id, job_ids)
    
    return {
        "batch_id": batch_id,
        "job_ids": job_ids,
        "status": "queued",
        "total_files": len(files)
    }

@app.get("/api/reports/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get status of batch analysis"""
    
    batch_info = await get_batch_info(batch_id)
    if not batch_info:
        raise HTTPException(404, "Batch not found")
    
    # Get status of all jobs in batch
    job_statuses = []
    for job_id in batch_info["job_ids"]:
        job_status = await get_job_status(job_id)
        job_statuses.append(job_status)
    
    # Calculate overall progress
    total_progress = sum(job.get("progress", 0) for job in job_statuses)
    overall_progress = total_progress / len(job_statuses) if job_statuses else 0
    
    completed_jobs = [job for job in job_statuses if job["status"] == "completed"]
    failed_jobs = [job for job in job_statuses if job["status"] == "failed"]
    
    return {
        "batch_id": batch_id,
        "overall_progress": overall_progress,
        "total_jobs": len(job_statuses),
        "completed_jobs": len(completed_jobs),
        "failed_jobs": len(failed_jobs),
        "job_details": job_statuses
    }
```

---

## 🚀 PERFORMANCE OPTIMIZATIONS

### 7. Async Database Operations
**Priority**: High  
**Impact**: Better concurrency and performance

```python
# backend/database/async_operations.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Any
import logging

class AsyncDatabaseManager:
    def __init__(self, connection_string: str):
        self.client = AsyncIOMotorClient(connection_string)
        self.db = self.client.pcap_reporter
        
    async def batch_insert_with_concurrency(
        self, 
        collection_name: str, 
        documents: List[Dict[str, Any]],
        batch_size: int = 100,
        max_concurrent: int = 5
    ):
        """Insert documents with controlled concurrency"""
        
        async def insert_batch(batch):
            try:
                await self.db[collection_name].insert_many(batch, ordered=False)
                return len(batch)
            except Exception as e:
                logging.error(f"Batch insert failed: {e}")
                return 0
        
        # Split documents into batches
        batches = [
            documents[i:i + batch_size] 
            for i in range(0, len(documents), batch_size)
        ]
        
        # Process batches with limited concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_batch(batch):
            async with semaphore:
                return await insert_batch(batch)
        
        # Execute all batches concurrently
        results = await asyncio.gather(
            *[process_batch(batch) for batch in batches],
            return_exceptions=True
        )
        
        successful_inserts = sum(r for r in results if isinstance(r, int))
        return successful_inserts

    async def parallel_aggregation(
        self, 
        pipelines: List[List[Dict[str, Any]]],
        collection_name: str = "analysis_results"
    ) -> List[List[Dict[str, Any]]]:
        """Execute multiple aggregation pipelines in parallel"""
        
        async def run_pipeline(pipeline):
            cursor = self.db[collection_name].aggregate(pipeline)
            return await cursor.to_list(length=None)
        
        # Run all pipelines concurrently
        results = await asyncio.gather(
            *[run_pipeline(pipeline) for pipeline in pipelines]
        )
        
        return results
```

### 8. Memory-Efficient Processing
**Priority**: Medium  
**Impact**: Handle larger files without memory issues

```python
# backend/services/memory_efficient.py
import psutil
import gc
from typing import Generator, Dict, Any
import mmap

class MemoryEfficientAnalyzer:
    def __init__(self, max_memory_mb: int = 512):
        self.max_memory_mb = max_memory_mb
        
    def monitor_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return memory_info.rss / 1024 / 1024  # Convert to MB
    
    def should_trigger_gc(self) -> bool:
        """Check if garbage collection should be triggered"""
        current_memory = self.monitor_memory_usage()
        return current_memory > self.max_memory_mb * 0.8  # 80% threshold
    
    def process_large_pcap_chunked(self, file_path: str) -> Generator[Dict[str, Any], None, None]:
        """Process large PCAP files in memory-efficient chunks"""
        
        with open(file_path, 'rb') as f:
            # Use memory mapping for large files
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                chunk_size = 1024 * 1024  # 1MB chunks
                position = 0
                
                while position < len(mm):
                    # Read chunk
                    chunk_end = min(position + chunk_size, len(mm))
                    chunk_data = mm[position:chunk_end]
                    
                    # Process chunk
                    chunk_analysis = self._analyze_chunk_data(chunk_data)
                    
                    # Memory management
                    if self.should_trigger_gc():
                        gc.collect()  # Force garbage collection
                    
                    yield {
                        'chunk_position': position,
                        'chunk_size': len(chunk_data),
                        'analysis': chunk_analysis,
                        'memory_usage_mb': self.monitor_memory_usage()
                    }
                    
                    position = chunk_end
    
    def _analyze_chunk_data(self, chunk_data: bytes) -> Dict[str, Any]:
        """Analyze a chunk of PCAP data efficiently"""
        
        # Implement efficient chunk analysis
        packet_count = self._count_packets_in_chunk(chunk_data)
        protocols = self._extract_protocols_from_chunk(chunk_data)
        
        return {
            'packet_count': packet_count,
            'protocols': protocols,
            'chunk_size_bytes': len(chunk_data)
        }
```

---

## 📋 Implementation Timeline

### Phase 1: Critical Fixes (Week 1-2)
1. Implement real PCAP analysis engine
2. Add WebSocket real-time updates
3. Fix database connection resilience
4. Implement proper error handling

### Phase 2: Performance (Week 3-4)
1. Add streaming for large files
2. Implement enhanced caching layer
3. Optimize database operations
4. Add memory-efficient processing

### Phase 3: Advanced Features (Week 5-6)
1. Add advanced API endpoints
2. Implement batch processing
3. Add comprehensive search
4. Performance monitoring

### Phase 4: Production Ready (Week 7-8)
1. Load testing and optimization
2. Comprehensive error handling
3. Monitoring and alerting integration
4. Documentation and testing
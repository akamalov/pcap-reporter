# Infrastructure Improvements and Scalability

## Overview
This document outlines comprehensive infrastructure improvements for scalability, reliability, and production-grade deployment.

## 🚀 CONTAINERIZATION & ORCHESTRATION

### 1. Kubernetes Deployment
**Priority**: High  
**Impact**: Production-grade orchestration and auto-scaling

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: pcap-reporter
  labels:
    name: pcap-reporter
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pcap-reporter-config
  namespace: pcap-reporter
data:
  MONGODB_URL: "mongodb://mongodb-service:27017/pcap_reporter"
  REDIS_URL: "redis://redis-service:6379/0"
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: pcap-reporter-secrets
  namespace: pcap-reporter
type: Opaque
data:
  SECRET_KEY: <base64-encoded-secret>
  JWT_SECRET: <base64-encoded-jwt-secret>
  MONGO_ROOT_PASSWORD: <base64-encoded-password>
---
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-deployment
  namespace: pcap-reporter
  labels:
    app: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: pcap-reporter/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONGODB_URL
          valueFrom:
            configMapKeyRef:
              name: pcap-reporter-config
              key: MONGODB_URL
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: pcap-reporter-config
              key: REDIS_URL
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: pcap-reporter-secrets
              key: SECRET_KEY
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: upload-storage
          mountPath: /app/uploads
      volumes:
      - name: upload-storage
        persistentVolumeClaim:
          claimName: upload-pvc
---
# k8s/backend-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: pcap-reporter
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend-deployment
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
---
# k8s/celery-worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker-deployment
  namespace: pcap-reporter
  labels:
    app: celery-worker
spec:
  replicas: 5
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: celery-worker
        image: pcap-reporter/backend:latest
        command: ["celery"]
        args: ["-A", "core.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
        envFrom:
        - configMapRef:
            name: pcap-reporter-config
        - secretRef:
            name: pcap-reporter-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        volumeMounts:
        - name: upload-storage
          mountPath: /app/uploads
      volumes:
      - name: upload-storage
        persistentVolumeClaim:
          claimName: upload-pvc
---
# k8s/celery-worker-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-hpa
  namespace: pcap-reporter
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker-deployment
  minReplicas: 5
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 85
  - type: Object
    object:
      metric:
        name: redis_queue_length
      target:
        type: Value
        value: "10"
      describedObject:
        apiVersion: v1
        kind: Service
        name: redis-service
---
# k8s/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend-deployment
  namespace: pcap-reporter
  labels:
    app: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: pcap-reporter/frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "https://api.pcap-reporter.com"
        - name: NODE_ENV
          value: "production"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
# k8s/services.yaml
apiVersion: v1
kind: Service
metadata:
  name: backend-service
  namespace: pcap-reporter
spec:
  selector:
    app: backend
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: frontend-service
  namespace: pcap-reporter
spec:
  selector:
    app: frontend
  ports:
  - protocol: TCP
    port: 3000
    targetPort: 3000
  type: ClusterIP
---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pcap-reporter-ingress
  namespace: pcap-reporter
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "2g"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - pcap-reporter.com
    - api.pcap-reporter.com
    secretName: pcap-reporter-tls
  rules:
  - host: pcap-reporter.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 3000
  - host: api.pcap-reporter.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
```

### 2. Advanced Storage Solutions
**Priority**: High  
**Impact**: Scalable and reliable data storage

```yaml
# k8s/storage.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: upload-pvc
  namespace: pcap-reporter
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: nfs-client
  resources:
    requests:
      storage: 1Ti
---
# k8s/mongodb-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mongodb
  namespace: pcap-reporter
spec:
  serviceName: mongodb-service
  replicas: 3
  selector:
    matchLabels:
      app: mongodb
  template:
    metadata:
      labels:
        app: mongodb
    spec:
      containers:
      - name: mongodb
        image: mongo:7.0
        ports:
        - containerPort: 27017
        env:
        - name: MONGO_INITDB_ROOT_USERNAME
          value: "admin"
        - name: MONGO_INITDB_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: pcap-reporter-secrets
              key: MONGO_ROOT_PASSWORD
        - name: MONGO_INITDB_DATABASE
          value: "pcap_reporter"
        volumeMounts:
        - name: mongodb-data
          mountPath: /data/db
        - name: mongodb-config
          mountPath: /etc/mongod.conf
          subPath: mongod.conf
        livenessProbe:
          exec:
            command:
            - mongosh
            - --eval
            - "db.adminCommand('ping')"
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - mongosh
            - --eval
            - "db.adminCommand('ping')"
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      volumes:
      - name: mongodb-config
        configMap:
          name: mongodb-config
  volumeClaimTemplates:
  - metadata:
      name: mongodb-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: ssd-fast
      resources:
        requests:
          storage: 100Gi
---
# k8s/redis-cluster.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
  namespace: pcap-reporter
spec:
  serviceName: redis-cluster-service
  replicas: 6
  selector:
    matchLabels:
      app: redis-cluster
  template:
    metadata:
      labels:
        app: redis-cluster
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        - containerPort: 16379
        command:
        - redis-server
        - /etc/redis/redis.conf
        - --cluster-enabled
        - "yes"
        - --cluster-config-file
        - /data/nodes.conf
        - --cluster-node-timeout
        - "5000"
        - --appendonly
        - "yes"
        volumeMounts:
        - name: redis-data
          mountPath: /data
        - name: redis-config
          mountPath: /etc/redis
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
      volumes:
      - name: redis-config
        configMap:
          name: redis-config
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: ssd-fast
      resources:
        requests:
          storage: 20Gi
```

---

## 📊 MONITORING & OBSERVABILITY

### 3. Comprehensive Monitoring Stack
**Priority**: High  
**Impact**: Production monitoring and alerting

```yaml
# monitoring/prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: pcap-reporter
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    rule_files:
      - "/etc/prometheus/rules/*.yml"
    
    alerting:
      alertmanagers:
        - static_configs:
            - targets: ["alertmanager:9093"]
    
    scrape_configs:
      # Kubernetes API server
      - job_name: 'kubernetes-apiservers'
        kubernetes_sd_configs:
        - role: endpoints
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        relabel_configs:
        - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
          action: keep
          regex: default;kubernetes;https
      
      # Application metrics
      - job_name: 'pcap-reporter-backend'
        kubernetes_sd_configs:
        - role: pod
        relabel_configs:
        - source_labels: [__meta_kubernetes_pod_label_app]
          action: keep
          regex: backend
        - source_labels: [__meta_kubernetes_pod_ip]
          target_label: __address__
          replacement: ${1}:8000
      
      - job_name: 'pcap-reporter-celery'
        kubernetes_sd_configs:
        - role: pod
        relabel_configs:
        - source_labels: [__meta_kubernetes_pod_label_app]
          action: keep
          regex: celery-worker
        - source_labels: [__meta_kubernetes_pod_ip]
          target_label: __address__
          replacement: ${1}:9540  # Celery metrics port
      
      # Infrastructure metrics
      - job_name: 'mongodb-exporter'
        static_configs:
        - targets: ['mongodb-exporter:9216']
      
      - job_name: 'redis-exporter'
        static_configs:
        - targets: ['redis-exporter:9121']
      
      - job_name: 'node-exporter'
        kubernetes_sd_configs:
        - role: node
        relabel_configs:
        - source_labels: [__address__]
          regex: '(.*):10250'
          target_label: __address__
          replacement: '${1}:9100'
---
# monitoring/alert-rules.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: pcap-reporter
data:
  pcap-reporter.yml: |
    groups:
    - name: pcap-reporter.rules
      rules:
      
      # High CPU usage
      - alert: HighCPUUsage
        expr: rate(container_cpu_usage_seconds_total{pod=~".*pcap-reporter.*"}[5m]) * 100 > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "Pod {{ $labels.pod }} CPU usage is above 80%"
      
      # High memory usage
      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes{pod=~".*pcap-reporter.*"} / container_spec_memory_limit_bytes * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage detected"
          description: "Pod {{ $labels.pod }} memory usage is above 85%"
      
      # Queue backup
      - alert: CeleryQueueBackup
        expr: celery_queue_length > 100
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Celery queue backup detected"
          description: "Queue length is {{ $value }}, indicating processing bottleneck"
      
      # Failed analysis rate
      - alert: HighAnalysisFailureRate
        expr: rate(pcap_analysis_failures_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High analysis failure rate"
          description: "Analysis failure rate is {{ $value }} per second"
      
      # Database connection issues
      - alert: DatabaseConnectionFailure
        expr: mongodb_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "MongoDB connection failure"
          description: "Cannot connect to MongoDB"
      
      # Redis connection issues
      - alert: RedisConnectionFailure
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis connection failure"
          description: "Cannot connect to Redis"
      
      # Disk space
      - alert: LowDiskSpace
        expr: node_filesystem_avail_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes * 100 < 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Filesystem {{ $labels.mountpoint }} has less than 10% space remaining"
```

### 4. Application Performance Monitoring
**Priority**: Medium  
**Impact**: Deep application insights and optimization

```python
# backend/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
import functools
from typing import Callable, Any
import asyncio

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ANALYSIS_DURATION = Histogram(
    'pcap_analysis_duration_seconds',
    'PCAP analysis duration in seconds',
    ['file_size_category']
)

ANALYSIS_QUEUE_LENGTH = Gauge(
    'celery_queue_length',
    'Current length of Celery task queue'
)

ANALYSIS_FAILURES = Counter(
    'pcap_analysis_failures_total',
    'Total number of failed PCAP analyses',
    ['error_type']
)

ACTIVE_USERS = Gauge(
    'active_users_total',
    'Number of currently active users'
)

UPLOAD_FILE_SIZE = Histogram(
    'upload_file_size_bytes',
    'Size of uploaded files in bytes'
)

DATABASE_OPERATIONS = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'collection', 'status']
)

def metrics_middleware():
    """Middleware to collect HTTP metrics"""
    
    async def middleware(request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
    
    return middleware

def monitor_analysis_time(func: Callable) -> Callable:
    """Decorator to monitor analysis execution time"""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        file_path = args[1] if len(args) > 1 else kwargs.get('file_path')
        
        # Determine file size category
        try:
            file_size = os.path.getsize(file_path)
            if file_size < 10 * 1024 * 1024:  # < 10MB
                size_category = 'small'
            elif file_size < 100 * 1024 * 1024:  # < 100MB
                size_category = 'medium'
            else:
                size_category = 'large'
        except:
            size_category = 'unknown'
        
        try:
            result = await func(*args, **kwargs)
            
            # Record successful analysis time
            duration = time.time() - start_time
            ANALYSIS_DURATION.labels(file_size_category=size_category).observe(duration)
            
            return result
            
        except Exception as e:
            # Record failure
            error_type = type(e).__name__
            ANALYSIS_FAILURES.labels(error_type=error_type).inc()
            raise
    
    return wrapper

def monitor_database_operations(func: Callable) -> Callable:
    """Decorator to monitor database operations"""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        operation = func.__name__
        collection = kwargs.get('collection', 'unknown')
        
        try:
            result = await func(*args, **kwargs)
            
            DATABASE_OPERATIONS.labels(
                operation=operation,
                collection=collection,
                status='success'
            ).inc()
            
            return result
            
        except Exception as e:
            DATABASE_OPERATIONS.labels(
                operation=operation,
                collection=collection,
                status='error'
            ).inc()
            raise
    
    return wrapper

# Metrics collection tasks
@celery_app.task
def collect_queue_metrics():
    """Collect Celery queue metrics"""
    
    # Get active task count from Redis
    redis_client = get_redis_client()
    queue_length = redis_client.llen('celery')
    
    ANALYSIS_QUEUE_LENGTH.set(queue_length)

@celery_app.task
def collect_user_metrics():
    """Collect active user metrics"""
    
    # Count active sessions
    redis_client = get_redis_client()
    active_sessions = len(redis_client.keys('session:*'))
    
    ACTIVE_USERS.set(active_sessions)

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )

# Custom metrics for business logic
class BusinessMetrics:
    def __init__(self):
        self.successful_analyses = Counter(
            'successful_analyses_total',
            'Total successful PCAP analyses'
        )
        
        self.user_registrations = Counter(
            'user_registrations_total',
            'Total user registrations'
        )
        
        self.pdf_exports = Counter(
            'pdf_exports_total',
            'Total PDF report exports'
        )
    
    def record_successful_analysis(self):
        self.successful_analyses.inc()
    
    def record_user_registration(self):
        self.user_registrations.inc()
    
    def record_pdf_export(self):
        self.pdf_exports.inc()

# Usage in application code
business_metrics = BusinessMetrics()

@app.post("/api/auth/register")
async def register_user(user_data: UserCreate):
    # ... registration logic ...
    
    business_metrics.record_user_registration()
    
    return {"message": "User registered successfully"}

@monitor_analysis_time
async def analyze_pcap_file(self, file_path: str) -> dict:
    # ... analysis logic ...
    
    business_metrics.record_successful_analysis()
    
    return analysis_result
```

### 5. Log Aggregation and Analysis
**Priority**: Medium  
**Impact**: Centralized logging and troubleshooting

```yaml
# logging/fluentd-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: pcap-reporter
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/*pcap-reporter*.log
      pos_file /var/log/fluentd-containers.log.pos
      tag kubernetes.*
      read_from_head true
      <parse>
        @type json
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </source>
    
    <filter kubernetes.**>
      @type kubernetes_metadata
    </filter>
    
    <filter kubernetes.**>
      @type grep
      <regexp>
        key log
        pattern /(ERROR|WARN|INFO)/
      </regexp>
    </filter>
    
    <match kubernetes.**>
      @type elasticsearch
      host elasticsearch-service
      port 9200
      index_name pcap-reporter-logs
      type_name _doc
      include_tag_key true
      tag_key @log_name
      flush_interval 1s
      <buffer>
        @type file
        path /var/log/fluentd-buffers/kubernetes.system.buffer
        flush_mode interval
        retry_type exponential_backoff
        flush_thread_count 2
        flush_interval 5s
        retry_forever
        retry_max_interval 30
        chunk_limit_size 2M
        queue_limit_length 8
        overflow_action block
      </buffer>
    </match>
---
# logging/elasticsearch-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch
  namespace: pcap-reporter
spec:
  replicas: 3
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
        ports:
        - containerPort: 9200
        - containerPort: 9300
        env:
        - name: discovery.type
          value: "single-node"
        - name: ES_JAVA_OPTS
          value: "-Xms1g -Xmx1g"
        - name: xpack.security.enabled
          value: "false"
        volumeMounts:
        - name: elasticsearch-data
          mountPath: /usr/share/elasticsearch/data
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
      volumes:
      - name: elasticsearch-data
        persistentVolumeClaim:
          claimName: elasticsearch-pvc
```

---

## 🔄 CI/CD PIPELINE

### 6. GitLab CI/CD Configuration
**Priority**: High  
**Impact**: Automated testing and deployment

```yaml
# .gitlab-ci.yml
stages:
  - test
  - security
  - build
  - deploy

variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: "/certs"
  
before_script:
  - docker info

# Test Stage
test-backend:
  stage: test
  image: python:3.11
  services:
    - mongodb:7.0
    - redis:7-alpine
  variables:
    MONGODB_URL: "mongodb://mongodb:27017/test"
    REDIS_URL: "redis://redis:6379/0"
  before_script:
    - cd backend
    - pip install -r requirements.txt
    - pip install pytest pytest-asyncio pytest-cov
  script:
    - pytest tests/ --cov=. --cov-report=xml --cov-report=term
    - python -m coverage report --fail-under=80
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: backend/coverage.xml
  coverage: '/TOTAL.*\s+(\d+%)$/'

test-frontend:
  stage: test
  image: node:18-alpine
  before_script:
    - cd frontend
    - npm ci
  script:
    - npm run lint
    - npm run type-check
    - npm run test:coverage
  artifacts:
    reports:
      junit: frontend/junit.xml
      coverage_report:
        coverage_format: cobertura
        path: frontend/coverage/cobertura-coverage.xml
  coverage: '/Lines\s*:\s*(\d+\.\d+)%/'

# Security Stage
security-scan:
  stage: security
  image: owasp/zap2docker-stable
  script:
    - mkdir -p /zap/wrk/
    - zap-baseline.py -t http://localhost:8000 -J gl-sast-report.json || true
  artifacts:
    reports:
      sast: gl-sast-report.json
  allow_failure: true

dependency-scan:
  stage: security
  image: python:3.11
  before_script:
    - pip install safety bandit
  script:
    - cd backend
    - safety check -r requirements.txt --json --output safety-report.json || true
    - bandit -r . -f json -o bandit-report.json || true
  artifacts:
    reports:
      dependency_scanning: backend/safety-report.json
      sast: backend/bandit-report.json
  allow_failure: true

# Build Stage
build-backend:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - cd backend
    - docker build -t $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA
    - docker tag $CI_REGISTRY_IMAGE/backend:$CI_COMMIT_SHA $CI_REGISTRY_IMAGE/backend:latest
    - docker push $CI_REGISTRY_IMAGE/backend:latest
  only:
    - main
    - develop

build-frontend:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - cd frontend
    - docker build -t $CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA
    - docker tag $CI_REGISTRY_IMAGE/frontend:$CI_COMMIT_SHA $CI_REGISTRY_IMAGE/frontend:latest
    - docker push $CI_REGISTRY_IMAGE/frontend:latest
  only:
    - main
    - develop

# Deploy Stage
deploy-staging:
  stage: deploy
  image: bitnami/kubectl:latest
  before_script:
    - kubectl config use-context $KUBE_CONTEXT_STAGING
  script:
    - sed -i "s|IMAGE_TAG|$CI_COMMIT_SHA|g" k8s/staging/*.yaml
    - kubectl apply -f k8s/staging/
    - kubectl rollout status deployment/backend-deployment -n pcap-reporter-staging
    - kubectl rollout status deployment/frontend-deployment -n pcap-reporter-staging
    - kubectl rollout status deployment/celery-worker-deployment -n pcap-reporter-staging
  environment:
    name: staging
    url: https://staging.pcap-reporter.com
  only:
    - develop

deploy-production:
  stage: deploy
  image: bitnami/kubectl:latest
  before_script:
    - kubectl config use-context $KUBE_CONTEXT_PRODUCTION
  script:
    - sed -i "s|IMAGE_TAG|$CI_COMMIT_SHA|g" k8s/production/*.yaml
    - kubectl apply -f k8s/production/
    - kubectl rollout status deployment/backend-deployment -n pcap-reporter
    - kubectl rollout status deployment/frontend-deployment -n pcap-reporter
    - kubectl rollout status deployment/celery-worker-deployment -n pcap-reporter
  environment:
    name: production
    url: https://pcap-reporter.com
  when: manual
  only:
    - main

# Database Migration Job
migrate-database:
  stage: deploy
  image: python:3.11
  before_script:
    - pip install alembic pymongo
  script:
    - cd backend
    - python -c "from database.migrations import run_migrations; run_migrations()"
  only:
    - main
    - develop
  when: manual
```

### 7. Automated Testing Strategy
**Priority**: High  
**Impact**: Quality assurance and regression prevention

```python
# backend/tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from main import app
from database.connection import get_database
from core.config import get_settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db():
    """Create test database."""
    settings = get_settings()
    client = AsyncIOMotorClient(settings.TEST_MONGODB_URL)
    db = client.pcap_reporter_test
    
    # Clean database before test
    await db.drop_collection("analysis_results")
    await db.drop_collection("users")
    
    yield db
    
    # Clean up after test
    await client.drop_database("pcap_reporter_test")
    client.close()

@pytest.fixture
async def test_redis():
    """Create test Redis client."""
    settings = get_settings()
    redis_client = redis.from_url(settings.TEST_REDIS_URL)
    
    # Clean Redis before test
    await redis_client.flushdb()
    
    yield redis_client
    
    # Clean up after test
    await redis_client.flushdb()
    await redis_client.close()

@pytest.fixture
async def test_client(test_db, test_redis):
    """Create test HTTP client."""
    
    # Override dependencies
    app.dependency_overrides[get_database] = lambda: test_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Clear overrides
    app.dependency_overrides.clear()

@pytest.fixture
def sample_pcap_file():
    """Create sample PCAP file for testing."""
    import tempfile
    import scapy.all as scapy
    
    # Create sample packets
    packets = []
    for i in range(100):
        packet = scapy.IP(src="192.168.1.1", dst="192.168.1.2") / scapy.TCP(sport=1234, dport=80)
        packets.append(packet)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as f:
        scapy.wrpcap(f.name, packets)
        yield f.name
    
    # Clean up
    os.unlink(f.name)

# backend/tests/test_analysis.py
import pytest
from services.pcap_analyzer import PCAPAnalyzer
from services.streaming_analyzer import StreamingPCAPAnalyzer

@pytest.mark.asyncio
async def test_pcap_analysis_basic(sample_pcap_file):
    """Test basic PCAP analysis functionality."""
    
    analyzer = PCAPAnalyzer()
    result = await analyzer.analyze_pcap_file(sample_pcap_file)
    
    assert result is not None
    assert "executive_summary" in result
    assert "protocol_analysis" in result
    assert result["executive_summary"]["total_packets"] == 100

@pytest.mark.asyncio
async def test_streaming_analysis(sample_pcap_file):
    """Test streaming analysis for large files."""
    
    analyzer = StreamingPCAPAnalyzer(chunk_size=1024)
    
    progress_updates = []
    async for update in analyzer.stream_analyze(sample_pcap_file):
        progress_updates.append(update)
    
    assert len(progress_updates) > 0
    assert progress_updates[-1]["type"] == "complete"

@pytest.mark.asyncio
async def test_analysis_error_handling():
    """Test analysis error handling for invalid files."""
    
    analyzer = PCAPAnalyzer()
    
    with pytest.raises(ValueError):
        await analyzer.analyze_pcap_file("/nonexistent/file.pcap")

# Load testing
@pytest.mark.asyncio
async def test_concurrent_analysis(sample_pcap_file):
    """Test concurrent analysis processing."""
    
    analyzer = PCAPAnalyzer()
    
    # Run multiple analyses concurrently
    tasks = []
    for i in range(10):
        task = analyzer.analyze_pcap_file(sample_pcap_file)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 10
    assert all(result is not None for result in results)

# Performance testing
@pytest.mark.performance
async def test_analysis_performance(sample_pcap_file):
    """Test analysis performance benchmarks."""
    
    import time
    
    analyzer = PCAPAnalyzer()
    
    start_time = time.time()
    result = await analyzer.analyze_pcap_file(sample_pcap_file)
    end_time = time.time()
    
    execution_time = end_time - start_time
    
    # Analysis should complete within reasonable time
    assert execution_time < 10.0  # 10 seconds max for test file
    assert result["metadata"]["analysis_duration"] < 10.0

# Integration tests
@pytest.mark.integration
async def test_full_upload_analysis_workflow(test_client, sample_pcap_file):
    """Test complete upload and analysis workflow."""
    
    # Upload file
    with open(sample_pcap_file, "rb") as f:
        response = await test_client.post(
            "/api/reports/upload",
            files={"file": ("test.pcap", f, "application/vnd.tcpdump.pcap")}
        )
    
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    # Wait for analysis completion
    for _ in range(30):  # 30 seconds timeout
        response = await test_client.get(f"/api/reports/{job_id}")
        
        if response.status_code == 200:
            result = response.json()
            if result["status"] == "completed":
                break
        
        await asyncio.sleep(1)
    
    assert result["status"] == "completed"
    assert "analysis_result" in result
```

---

## 📋 Implementation Roadmap

### Phase 1: Core Infrastructure (Month 1)
1. Kubernetes deployment configuration
2. Monitoring and alerting setup
3. CI/CD pipeline implementation
4. Basic auto-scaling configuration

### Phase 2: Advanced Features (Month 2)
1. Advanced storage solutions
2. Load balancing and high availability
3. Comprehensive logging system
4. Performance optimization

### Phase 3: Production Hardening (Month 3)
1. Security hardening
2. Disaster recovery planning
3. Performance tuning
4. Documentation and runbooks

### Phase 4: Optimization (Month 4)
1. Cost optimization
2. Advanced monitoring features
3. Capacity planning
4. Long-term maintenance strategy
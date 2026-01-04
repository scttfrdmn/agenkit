# Agenkit Docker Compose Deployment

Production-ready Docker Compose configuration for deploying Agenkit agents with complete observability stack.

## Overview

This deployment provides a turnkey solution for running Agenkit in production with:

- ✅ **Multi-Runtime Agents**: Python and Go agents running side-by-side
- ✅ **Load Balancing**: Nginx with round-robin and health checks
- ✅ **State Management**: Redis for caching and sessions
- ✅ **Persistence**: PostgreSQL for data storage
- ✅ **Metrics**: Prometheus + Grafana dashboards
- ✅ **Tracing**: Jaeger for distributed tracing
- ✅ **Container Metrics**: cAdvisor and Node Exporter
- ✅ **Health Checks**: Automated health monitoring
- ✅ **Resource Limits**: CPU and memory constraints
- ✅ **Auto-Restart**: Failure recovery

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  Nginx (8080)    │  Load Balancer
└────┬────────┬────┘
     │        │
     ▼        ▼
┌─────────┐ ┌─────────┐
│ Python  │ │   Go    │  Agents
│  Agent  │ │  Agent  │
└────┬────┘ └────┬────┘
     │           │
     ├───────────┴───────┐
     │                   │
     ▼                   ▼
┌─────────┐         ┌──────────┐
│  Redis  │         │Postgres  │  Data Layer
└─────────┘         └──────────┘
     │                   │
     └───────┬───────────┘
             │
    ┌────────▼────────┐
    │  Observability  │  Monitoring
    ├─────────────────┤
    │  Prometheus     │
    │  Grafana        │
    │  Jaeger         │
    │  cAdvisor       │
    └─────────────────┘
```

## Quick Start

### 1. Prerequisites

- Docker Engine 24.0+
- Docker Compose 2.20+
- 4GB+ available RAM
- 10GB+ available disk space

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env

# Set LLM API keys (required)
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Deploy

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:8080 | - |
| **Grafana** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **Jaeger** | http://localhost:16686 | - |
| **Redis Commander** | http://localhost:8081 | - |
| **pgAdmin** | http://localhost:5050 | - |

### 5. Test Deployment

```bash
# Test Python agent
curl -X POST http://localhost:8080/api/python/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "user",
      "content": "Calculate 10 + 5"
    }
  }'

# Test Go agent
curl -X POST http://localhost:8080/api/go/agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "user",
      "content": "Hello! How are you?"
    }
  }'

# Health check
curl http://localhost:8080/health
```

## Development Mode

For local development with hot reload:

```bash
# Start development stack
docker-compose -f docker-compose.dev.yml up

# Python agent available at: http://localhost:8000
# Go agent available at: http://localhost:8001
# Redis GUI: http://localhost:8081
# pgAdmin: http://localhost:5050
```

**Development features:**
- Hot reload for code changes
- Debug ports exposed (Python: 5678, Go: 2345)
- Simplified configuration
- Development tools included (Redis Commander, pgAdmin)

## Configuration

### Agent Configuration

**Python Agent** (`docker-compose.yml`):
```yaml
environment:
  - AGENT_TYPE=react           # react, conversational, router
  - LOG_LEVEL=INFO             # DEBUG, INFO, WARNING, ERROR
  - REDIS_URL=redis://redis:6379/0
  - DATABASE_URL=postgresql://...
```

**Go Agent**:
```yaml
environment:
  - AGENT_TYPE=conversational
  - LOG_LEVEL=INFO
  - REDIS_URL=redis://redis:6379/1
  - DATABASE_URL=postgresql://...
```

### Resource Limits

Adjust in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

### Scaling

Scale services horizontally:

```bash
# Scale Python agents
docker-compose up -d --scale agenkit-python=3

# Scale Go agents
docker-compose up -d --scale agenkit-go=3

# Nginx will automatically load balance across all instances
```

## Observability

### Grafana Dashboards

**Pre-configured dashboards:**
1. **Agenkit Overview** - Request rate, errors, latency, resource usage
2. **Container Metrics** - CPU, memory, network, disk I/O
3. **Database Metrics** - Connections, queries, performance
4. **Redis Metrics** - Commands, keys, memory

**Access:** http://localhost:3000 (admin/admin)

### Prometheus Metrics

**Agent metrics:**
- `agenkit_requests_total` - Total requests
- `agenkit_errors_total` - Total errors
- `agenkit_request_duration_seconds` - Request latency histogram
- `agenkit_active_connections` - Active connections

**Query examples:**
```promql
# Request rate
rate(agenkit_requests_total[5m])

# Error rate
rate(agenkit_errors_total[5m]) / rate(agenkit_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(agenkit_request_duration_seconds_bucket[5m]))
```

**Access:** http://localhost:9090

### Jaeger Tracing

**View traces:** http://localhost:16686

**Trace structure:**
1. **Nginx** - Load balancer span
2. **Agent** - Agent processing span
3. **LLM** - LLM API call span
4. **Database** - Database query spans
5. **Redis** - Cache operation spans

**Use cases:**
- Identify slow requests
- Debug errors
- Optimize performance
- Analyze dependencies

### Alerts

Prometheus alerts configured in `prometheus/alerts.yml`:

- **AgentDown** - Agent service unavailable
- **AgentHighErrorRate** - Error rate > 5%
- **AgentHighLatency** - P95 latency > 5s
- **HighCPUUsage** - CPU usage > 80%
- **HighMemoryUsage** - Memory usage > 90%
- **PostgresDown** - Database unavailable
- **RedisDown** - Cache unavailable

**View alerts:** http://localhost:9090/alerts

## Persistence

### Data Volumes

Persistent data stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep agenkit

# Backup volume
docker run --rm -v agenkit_postgres-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz /data

# Restore volume
docker run --rm -v agenkit_postgres-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/postgres-backup.tar.gz -C /
```

### PostgreSQL Backups

**Manual backup:**
```bash
docker-compose exec postgres pg_dump -U agenkit agenkit > backup.sql
```

**Automated backups** (add to cron):
```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/docker-compose && \
  docker-compose exec -T postgres pg_dump -U agenkit agenkit | \
  gzip > /backups/agenkit-$(date +\%Y\%m\%d).sql.gz
```

**Restore:**
```bash
docker-compose exec -T postgres psql -U agenkit agenkit < backup.sql
```

### Redis Persistence

Redis configured with AOF persistence:

```bash
# Force save
docker-compose exec redis redis-cli BGSAVE

# View persistence stats
docker-compose exec redis redis-cli INFO persistence
```

## Security

### Production Checklist

- [ ] Change default passwords in `.env`
- [ ] Enable SSL/TLS for Nginx
- [ ] Use Docker Secrets for API keys
- [ ] Enable authentication for Grafana
- [ ] Enable authentication for Prometheus
- [ ] Restrict network access (firewall rules)
- [ ] Enable audit logging
- [ ] Implement rate limiting
- [ ] Use non-root users in containers
- [ ] Scan images for vulnerabilities
- [ ] Keep Docker and images updated

### SSL/TLS Configuration

**Generate self-signed certificate:**
```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem
```

**Enable HTTPS** in `nginx/conf.d/agenkit.conf`:
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ... (see commented section)
}
```

**Update `docker-compose.yml`:**
```yaml
environment:
  - SSL_ENABLED=true
```

### Docker Secrets

For production, use Docker Secrets instead of environment variables:

```bash
# Create secrets
echo "sk-..." | docker secret create openai_api_key -
echo "sk-ant-..." | docker secret create anthropic_api_key -

# Update docker-compose.yml
secrets:
  - openai_api_key
  - anthropic_api_key
```

## Monitoring and Maintenance

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f agenkit-python

# Last 100 lines
docker-compose logs --tail=100 agenkit-python

# Errors only
docker-compose logs | grep ERROR
```

### Service Status

```bash
# Check all services
docker-compose ps

# Check specific service
docker-compose ps agenkit-python

# Resource usage
docker stats
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart agenkit-python

# Rebuild and restart
docker-compose up -d --build agenkit-python
```

### Update Services

```bash
# Pull latest images
docker-compose pull

# Rebuild custom images
docker-compose build --no-cache

# Restart with new images
docker-compose up -d
```

## Performance Tuning

### Nginx Optimization

**Increase worker connections** (`nginx/nginx.conf`):
```nginx
events {
    worker_connections 4096;  # Increase from 2048
}
```

**Enable caching**:
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=agenkit_cache:10m;
proxy_cache agenkit_cache;
proxy_cache_valid 200 1m;
```

### Database Optimization

**PostgreSQL** (`docker-compose.yml`):
```yaml
command:
  - postgres
  - -c
  - shared_buffers=256MB
  - -c
  - effective_cache_size=1GB
  - -c
  - max_connections=200
```

**Connection pooling** (PgBouncer):
```yaml
pgbouncer:
  image: pgbouncer/pgbouncer:latest
  environment:
    - DATABASES_HOST=postgres
    - POOL_MODE=transaction
    - MAX_CLIENT_CONN=1000
```

### Redis Optimization

**Increase memory** (`.env`):
```bash
REDIS_MAXMEMORY=512mb  # Increase from 256mb
```

**Configure eviction**:
```yaml
command: >
  redis-server
  --maxmemory 512mb
  --maxmemory-policy allkeys-lru
```

## Troubleshooting

### Common Issues

#### Issue: Services not starting

**Solution:**
```bash
# Check logs
docker-compose logs

# Verify system resources
docker system df
docker system prune  # Clean up if needed

# Check port conflicts
netstat -tulpn | grep -E '(8080|3000|9090)'
```

#### Issue: High memory usage

**Solution:**
```bash
# Check container stats
docker stats

# Reduce resource limits in docker-compose.yml
# Increase swap space
```

#### Issue: Database connection errors

**Solution:**
```bash
# Check PostgreSQL status
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U agenkit -d agenkit
```

#### Issue: Metrics not appearing in Grafana

**Solution:**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify datasource in Grafana
# Settings > Data Sources > Prometheus

# Check Prometheus logs
docker-compose logs prometheus
```

### Debug Mode

Enable debug logging:

```yaml
# docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG
  - DEBUG_MODE=true
```

Restart services:
```bash
docker-compose up -d
docker-compose logs -f agenkit-python
```

## Cost and Resources

### Resource Requirements

**Minimum:**
- 4 CPU cores
- 4GB RAM
- 20GB disk

**Recommended:**
- 8 CPU cores
- 8GB RAM
- 50GB disk

**Production:**
- 16+ CPU cores
- 16GB+ RAM
- 100GB+ disk (SSD)

### Cost Estimate (AWS)

**t3.xlarge instance** (4 vCPU, 16 GB):
- Instance: ~$140/month
- Storage (50 GB): ~$5/month
- **Total: ~$145/month**

**t3.2xlarge instance** (8 vCPU, 32 GB):
- Instance: ~$280/month
- Storage (100 GB): ~$10/month
- **Total: ~$290/month**

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: Deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Complete cleanup
docker-compose down -v --rmi all --remove-orphans
```

## Next Steps

- [ ] Add real LLM integrations (OpenAI, Anthropic, Bedrock)
- [ ] Configure SSL/TLS certificates
- [ ] Set up automated backups
- [ ] Implement CI/CD pipeline
- [ ] Configure monitoring alerts
- [ ] Add custom Grafana dashboards
- [ ] Implement log aggregation (ELK stack)
- [ ] Add API documentation (Swagger/OpenAPI)

## Support

For issues and questions:
- GitHub Issues: https://github.com/agenkit/agenkit/issues
- Documentation: https://docs.agenkit.dev

# Agenkit Performance Optimization Review - Executive Summary

**Report Location**: `/Users/scttfrdmn/src/agenkit/PERFORMANCE_OPTIMIZATION_REVIEW.md`  
**Date**: November 16, 2025

---

## Key Findings

| Category | Current State | Improvement Potential | Priority |
|----------|---------------|----------------------|----------|
| **Connection Management** | No pooling/keep-alive | 20-35% latency reduction | CRITICAL |
| **Message Serialization** | 18 JSON encode/decode cycles | 15-30% reduction | HIGH |
| **Caching** | Good LRU, full locks | 40-80% concurrent latency improvement | HIGH |
| **Async/Concurrency** | Good patterns, polling overhead | 50% CPU reduction for idle | MEDIUM |
| **Memory Management** | Stable, no leaks | Prevention of edge cases | LOW-MEDIUM |
| **Middleware Overhead** | Excellent (2.57-6.26µs) | 10-15% reduction possible | LOW |
| **Network** | HTTP/2 good, no compression | 40-60% bandwidth savings | MEDIUM |

---

## Performance Improvement Roadmap

### Phase 1: Critical Gains (1-3 hours)
**Expected Combined Improvement: 25-35%**

```
Priority  | Item                              | Gain    | Effort | File Location
----------|-----------------------------------|---------|--------|-----------------------------------
CRITICAL  | HTTP connection pooling          | 25-35%  | 1h     | http_transport.py/go
HIGH      | gRPC channel pooling + keepalive | 20-25%  | 1.5h   | grpc_transport.py/go
MEDIUM    | Enable message compression       | 40-60%  | 0.5h   | grpc_transport.go
MEDIUM    | Fast-path cache keys             | 30-50%  | 1h     | caching.py/go
```

### Phase 2: Performance Optimization (3-6 hours)
**Expected Combined Improvement: 15-25%**

```
Priority  | Item                              | Gain    | Effort | File Location
----------|-----------------------------------|---------|--------|-----------------------------------
HIGH      | Protobuf-native gRPC streaming   | 20-30%  | 3h     | grpc_transport.go
HIGH      | Read-write lock for caching      | 40-60%  | 2-3h   | caching.py
MEDIUM    | Min-heap expiration tracking     | 60-80%  | 2h     | caching.py/go
MEDIUM    | Remove polling in batching       | 50% CPU | 1h     | batching.py
```

### Phase 3: Scale Optimization (6+ hours)
**Expected Combined Improvement: 10-15%**

```
Priority  | Item                              | Gain    | Effort | File Location
----------|-----------------------------------|---------|--------|-----------------------------------
MEDIUM    | Worker pool for parallel agents  | 40-60%  | 3-4h   | parallel.go
MEDIUM    | Message batching transport       | 30-40%  | 4-6h   | transport layers
LOW       | Response queue backpressure      | Stability| 1h    | grpc_transport.go
LOW       | Cache entry size limits          | Memory  | 2h     | caching.py/go
```

---

## Critical Issues by Area

### 1. Connection Management (CRITICAL)
**Problem**: Each transport instance creates new client/connection
**Current**: 10-50ms overhead per request
**Impact**: Sequential requests lose connection reuse benefits

**Files Affected**:
- `agenkit/adapters/python/http_transport.py:71-87`
- `agenkit-go/adapter/transport/http_transport.go:80-115`
- `agenkit/adapters/python/grpc_transport.py:73`
- `agenkit-go/adapter/transport/grpc_transport.go:75`

**Action Items**:
1. Implement HTTP client pooling (Python httpx, Go http.Client)
2. Add gRPC channel pooling with connection limits
3. Configure keep-alive: TCP/gRPC ping intervals

---

### 2. Message Serialization (HIGH)
**Problem**: Repeated JSON encode/decode in hot path
**Current**: 0.5-1ms per message, 18 instances across transports
**Impact**: 15-25% throughput reduction for streaming

**Files Affected**:
- `agenkit/adapters/python/codec.py:118-119` (cache key generation)
- `agenkit/adapters/python/grpc_transport.py:139,158,180` (JSON conversion)
- `agenkit-go/adapter/transport/grpc_transport.go:139,161` (JSON marshaling)

**Action Items**:
1. Optimize cache key generation (use incremental hashing)
2. Implement protobuf-native gRPC streaming (eliminate JSON layer)
3. Add codec benchmarks

---

### 3. Caching Lock Contention (HIGH)
**Problem**: Full lock held during cache access and agent processing
**Current**: Serializes all cache operations
**Impact**: 40-60% latency improvement possible with concurrent reads

**Files Affected**:
- `agenkit/adapters/python/middleware/caching.py:152-182`
- `agenkit-go/middleware/caching.go:311-378`

**Action Items**:
1. Implement read-write lock for concurrent reads
2. Use min-heap for O(1) expiration tracking instead of O(n) cleanup
3. Release lock before calling agent.process()

---

### 4. Network Optimization (MEDIUM)
**Problem**: No compression, no request batching
**Current**: Full payload size transmitted, extra RTTs for small requests
**Impact**: 40-60% bandwidth reduction possible

**Action Items**:
1. Enable gRPC message compression (gzip)
2. Implement message batching for high-frequency requests
3. Configure HTTP/2 for automatic multiplexing

---

## Code-Specific Recommendations

### HTTP Transport (Python)
```python
# BEFORE: New client per instance
class HTTPTransport(Transport):
    async def connect(self):
        self.client = httpx.AsyncClient(http2=True)

# AFTER: Use shared pool
_http_client = httpx.AsyncClient(
    http2=True,
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    )
)
```

### gRPC Transport (Go)
```go
// BEFORE: New channel per connect
func (t *GRPCTransport) Connect(ctx context.Context) error {
    conn, err := grpc.NewClient(target, 
        grpc.WithTransportCredentials(insecure.NewCredentials()))
    t.conn = conn
}

// AFTER: Channel pooling + keepalive
func getGRPCChannel(target string) (*grpc.ClientConn, error) {
    if conn, ok := channelPool[target]; ok {
        return conn, nil
    }
    
    conn, err := grpc.NewClient(target,
        grpc.WithTransportCredentials(insecure.NewCredentials()),
        grpc.WithKeepaliveParams(keepalive.ClientParameters{
            Time:    20 * time.Second,
            Timeout: 10 * time.Second,
        }),
    )
    channelPool[target] = conn
    return conn, nil
}
```

### Cache Locking (Python)
```python
# BEFORE: Full lock serializes everything
async with self._lock:
    if cache_key in self._cache:
        return entry.response

# AFTER: Read lock allows concurrent access
async with self._read_lock():
    if cache_key in self._cache:
        return entry.response
```

---

## Performance Testing Strategy

### 1. Establish Baselines
```bash
# Run existing benchmarks
cd /Users/scttfrdmn/src/agenkit/benchmarks
pytest test_middleware_overhead.py -v
pytest test_transport_overhead.py -v
pytest test_streaming_overhead.py -v
```

### 2. Targeted Measurements
Create micro-benchmarks for:
- Connection pool efficiency
- Cache key generation speed
- Serialization overhead
- Lock contention

### 3. End-to-End Testing
- Measure request latency with/without optimizations
- Measure throughput (requests/sec)
- Measure memory usage under load
- Measure GC pause times

---

## Risk Assessment

| Optimization | Risk | Mitigation |
|--------------|------|-----------|
| Connection pooling | Connection stale/closed | Monitor pool health, implement cleanup |
| Channel pooling | Goroutine leaks | Proper shutdown, connection limits |
| RW locks | Deadlock | Careful lock ordering, tests |
| Protobuf streaming | Breaking change | Version bump, backwards compatibility |

---

## Success Metrics

### After Phase 1
- [ ] HTTP requests: 25-35% latency reduction
- [ ] gRPC unary: 15-25% latency reduction
- [ ] gRPC streaming: 10-20% latency reduction
- [ ] Throughput: 20-30% improvement

### After Phase 2
- [ ] Cache lookup: 40-60% latency improvement (concurrent)
- [ ] Streaming: 20-30% latency reduction
- [ ] Cleanup: Near-instant (<100µs)
- [ ] CPU (idle): 50% reduction

### After Phase 3
- [ ] 100+ parallel agents: 40-60% memory reduction
- [ ] Small message throughput: 30-40% improvement
- [ ] Memory stability: No growth under load

---

## Implementation Timeline

**Week 1**: Connection pooling + compression = 25-35% gain  
**Week 2**: Caching optimization + protobuf streaming = +15-25%  
**Week 3**: Scale optimizations = +10-15%  

**Total Expected**: 40-60% end-to-end improvement

---

## File Locations & Line Numbers

### Python Critical Files
| File | Lines | Issue |
|------|-------|-------|
| http_transport.py | 71-87 | Connection pooling |
| grpc_transport.py | 73, 139-180 | Pooling + serialization |
| codec.py | 118-119 | Cache key generation |
| caching.py | 152-182 | Lock contention |
| batching.py | 177-179 | Polling overhead |

### Go Critical Files
| File | Lines | Issue |
|------|-------|-------|
| http_transport.go | 80-115 | Connection pooling |
| grpc_transport.go | 75, 139, 161 | Pooling + serialization |
| transport/transport.go | 30-60 | Response queue |
| middleware/caching.go | 311-378 | Lock contention |
| composition/parallel.go | 63-84 | Goroutine pooling |

---

## Next Steps

1. **Review & Prioritize**: Team review of recommendations
2. **Create Issues**: Track each optimization as separate issue
3. **Benchmark**: Establish baseline measurements
4. **Implement Phase 1**: Connection pooling (highest impact)
5. **Test & Measure**: Validate improvements
6. **Iterate**: Move to Phase 2 optimizations

---

**Full Report**: See `/Users/scttfrdmn/src/agenkit/PERFORMANCE_OPTIMIZATION_REVIEW.md` (1074 lines)

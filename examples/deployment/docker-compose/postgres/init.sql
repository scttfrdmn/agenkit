-- ============================================================
-- Agenkit PostgreSQL Initialization Script
-- ============================================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS agenkit;
CREATE SCHEMA IF NOT EXISTS metrics;

-- Set search path
SET search_path TO agenkit, public;

-- ============================================================
-- Agent Execution Tables
-- ============================================================

-- Agent sessions table
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type VARCHAR(50) NOT NULL,
    agent_runtime VARCHAR(20) NOT NULL,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent messages table
CREATE TABLE IF NOT EXISTS agent_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES agent_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent errors table
CREATE TABLE IF NOT EXISTS agent_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES agent_sessions(id) ON DELETE CASCADE,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Metrics Tables
-- ============================================================

-- Request metrics
CREATE TABLE IF NOT EXISTS metrics.requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type VARCHAR(50) NOT NULL,
    agent_runtime VARCHAR(20) NOT NULL,
    method VARCHAR(10),
    path VARCHAR(255),
    status_code INTEGER,
    duration_ms INTEGER,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    client_ip INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS metrics.performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10, 2) NOT NULL,
    metric_unit VARCHAR(20),
    tags JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Indexes
-- ============================================================

-- Agent sessions indexes
CREATE INDEX IF NOT EXISTS idx_sessions_agent_type ON agent_sessions(agent_type);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON agent_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON agent_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON agent_sessions(session_id);

-- Agent messages indexes
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON agent_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON agent_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_role ON agent_messages(role);

-- Agent errors indexes
CREATE INDEX IF NOT EXISTS idx_errors_session_id ON agent_errors(session_id);
CREATE INDEX IF NOT EXISTS idx_errors_created_at ON agent_errors(created_at);
CREATE INDEX IF NOT EXISTS idx_errors_error_type ON agent_errors(error_type);

-- Metrics indexes
CREATE INDEX IF NOT EXISTS idx_requests_agent_type ON metrics.requests(agent_type);
CREATE INDEX IF NOT EXISTS idx_requests_created_at ON metrics.requests(created_at);
CREATE INDEX IF NOT EXISTS idx_requests_status_code ON metrics.requests(status_code);
CREATE INDEX IF NOT EXISTS idx_performance_metric_name ON metrics.performance(metric_name);
CREATE INDEX IF NOT EXISTS idx_performance_created_at ON metrics.performance(created_at);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS idx_sessions_metadata ON agent_sessions USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_messages_metadata ON agent_messages USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_errors_metadata ON agent_errors USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_performance_tags ON metrics.performance USING GIN (tags);

-- ============================================================
-- Functions
-- ============================================================

-- Update updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
DROP TRIGGER IF EXISTS update_agent_sessions_updated_at ON agent_sessions;
CREATE TRIGGER update_agent_sessions_updated_at
    BEFORE UPDATE ON agent_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Views
-- ============================================================

-- Active sessions view
CREATE OR REPLACE VIEW active_sessions AS
SELECT
    id,
    agent_type,
    agent_runtime,
    session_id,
    started_at,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at)) as duration_seconds,
    metadata
FROM agent_sessions
WHERE status = 'active';

-- Session summary view
CREATE OR REPLACE VIEW session_summary AS
SELECT
    agent_type,
    agent_runtime,
    COUNT(*) as total_sessions,
    COUNT(*) FILTER (WHERE status = 'active') as active_sessions,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_sessions,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_sessions,
    AVG(EXTRACT(EPOCH FROM (ended_at - started_at))) as avg_duration_seconds
FROM agent_sessions
WHERE started_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY agent_type, agent_runtime;

-- Error summary view
CREATE OR REPLACE VIEW error_summary AS
SELECT
    error_type,
    COUNT(*) as error_count,
    MAX(created_at) as last_occurrence
FROM agent_errors
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
GROUP BY error_type
ORDER BY error_count DESC;

-- Request metrics view
CREATE OR REPLACE VIEW request_metrics AS
SELECT
    agent_type,
    agent_runtime,
    COUNT(*) as request_count,
    AVG(duration_ms) as avg_duration_ms,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms) as p50_duration_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99_duration_ms,
    COUNT(*) FILTER (WHERE status_code >= 500) as error_5xx_count,
    COUNT(*) FILTER (WHERE status_code >= 400 AND status_code < 500) as error_4xx_count
FROM metrics.requests
WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY agent_type, agent_runtime;

-- ============================================================
-- Grants
-- ============================================================

-- Grant permissions to agenkit user
GRANT ALL PRIVILEGES ON SCHEMA agenkit TO agenkit;
GRANT ALL PRIVILEGES ON SCHEMA metrics TO agenkit;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA agenkit TO agenkit;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA metrics TO agenkit;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA agenkit TO agenkit;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA metrics TO agenkit;

-- ============================================================
-- Initial Data
-- ============================================================

-- Insert sample configuration (optional)
-- INSERT INTO agenkit.config (key, value) VALUES ('version', '0.45.0');

-- ============================================================
-- Maintenance
-- ============================================================

-- Create cleanup function for old metrics (retention policy)
CREATE OR REPLACE FUNCTION cleanup_old_metrics()
RETURNS void AS $$
BEGIN
    -- Delete metrics older than 30 days
    DELETE FROM metrics.requests WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
    DELETE FROM metrics.performance WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';

    -- Delete completed sessions older than 90 days
    DELETE FROM agent_sessions WHERE status = 'completed' AND ended_at < CURRENT_TIMESTAMP - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Agenkit PostgreSQL initialization complete';
END $$;

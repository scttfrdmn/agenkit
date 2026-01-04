-- ============================================================
-- Agenkit D1 Database Initial Migration
-- ============================================================

-- Metrics table for performance tracking
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_type TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_metrics_agent_type ON metrics(agent_type);
CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON metrics(created_at);
CREATE INDEX IF NOT EXISTS idx_metrics_status ON metrics(status);

-- Session metadata table (for cross-DO queries)
CREATE TABLE IF NOT EXISTS session_metadata (
    session_id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    last_accessed_at TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_session_agent_type ON session_metadata(agent_type);
CREATE INDEX IF NOT EXISTS idx_session_last_accessed ON session_metadata(last_accessed_at);

-- Error tracking table
CREATE TABLE IF NOT EXISTS errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    agent_type TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_errors_session_id ON errors(session_id);
CREATE INDEX IF NOT EXISTS idx_errors_agent_type ON errors(agent_type);
CREATE INDEX IF NOT EXISTS idx_errors_created_at ON errors(created_at);

-- Request log table
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    user_agent TEXT,
    country TEXT,
    colo TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_requests_path ON requests(path);
CREATE INDEX IF NOT EXISTS idx_requests_status_code ON requests(status_code);
CREATE INDEX IF NOT EXISTS idx_requests_created_at ON requests(created_at);

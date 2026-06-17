// Health checking for agents with Kubernetes-style probes:
// - Liveness: Is the agent alive?
// - Readiness: Is the agent ready to accept traffic?
// - Startup: Has initialization completed?
// - Prometheus metrics export

const std = @import("std");
const agksync = @import("../sync_compat.zig");
const agktime = @import("../time_compat.zig");
const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;

/// Health status values.
pub const HealthStatus = enum {
    healthy,
    unhealthy,
    degraded,
    unknown,

    pub fn asString(self: HealthStatus) []const u8 {
        return switch (self) {
            .healthy => "healthy",
            .unhealthy => "unhealthy",
            .degraded => "degraded",
            .unknown => "unknown",
        };
    }
};

/// Types of health probes.
pub const ProbeType = enum {
    liveness,
    readiness,
    startup,

    pub fn asString(self: ProbeType) []const u8 {
        return switch (self) {
            .liveness => "liveness",
            .readiness => "readiness",
            .startup => "startup",
        };
    }
};

/// Result of a health check.
pub const HealthCheckResult = struct {
    status: HealthStatus,
    probe_type: ProbeType,
    message: []const u8,
    timestamp: i64,
    duration_ms: f64,
};

/// Health check configuration.
pub const HealthCheckConfig = struct {
    // Liveness probe settings
    liveness_enabled: bool,
    liveness_interval_ms: u64,
    liveness_timeout_ms: u64,
    liveness_failure_threshold: usize,

    // Readiness probe settings
    readiness_enabled: bool,
    readiness_interval_ms: u64,
    readiness_timeout_ms: u64,
    readiness_failure_threshold: usize,

    // Startup probe settings
    startup_enabled: bool,
    startup_timeout_ms: u64,
    startup_failure_threshold: usize,

    pub fn default() HealthCheckConfig {
        return .{
            .liveness_enabled = true,
            .liveness_interval_ms = 10000,
            .liveness_timeout_ms = 5000,
            .liveness_failure_threshold = 3,
            .readiness_enabled = true,
            .readiness_interval_ms = 5000,
            .readiness_timeout_ms = 3000,
            .readiness_failure_threshold = 2,
            .startup_enabled = true,
            .startup_timeout_ms = 30000,
            .startup_failure_threshold = 30,
        };
    }
};

/// Health check metrics.
pub const HealthMetrics = struct {
    allocator: std.mem.Allocator,
    total_checks: std.AutoHashMap(ProbeType, u64),
    successful_checks: std.AutoHashMap(ProbeType, u64),
    failed_checks: std.AutoHashMap(ProbeType, u64),
    last_check_time: std.AutoHashMap(ProbeType, i64),
    last_check_duration: std.AutoHashMap(ProbeType, f64),
    consecutive_failures: std.AutoHashMap(ProbeType, usize),
    uptime_start: i64,

    pub fn init(allocator: std.mem.Allocator) HealthMetrics {
        return .{
            .allocator = allocator,
            .total_checks = std.AutoHashMap(ProbeType, u64).init(allocator),
            .successful_checks = std.AutoHashMap(ProbeType, u64).init(allocator),
            .failed_checks = std.AutoHashMap(ProbeType, u64).init(allocator),
            .last_check_time = std.AutoHashMap(ProbeType, i64).init(allocator),
            .last_check_duration = std.AutoHashMap(ProbeType, f64).init(allocator),
            .consecutive_failures = std.AutoHashMap(ProbeType, usize).init(allocator),
            .uptime_start = agktime.milliTimestamp(),
        };
    }

    pub fn deinit(self: *HealthMetrics) void {
        self.total_checks.deinit();
        self.successful_checks.deinit();
        self.failed_checks.deinit();
        self.last_check_time.deinit();
        self.last_check_duration.deinit();
        self.consecutive_failures.deinit();
    }

    pub fn getUptime(self: *const HealthMetrics) f64 {
        const now = agktime.milliTimestamp();
        return @as(f64, @floatFromInt(now - self.uptime_start)) / 1000.0;
    }
};

/// Health checker monitors agent health.
pub const HealthChecker = struct {
    allocator: std.mem.Allocator,
    agent: Agent,
    config: HealthCheckConfig,
    metrics: HealthMetrics,
    is_alive: bool,
    is_ready: bool,
    startup_complete: bool,
    mutex: agksync.Mutex,

    pub fn init(
        allocator: std.mem.Allocator,
        agent: Agent,
        config: HealthCheckConfig,
    ) HealthChecker {
        return .{
            .allocator = allocator,
            .agent = agent,
            .config = config,
            .metrics = HealthMetrics.init(allocator),
            .is_alive = true,
            .is_ready = false,
            .startup_complete = false,
            .mutex = agksync.Mutex{},
        };
    }

    pub fn deinit(self: *HealthChecker) void {
        self.metrics.deinit();
    }

    pub fn isHealthy(self: *HealthChecker) bool {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.is_alive and self.is_ready;
    }

    pub fn checkLiveness(self: *HealthChecker) !HealthCheckResult {
        const start_time = agktime.milliTimestamp();
        const probe_type = ProbeType.liveness;

        try self.trackCheckStarted(probe_type);

        // Basic liveness: Can we call methods?
        _ = self.agent.name();
        const caps = try self.agent.capabilities(self.allocator);
        self.allocator.free(caps);

        // Success
        const duration = @as(f64, @floatFromInt(agktime.milliTimestamp() - start_time));
        try self.trackCheckSuccess(probe_type, duration);

        return HealthCheckResult{
            .status = .healthy,
            .probe_type = probe_type,
            .message = "Agent process is alive",
            .timestamp = agktime.milliTimestamp(),
            .duration_ms = duration,
        };
    }

    pub fn checkReadiness(self: *HealthChecker) !HealthCheckResult {
        const start_time = agktime.milliTimestamp();
        const probe_type = ProbeType.readiness;

        try self.trackCheckStarted(probe_type);

        // Check if startup completed
        if (self.config.startup_enabled and !self.startup_complete) {
            const duration = @as(f64, @floatFromInt(agktime.milliTimestamp() - start_time));
            try self.trackCheckFailure(probe_type, duration);
            return HealthCheckResult{
                .status = .unhealthy,
                .probe_type = probe_type,
                .message = "Startup not complete",
                .timestamp = agktime.milliTimestamp(),
                .duration_ms = duration,
            };
        }

        // Test with a simple request
        const test_msg = Message{
            .role = "system",
            .content = "readiness_check",
            .metadata = null,
        };

        const result = self.agent.process(test_msg);
        const duration = @as(f64, @floatFromInt(agktime.milliTimestamp() - start_time));

        if (result) |response| {
            if (response.content.len == 0) {
                try self.trackCheckFailure(probe_type, duration);
                return HealthCheckResult{
                    .status = .unhealthy,
                    .probe_type = probe_type,
                    .message = "Readiness check failed: empty response",
                    .timestamp = agktime.milliTimestamp(),
                    .duration_ms = duration,
                };
            }

            // Success
            try self.trackCheckSuccess(probe_type, duration);
            return HealthCheckResult{
                .status = .healthy,
                .probe_type = probe_type,
                .message = "Agent is ready to handle requests",
                .timestamp = agktime.milliTimestamp(),
                .duration_ms = duration,
            };
        } else |_| {
            try self.trackCheckFailure(probe_type, duration);
            return HealthCheckResult{
                .status = .unhealthy,
                .probe_type = probe_type,
                .message = "Readiness check failed",
                .timestamp = agktime.milliTimestamp(),
                .duration_ms = duration,
            };
        }
    }

    pub fn checkStartup(self: *HealthChecker) !HealthCheckResult {
        const start_time = agktime.milliTimestamp();
        const probe_type = ProbeType.startup;

        try self.trackCheckStarted(probe_type);

        // Perform readiness check as startup test
        const readiness_result = try self.checkReadiness();

        if (readiness_result.status == .healthy) {
            self.mutex.lock();
            self.startup_complete = true;
            self.mutex.unlock();

            const duration = @as(f64, @floatFromInt(agktime.milliTimestamp() - start_time));
            try self.trackCheckSuccess(probe_type, duration);

            return HealthCheckResult{
                .status = .healthy,
                .probe_type = probe_type,
                .message = "Startup complete",
                .timestamp = agktime.milliTimestamp(),
                .duration_ms = duration,
            };
        }

        const duration = @as(f64, @floatFromInt(agktime.milliTimestamp() - start_time));
        try self.trackCheckFailure(probe_type, duration);

        return HealthCheckResult{
            .status = .unhealthy,
            .probe_type = probe_type,
            .message = "Startup checks not passing yet",
            .timestamp = agktime.milliTimestamp(),
            .duration_ms = duration,
        };
    }

    fn trackCheckStarted(self: *HealthChecker, probe_type: ProbeType) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        const entry = try self.metrics.total_checks.getOrPut(probe_type);
        if (entry.found_existing) {
            entry.value_ptr.* += 1;
        } else {
            entry.value_ptr.* = 1;
        }
    }

    fn trackCheckSuccess(self: *HealthChecker, probe_type: ProbeType, duration_ms: f64) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        const entry = try self.metrics.successful_checks.getOrPut(probe_type);
        if (entry.found_existing) {
            entry.value_ptr.* += 1;
        } else {
            entry.value_ptr.* = 1;
        }

        try self.metrics.last_check_time.put(probe_type, agktime.milliTimestamp());
        try self.metrics.last_check_duration.put(probe_type, duration_ms);
        try self.metrics.consecutive_failures.put(probe_type, 0);
    }

    fn trackCheckFailure(self: *HealthChecker, probe_type: ProbeType, duration_ms: f64) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        const entry = try self.metrics.failed_checks.getOrPut(probe_type);
        if (entry.found_existing) {
            entry.value_ptr.* += 1;
        } else {
            entry.value_ptr.* = 1;
        }

        try self.metrics.last_check_time.put(probe_type, agktime.milliTimestamp());
        try self.metrics.last_check_duration.put(probe_type, duration_ms);

        const failures_entry = try self.metrics.consecutive_failures.getOrPut(probe_type);
        if (failures_entry.found_existing) {
            failures_entry.value_ptr.* += 1;
        } else {
            failures_entry.value_ptr.* = 1;
        }
    }

    pub fn exportPrometheusMetrics(self: *HealthChecker, allocator: std.mem.Allocator) ![]const u8 {
        self.mutex.lock();
        defer self.mutex.unlock();

        var lines = std.ArrayList([]const u8).empty;
        defer lines.deinit();

        // Total checks
        try lines.append("# HELP agenkit_health_checks_total Total number of health checks performed");
        try lines.append("# TYPE agenkit_health_checks_total counter");
        var iter = self.metrics.total_checks.iterator();
        while (iter.next()) |entry| {
            const line = try std.fmt.allocPrint(
                allocator,
                "agenkit_health_checks_total{{probe=\"{s}\"}} {}",
                .{ entry.key_ptr.asString(), entry.value_ptr.* },
            );
            try lines.append(line);
        }

        // Failed checks
        try lines.append("");
        try lines.append("# HELP agenkit_health_check_failures_total Total number of failed health checks");
        try lines.append("# TYPE agenkit_health_check_failures_total counter");
        var failed_iter = self.metrics.failed_checks.iterator();
        while (failed_iter.next()) |entry| {
            const line = try std.fmt.allocPrint(
                allocator,
                "agenkit_health_check_failures_total{{probe=\"{s}\"}} {}",
                .{ entry.key_ptr.asString(), entry.value_ptr.* },
            );
            try lines.append(line);
        }

        // Duration
        try lines.append("");
        try lines.append("# HELP agenkit_health_check_duration_ms Duration of last health check in milliseconds");
        try lines.append("# TYPE agenkit_health_check_duration_ms gauge");
        var duration_iter = self.metrics.last_check_duration.iterator();
        while (duration_iter.next()) |entry| {
            const line = try std.fmt.allocPrint(
                allocator,
                "agenkit_health_check_duration_ms{{probe=\"{s}\"}} {d:.2}",
                .{ entry.key_ptr.asString(), entry.value_ptr.* },
            );
            try lines.append(line);
        }

        // Uptime
        try lines.append("");
        try lines.append("# HELP agenkit_agent_uptime_seconds Uptime in seconds");
        try lines.append("# TYPE agenkit_agent_uptime_seconds gauge");
        const uptime_line = try std.fmt.allocPrint(
            allocator,
            "agenkit_agent_uptime_seconds {d:.2}",
            .{self.metrics.getUptime()},
        );
        try lines.append(uptime_line);

        // Health status
        try lines.append("");
        try lines.append("# HELP agenkit_agent_healthy Agent health status (1=healthy, 0=unhealthy)");
        try lines.append("# TYPE agenkit_agent_healthy gauge");
        const health_value: u8 = if (self.is_alive and self.is_ready) 1 else 0;
        const health_line = try std.fmt.allocPrint(
            allocator,
            "agenkit_agent_healthy {}",
            .{health_value},
        );
        try lines.append(health_line);

        // Join all lines
        return std.mem.join(allocator, "\n", lines.items);
    }

    pub fn getMetrics(self: *HealthChecker) HealthMetrics {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.metrics;
    }
};

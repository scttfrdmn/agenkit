// Load balancing for distributing requests across multiple agents with:
// - Multiple strategies (round-robin, least-connections, weighted, random)
// - Automatic health checking
// - Failover support
// - Real-time backend statistics
// - Thread-safe for concurrent requests

const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;

/// Load balancing strategy.
pub const LoadBalancingStrategy = enum {
    round_robin,
    least_connections,
    weighted_round_robin,
    random,
};

/// Backend agent with metadata.
pub const AgentBackend = struct {
    agent: Agent,
    weight: usize,
    healthy: bool,
    active_connections: usize,
    total_requests: u64,
    total_failures: u64,
    last_health_check: i64,
    consecutive_failures: usize,

    pub fn init(agent: Agent, weight: usize) AgentBackend {
        return .{
            .agent = agent,
            .weight = weight,
            .healthy = true,
            .active_connections = 0,
            .total_requests = 0,
            .total_failures = 0,
            .last_health_check = std.time.milliTimestamp(),
            .consecutive_failures = 0,
        };
    }
};

/// Load balancer configuration.
pub const LoadBalancerConfig = struct {
    strategy: LoadBalancingStrategy,
    health_check_interval_ms: u64,
    health_check_timeout_ms: u64,
    failure_threshold: usize,
    success_threshold: usize,
    enable_failover: bool,

    pub fn default() LoadBalancerConfig {
        return .{
            .strategy = .round_robin,
            .health_check_interval_ms = 30000,
            .health_check_timeout_ms = 5000,
            .failure_threshold = 3,
            .success_threshold = 2,
            .enable_failover = true,
        };
    }
};

/// Load balancer performance metrics.
pub const LoadBalancerMetrics = struct {
    total_requests: u64,
    successful_requests: u64,
    failed_requests: u64,
    failover_attempts: u64,
    backend_health_changes: std.StringHashMap(u64),

    pub fn init(allocator: std.mem.Allocator) LoadBalancerMetrics {
        return .{
            .total_requests = 0,
            .successful_requests = 0,
            .failed_requests = 0,
            .failover_attempts = 0,
            .backend_health_changes = std.StringHashMap(u64).init(allocator),
        };
    }

    pub fn deinit(self: *LoadBalancerMetrics) void {
        self.backend_health_changes.deinit();
    }
};

/// Backend statistics.
pub const BackendStats = struct {
    name: []const u8,
    healthy: bool,
    weight: usize,
    active_connections: usize,
    total_requests: u64,
    total_failures: u64,
};

/// Load balancer distributes requests across multiple agents.
pub const LoadBalancer = struct {
    allocator: std.mem.Allocator,
    backends: []AgentBackend,
    config: LoadBalancerConfig,
    metrics: LoadBalancerMetrics,
    current_index: usize,
    mutex: std.Thread.Mutex,

    pub fn init(
        allocator: std.mem.Allocator,
        agents: []Agent,
        config: LoadBalancerConfig,
        weights: ?[]const usize,
    ) !LoadBalancer {
        if (agents.len == 0) {
            return error.NoAgents;
        }

        // Default weights to 1 if not provided
        const final_weights = if (weights) |w| blk: {
            if (w.len != agents.len) {
                return error.WeightsMismatch;
            }
            break :blk w;
        } else blk: {
            const default_weights = try allocator.alloc(usize, agents.len);
            @memset(default_weights, 1);
            break :blk default_weights;
        };

        // Create backends
        const backends = try allocator.alloc(AgentBackend, agents.len);
        for (agents, final_weights, 0..) |agent, weight, i| {
            backends[i] = AgentBackend.init(agent, weight);
        }

        // Clean up default weights if we allocated them
        if (weights == null) {
            allocator.free(final_weights);
        }

        return LoadBalancer{
            .allocator = allocator,
            .backends = backends,
            .config = config,
            .metrics = LoadBalancerMetrics.init(allocator),
            .current_index = 0,
            .mutex = std.Thread.Mutex{},
        };
    }

    pub fn deinit(self: *LoadBalancer) void {
        self.allocator.free(self.backends);
        self.metrics.deinit();
    }

    pub fn name(self: *const LoadBalancer) []const u8 {
        _ = self;
        return "LoadBalancer";
    }

    pub fn capabilities(self: *const LoadBalancer, allocator: std.mem.Allocator) ![][]const u8 {
        var caps_map = std.StringHashMap(void).init(allocator);
        defer caps_map.deinit();

        for (self.backends) |backend| {
            const backend_caps = try backend.agent.capabilities(allocator);
            defer allocator.free(backend_caps);

            for (backend_caps) |cap| {
                try caps_map.put(cap, {});
            }
        }

        const result = try allocator.alloc([]const u8, caps_map.count());
        var iter = caps_map.keyIterator();
        var i: usize = 0;
        while (iter.next()) |key| : (i += 1) {
            result[i] = key.*;
        }

        return result;
    }

    pub fn getBackendStats(self: *LoadBalancer, allocator: std.mem.Allocator) ![]BackendStats {
        self.mutex.lock();
        defer self.mutex.unlock();

        const stats = try allocator.alloc(BackendStats, self.backends.len);
        for (self.backends, 0..) |backend, i| {
            stats[i] = BackendStats{
                .name = backend.agent.name(),
                .healthy = backend.healthy,
                .weight = backend.weight,
                .active_connections = backend.active_connections,
                .total_requests = backend.total_requests,
                .total_failures = backend.total_failures,
            };
        }

        return stats;
    }

    fn selectBackend(self: *LoadBalancer) !usize {
        self.mutex.lock();
        defer self.mutex.unlock();

        var healthy_indices = std.ArrayList(usize).init(self.allocator);
        defer healthy_indices.deinit();

        for (self.backends, 0..) |backend, i| {
            if (backend.healthy) {
                try healthy_indices.append(i);
            }
        }

        if (healthy_indices.items.len == 0) {
            return error.AllBackendsUnhealthy;
        }

        return switch (self.config.strategy) {
            .round_robin => self.selectRoundRobin(),
            .least_connections => self.selectLeastConnections(healthy_indices.items),
            .weighted_round_robin => self.selectWeightedRoundRobin(healthy_indices.items),
            .random => blk: {
                var prng = std.rand.DefaultPrng.init(@intCast(std.time.milliTimestamp()));
                const rand = prng.random();
                const index = rand.intRangeAtMost(usize, 0, healthy_indices.items.len - 1);
                break :blk healthy_indices.items[index];
            },
        };
    }

    fn selectRoundRobin(self: *LoadBalancer) usize {
        // Find next healthy backend in rotation
        for (0..self.backends.len) |_| {
            self.current_index = (self.current_index + 1) % self.backends.len;
            if (self.backends[self.current_index].healthy) {
                return self.current_index;
            }
        }

        // Fallback to first healthy
        for (self.backends, 0..) |backend, i| {
            if (backend.healthy) {
                return i;
            }
        }

        return 0; // Should never reach here due to check in selectBackend
    }

    fn selectLeastConnections(self: *LoadBalancer, healthy_indices: []const usize) usize {
        var selected = healthy_indices[0];
        var min_connections = self.backends[selected].active_connections;

        for (healthy_indices[1..]) |index| {
            const connections = self.backends[index].active_connections;
            if (connections < min_connections) {
                min_connections = connections;
                selected = index;
            }
        }

        return selected;
    }

    fn selectWeightedRoundRobin(self: *LoadBalancer, healthy_indices: []const usize) !usize {
        // Build weighted list
        var weighted = std.ArrayList(usize).init(self.allocator);
        defer weighted.deinit();

        for (healthy_indices) |index| {
            for (0..self.backends[index].weight) |_| {
                try weighted.append(index);
            }
        }

        if (weighted.items.len == 0) {
            return healthy_indices[0];
        }

        self.current_index = (self.current_index + 1) % weighted.items.len;
        return weighted.items[self.current_index];
    }

    fn trackHealthChange(self: *LoadBalancer, agent_name: []const u8, change_type: []const u8) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        const key = try std.fmt.allocPrint(
            self.allocator,
            "{s}:{s}",
            .{ agent_name, change_type },
        );
        defer self.allocator.free(key);

        const entry = try self.metrics.backend_health_changes.getOrPut(key);
        if (entry.found_existing) {
            entry.value_ptr.* += 1;
        } else {
            entry.value_ptr.* = 1;
        }
    }

    pub fn process(self: *LoadBalancer, message: Message) !Message {
        self.mutex.lock();
        self.metrics.total_requests += 1;
        self.mutex.unlock();

        var attempted = std.StringHashMap(void).init(self.allocator);
        defer attempted.deinit();

        while (true) {
            const backend_index = try self.selectBackend();

            const backend_name = blk: {
                self.mutex.lock();
                defer self.mutex.unlock();
                break :blk self.backends[backend_index].agent.name();
            };

            // Avoid retrying same backend
            if (attempted.contains(backend_name)) {
                self.mutex.lock();
                const backends_len = self.backends.len;
                self.mutex.unlock();

                if (!self.config.enable_failover or attempted.count() >= backends_len) {
                    return error.AllBackendsAttempted;
                }
                continue;
            }

            try attempted.put(backend_name, {});

            // Track request
            {
                self.mutex.lock();
                self.backends[backend_index].active_connections += 1;
                self.backends[backend_index].total_requests += 1;
                self.mutex.unlock();
            }

            // Process message
            const result = blk: {
                self.mutex.lock();
                const agent = self.backends[backend_index].agent;
                self.mutex.unlock();
                break :blk agent.process(message);
            };

            // Decrement active connections
            {
                self.mutex.lock();
                self.backends[backend_index].active_connections -= 1;
                self.mutex.unlock();
            }

            if (result) |response| {
                // Success
                self.mutex.lock();
                self.metrics.successful_requests += 1;
                self.mutex.unlock();
                return response;
            } else |err| {
                // Failure
                {
                    self.mutex.lock();
                    self.backends[backend_index].total_failures += 1;
                    self.metrics.failed_requests += 1;
                    self.mutex.unlock();
                }

                // Check if should mark unhealthy
                {
                    self.mutex.lock();
                    if (self.backends[backend_index].healthy and
                        self.backends[backend_index].total_failures >= self.config.failure_threshold)
                    {
                        self.backends[backend_index].healthy = false;
                        self.mutex.unlock();
                        try self.trackHealthChange(backend_name, "unhealthy");
                    } else {
                        self.mutex.unlock();
                    }
                }

                // Try failover if enabled
                {
                    self.mutex.lock();
                    const backends_len = self.backends.len;
                    self.mutex.unlock();

                    if (self.config.enable_failover and attempted.count() < backends_len) {
                        self.mutex.lock();
                        self.metrics.failover_attempts += 1;
                        self.mutex.unlock();
                        continue;
                    }
                }

                // No more failover
                return err;
            }
        }
    }

    pub fn getMetrics(self: *LoadBalancer) LoadBalancerMetrics {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.metrics;
    }
};

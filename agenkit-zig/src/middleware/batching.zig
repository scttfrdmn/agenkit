/// Batching middleware for combining multiple requests
///
/// This middleware collects multiple concurrent requests and processes them as a batch,
/// improving throughput at the cost of added latency.
///
/// Use cases:
/// - LLM batch processing (reduce API costs via batch endpoints)
/// - Database bulk operations (reduce round trips)
/// - High-throughput data processing (maximize resource utilization)
///
/// Trade-offs:
/// - Latency vs throughput: Adds wait time but improves throughput
/// - Memory usage: Buffers requests in queue
/// - Complexity: Handles partial failures and request/response mapping
///
/// Example:
/// ```zig
/// const config = BatchingConfig{
///     .max_batch_size = 10,
///     .max_wait_time_ms = 100,
///     .max_queue_size = 1000,
/// };
///
/// var batching_agent = try BatchingDecorator.init(allocator, base_agent, config);
/// defer batching_agent.deinit();
///
/// // Start background processor
/// try batching_agent.start();
/// defer batching_agent.stop();
///
/// const result = try batching_agent.agent().process(message);
/// ```
const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const AgentError = @import("../agent.zig").AgentError;
const Result = @import("../agent.zig").Result;
const Message = @import("../message.zig").Message;
const IntrospectionResult = @import("../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;

/// Configuration for batching behavior
pub const BatchingConfig = struct {
    /// Process when we have this many requests
    /// Default: 10
    max_batch_size: u32 = 10,

    /// Process after this many milliseconds since first request
    /// Default: 100ms
    max_wait_time_ms: u64 = 100,

    /// Maximum queue size (backpressure limit)
    /// Default: 1000
    max_queue_size: u32 = 1000,

    /// Validate configuration
    pub fn validate(self: BatchingConfig) !void {
        if (self.max_batch_size < 1) {
            return error.InvalidConfig;
        }
        if (self.max_wait_time_ms == 0) {
            return error.InvalidConfig;
        }
        if (self.max_queue_size < self.max_batch_size) {
            return error.InvalidConfig;
        }
    }
};

/// Metrics tracked by batching middleware
pub const BatchingMetrics = struct {
    /// Total number of requests
    total_requests: u64 = 0,

    /// Total number of batches processed
    total_batches: u64 = 0,

    /// Number of successful batches (all requests succeeded)
    successful_batches: u64 = 0,

    /// Number of failed batches (all requests failed)
    failed_batches: u64 = 0,

    /// Number of partial batches (some failures)
    partial_batches: u64 = 0,

    /// Total wait time in milliseconds
    total_wait_time_ms: u64 = 0,

    /// Minimum batch size observed
    min_batch_size: ?u32 = null,

    /// Maximum batch size observed
    max_batch_size: ?u32 = null,

    /// Average batch size
    pub fn avgBatchSize(self: *const BatchingMetrics) ?f64 {
        if (self.total_batches == 0) return null;
        return @as(f64, @floatFromInt(self.total_requests)) / @as(f64, @floatFromInt(self.total_batches));
    }

    /// Average wait time per request (milliseconds)
    pub fn avgWaitTime(self: *const BatchingMetrics) ?f64 {
        if (self.total_requests == 0) return null;
        return @as(f64, @floatFromInt(self.total_wait_time_ms)) / @as(f64, @floatFromInt(self.total_requests));
    }

    /// Create a snapshot of metrics
    pub fn snapshot(self: *const BatchingMetrics) BatchingMetrics {
        return BatchingMetrics{
            .total_requests = self.total_requests,
            .total_batches = self.total_batches,
            .successful_batches = self.successful_batches,
            .failed_batches = self.failed_batches,
            .partial_batches = self.partial_batches,
            .total_wait_time_ms = self.total_wait_time_ms,
            .min_batch_size = self.min_batch_size,
            .max_batch_size = self.max_batch_size,
        };
    }
};

/// Batch request with result signaling
const BatchRequest = struct {
    message: Message,
    enqueued_at_ms: i64,
    result: ?Result,
    error_value: ?AgentError,
    completed: std.Thread.Condition,

    fn init(message: Message) BatchRequest {
        return BatchRequest{
            .message = message,
            .enqueued_at_ms = std.time.milliTimestamp(),
            .result = null,
            .error_value = null,
            .completed = std.Thread.Condition{},
        };
    }
};

/// Batching decorator - wraps an agent with batching
pub const BatchingDecorator = struct {
    allocator: Allocator,
    inner_agent: Agent,
    config: BatchingConfig,
    metrics_data: BatchingMetrics,
    queue: std.ArrayList(*BatchRequest),
    queue_mutex: std.Thread.Mutex,
    queue_condition: std.Thread.Condition,
    processor_thread: ?std.Thread,
    shutdown: std.atomic.Value(bool),
    request_mutex: std.Thread.Mutex, // For coordinating individual requests

    pub fn init(allocator: Allocator, inner_agent: Agent, config: BatchingConfig) !*BatchingDecorator {
        // Validate configuration
        try config.validate();

        const self = try allocator.create(BatchingDecorator);
        self.* = BatchingDecorator{
            .allocator = allocator,
            .inner_agent = inner_agent,
            .config = config,
            .metrics_data = BatchingMetrics{},
            .queue = std.ArrayList(*BatchRequest).init(allocator),
            .queue_mutex = std.Thread.Mutex{},
            .queue_condition = std.Thread.Condition{},
            .processor_thread = null,
            .shutdown = std.atomic.Value(bool).init(false),
            .request_mutex = std.Thread.Mutex{},
        };
        return self;
    }

    pub fn deinit(self: *BatchingDecorator) void {
        self.queue.deinit();
    }

    /// Start background batch processor
    pub fn start(self: *BatchingDecorator) !void {
        if (self.processor_thread != null) return;
        self.processor_thread = try std.Thread.spawn(.{}, batchProcessor, .{self});
    }

    /// Stop background batch processor
    pub fn stop(self: *BatchingDecorator) void {
        self.shutdown.store(true, .release);

        // Signal condition to wake up processor
        self.queue_mutex.lock();
        self.queue_condition.signal();
        self.queue_mutex.unlock();

        if (self.processor_thread) |thread| {
            thread.join();
            self.processor_thread = null;
        }
    }

    pub fn agent(self: *BatchingDecorator) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    /// Get current metrics (thread-safe)
    pub fn metrics(self: *BatchingDecorator) BatchingMetrics {
        self.queue_mutex.lock();
        defer self.queue_mutex.unlock();
        return self.metrics_data.snapshot();
    }

    /// Background thread that processes batches
    fn batchProcessor(self: *BatchingDecorator) void {
        while (!self.shutdown.load(.acquire)) {
            self.collectAndProcessBatch() catch |err| {
                std.debug.print("Batch processor error: {}\n", .{err});
            };
        }
    }

    /// Collect a batch and process it
    fn collectAndProcessBatch(self: *BatchingDecorator) !void {
        var batch = std.ArrayList(*BatchRequest).init(self.allocator);
        defer batch.deinit();

        // Wait for first request
        self.queue_mutex.lock();

        while (self.queue.items.len == 0 and !self.shutdown.load(.acquire)) {
            self.queue_condition.wait(&self.queue_mutex);
        }

        if (self.shutdown.load(.acquire)) {
            self.queue_mutex.unlock();
            return;
        }

        // Get first request
        if (self.queue.items.len > 0) {
            const first_req = self.queue.orderedRemove(0);
            try batch.append(first_req);
        }

        const deadline_ms = std.time.milliTimestamp() + @as(i64, @intCast(self.config.max_wait_time_ms));

        // Collect more requests until batch full or timeout
        while (batch.items.len < self.config.max_batch_size) {
            const now_ms = std.time.milliTimestamp();
            if (now_ms >= deadline_ms) break;

            // Check if more requests available
            if (self.queue.items.len > 0) {
                const req = self.queue.orderedRemove(0);
                try batch.append(req);
            } else {
                // Wait for more requests with timeout
                const remaining_ms = @as(u64, @intCast(deadline_ms - now_ms));
                self.queue_mutex.unlock();
                std.time.sleep(remaining_ms * std.time.ns_per_ms);
                self.queue_mutex.lock();

                // Check again after sleep
                if (self.queue.items.len > 0) {
                    const req = self.queue.orderedRemove(0);
                    try batch.append(req);
                } else {
                    break;
                }
            }
        }

        self.queue_mutex.unlock();

        // Process the batch
        if (batch.items.len > 0) {
            self.processBatch(batch.items);
        }
    }

    /// Process a batch of requests
    fn processBatch(self: *BatchingDecorator, batch: []*BatchRequest) void {
        const batch_size = @as(u32, @intCast(batch.len));

        // Update metrics
        self.queue_mutex.lock();
        self.metrics_data.total_batches += 1;
        self.metrics_data.total_requests += batch_size;

        // Update batch size metrics
        if (self.metrics_data.min_batch_size == null or batch_size < self.metrics_data.min_batch_size.?) {
            self.metrics_data.min_batch_size = batch_size;
        }
        if (self.metrics_data.max_batch_size == null or batch_size > self.metrics_data.max_batch_size.?) {
            self.metrics_data.max_batch_size = batch_size;
        }

        // Calculate wait times
        const now_ms = std.time.milliTimestamp();
        for (batch) |req| {
            const wait_time_ms = @as(u64, @intCast(now_ms - req.enqueued_at_ms));
            self.metrics_data.total_wait_time_ms += wait_time_ms;
        }
        self.queue_mutex.unlock();

        // Process each request in the batch
        var success_count: u32 = 0;
        var failure_count: u32 = 0;

        for (batch) |req| {
            // Process request
            const result = self.inner_agent.process(req.message);

            self.request_mutex.lock();
            if (result) |res| {
                req.result = res;
                req.error_value = null;
                success_count += 1;
            } else |err| {
                req.result = null;
                req.error_value = err;
                failure_count += 1;
            }

            // Signal completion
            req.completed.signal();
            self.request_mutex.unlock();
        }

        // Update batch outcome metrics
        self.queue_mutex.lock();
        if (failure_count == 0) {
            self.metrics_data.successful_batches += 1;
        } else if (success_count == 0) {
            self.metrics_data.failed_batches += 1;
        } else {
            self.metrics_data.partial_batches += 1;
        }
        self.queue_mutex.unlock();
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *BatchingDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.name();
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        const self: *BatchingDecorator = @ptrCast(@alignCast(ptr));
        return self.inner_agent.capabilities(allocator);
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *BatchingDecorator = @ptrCast(@alignCast(ptr));

        // Create batch request
        const req = BatchRequest.init(message);

        // Add to queue
        self.queue_mutex.lock();

        // Check queue size (backpressure)
        if (self.queue.items.len >= self.config.max_queue_size) {
            self.queue_mutex.unlock();
            return AgentError.Cancelled; // Queue full
        }

        // Allocate and add request
        const req_ptr = self.allocator.create(BatchRequest) catch {
            self.queue_mutex.unlock();
            return AgentError.ProcessingFailed;
        };
        req_ptr.* = req;

        self.queue.append(req_ptr) catch {
            self.allocator.destroy(req_ptr);
            self.queue_mutex.unlock();
            return AgentError.ProcessingFailed;
        };

        // Signal batch processor
        self.queue_condition.signal();
        self.queue_mutex.unlock();

        // Wait for result
        self.request_mutex.lock();
        while (req_ptr.result == null and req_ptr.error_value == null) {
            req_ptr.completed.wait(&self.request_mutex);
        }

        const result = req_ptr.result;
        const err = req_ptr.error_value;
        self.request_mutex.unlock();

        // Cleanup
        self.allocator.destroy(req_ptr);

        // Return result
        if (err) |e| {
            return e;
        }
        return result.?;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *BatchingDecorator = @ptrCast(@alignCast(ptr));

        // Get introspection from inner agent
        const inner_result = try self.inner_agent.introspect(allocator);

        // Add batching metrics to metadata
        const metrics_snapshot = self.metrics();

        var metadata = std.StringHashMap([]const u8).init(allocator);
        errdefer metadata.deinit();

        // Add metrics as metadata
        try metadata.put("total_requests", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.total_requests}));
        try metadata.put("total_batches", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.total_batches}));
        try metadata.put("successful_batches", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.successful_batches}));
        try metadata.put("failed_batches", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.failed_batches}));
        try metadata.put("partial_batches", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.partial_batches}));
        try metadata.put("total_wait_time_ms", try std.fmt.allocPrint(allocator, "{d}", .{metrics_snapshot.total_wait_time_ms}));

        if (metrics_snapshot.min_batch_size) |min| {
            try metadata.put("min_batch_size", try std.fmt.allocPrint(allocator, "{d}", .{min}));
        }
        if (metrics_snapshot.max_batch_size) |max| {
            try metadata.put("max_batch_size", try std.fmt.allocPrint(allocator, "{d}", .{max}));
        }
        if (metrics_snapshot.avgBatchSize()) |avg| {
            try metadata.put("avg_batch_size", try std.fmt.allocPrint(allocator, "{d:.2}", .{avg}));
        }
        if (metrics_snapshot.avgWaitTime()) |avg| {
            try metadata.put("avg_wait_time_ms", try std.fmt.allocPrint(allocator, "{d:.2}", .{avg}));
        }

        // Add configuration
        try metadata.put("max_batch_size", try std.fmt.allocPrint(allocator, "{d}", .{self.config.max_batch_size}));
        try metadata.put("max_wait_time_ms", try std.fmt.allocPrint(allocator, "{d}", .{self.config.max_wait_time_ms}));
        try metadata.put("max_queue_size", try std.fmt.allocPrint(allocator, "{d}", .{self.config.max_queue_size}));

        // Merge with inner metadata
        var inner_iter = inner_result.metadata.iterator();
        while (inner_iter.next()) |entry| {
            if (!std.mem.startsWith(u8, entry.key_ptr.*, "batch_")) {
                try metadata.put(entry.key_ptr.*, entry.value_ptr.*);
            }
        }

        return IntrospectionResult{
            .agent_name = inner_result.agent_name,
            .capabilities = inner_result.capabilities,
            .metadata = metadata,
            .memory = inner_result.memory,
        };
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *BatchingDecorator = @ptrCast(@alignCast(ptr));
        self.stop();
        self.deinit();
        self.allocator.destroy(self);
    }
};

// Tests
const testing = std.testing;

test "BatchingConfig validation" {
    var config = BatchingConfig{};
    try config.validate();

    // Invalid: max_batch_size < 1
    config.max_batch_size = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.max_batch_size = 10;

    // Invalid: max_wait_time_ms == 0
    config.max_wait_time_ms = 0;
    try testing.expectError(error.InvalidConfig, config.validate());
    config.max_wait_time_ms = 100;

    // Invalid: max_queue_size < max_batch_size
    config.max_queue_size = 5;
    config.max_batch_size = 10;
    try testing.expectError(error.InvalidConfig, config.validate());
}

test "BatchingMetrics calculations" {
    var metrics = BatchingMetrics{
        .total_requests = 100,
        .total_batches = 10,
        .total_wait_time_ms = 5000,
    };

    // Average batch size
    const avg_batch = metrics.avgBatchSize().?;
    try testing.expectApproxEqRel(@as(f64, 10.0), avg_batch, 0.01);

    // Average wait time
    const avg_wait = metrics.avgWaitTime().?;
    try testing.expectApproxEqRel(@as(f64, 50.0), avg_wait, 0.01);
}

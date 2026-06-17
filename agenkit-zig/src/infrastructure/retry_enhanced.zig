// Enhanced retry logic with:
// - Multiple jitter types (Full, Equal, Decorrelated)
// - Per-error-type retry strategies
// - Budget awareness (cost and count limits)
// - Backpressure detection
// - Detailed metrics

const std = @import("std");
const agksync = @import("../sync_compat.zig");
const agktime = @import("../time_compat.zig");
const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;

/// Jitter types for retry backoff.
pub const JitterType = enum {
    none,
    full,
    equal,
    decorrelated,
};

/// Error classification for retry strategies.
pub const ErrorClass = enum {
    transient,
    rate_limit,
    timeout,
    server_error,
    client_error,
    unknown,

    pub fn asString(self: ErrorClass) []const u8 {
        return switch (self) {
            .transient => "transient",
            .rate_limit => "rate_limit",
            .timeout => "timeout",
            .server_error => "server_error",
            .client_error => "client_error",
            .unknown => "unknown",
        };
    }
};

/// Retry strategy for specific error class.
pub const ErrorStrategy = struct {
    error_class: ErrorClass,
    max_retries: usize,
    initial_delay_ms: u64,
    max_delay_ms: u64,
    multiplier: f64,
    should_retry: bool,
};

/// Retry budget to limit costs.
pub const RetryBudget = struct {
    max_cost: f64,
    current_cost: f64,
    max_retries_per_hour: u64,
    retry_count: u64,
    window_start: i64,
};

/// Enhanced retry configuration.
pub const EnhancedRetryConfig = struct {
    // Basic retry settings
    max_retries: usize,
    initial_delay_ms: u64,
    max_delay_ms: u64,
    multiplier: f64,

    // Jitter settings
    jitter_type: JitterType,
    jitter_min_ratio: f64,

    // Error-specific strategies
    error_strategies: std.AutoHashMap(ErrorClass, ErrorStrategy),

    // Budget settings
    enable_budget: bool,
    max_cost_per_hour: f64,
    max_retries_per_hour: u64,

    // Backpressure detection
    enable_backpressure: bool,
    backpressure_threshold: f64,
    backpressure_window: usize,

    pub fn default(allocator: std.mem.Allocator) !EnhancedRetryConfig {
        var error_strategies = std.AutoHashMap(ErrorClass, ErrorStrategy).init(allocator);

        try error_strategies.put(.transient, ErrorStrategy{
            .error_class = .transient,
            .max_retries = 5,
            .initial_delay_ms = 100,
            .max_delay_ms = 5000,
            .multiplier = 2.0,
            .should_retry = true,
        });

        try error_strategies.put(.rate_limit, ErrorStrategy{
            .error_class = .rate_limit,
            .max_retries = 10,
            .initial_delay_ms = 60000,
            .max_delay_ms = 300000,
            .multiplier = 1.5,
            .should_retry = true,
        });

        try error_strategies.put(.timeout, ErrorStrategy{
            .error_class = .timeout,
            .max_retries = 3,
            .initial_delay_ms = 2000,
            .max_delay_ms = 30000,
            .multiplier = 2.0,
            .should_retry = true,
        });

        try error_strategies.put(.server_error, ErrorStrategy{
            .error_class = .server_error,
            .max_retries = 3,
            .initial_delay_ms = 5000,
            .max_delay_ms = 60000,
            .multiplier = 2.0,
            .should_retry = true,
        });

        try error_strategies.put(.client_error, ErrorStrategy{
            .error_class = .client_error,
            .max_retries = 1,
            .initial_delay_ms = 0,
            .max_delay_ms = 0,
            .multiplier = 1.0,
            .should_retry = false,
        });

        return EnhancedRetryConfig{
            .max_retries = 3,
            .initial_delay_ms = 1000,
            .max_delay_ms = 30000,
            .multiplier = 2.0,
            .jitter_type = .full,
            .jitter_min_ratio = 0.5,
            .error_strategies = error_strategies,
            .enable_budget = false,
            .max_cost_per_hour = 100.0,
            .max_retries_per_hour = 1000,
            .enable_backpressure = true,
            .backpressure_threshold = 0.5,
            .backpressure_window = 100,
        };
    }

    pub fn deinit(self: *EnhancedRetryConfig) void {
        self.error_strategies.deinit();
    }
};

/// Enhanced retry metrics.
pub const EnhancedRetryMetrics = struct {
    allocator: std.mem.Allocator,
    total_attempts: u64,
    successful_first_attempt: u64,
    successful_on_retry: u64,
    failed_after_retries: u64,
    total_retries: u64,
    total_jitter_added: f64,
    budget_exceeded_count: u64,
    backpressure_detected: u64,
    error_class_counts: std.AutoHashMap(ErrorClass, u64),
    recent_results: std.ArrayList(bool),

    pub fn init(allocator: std.mem.Allocator, _: usize) EnhancedRetryMetrics {
        return .{
            .allocator = allocator,
            .total_attempts = 0,
            .successful_first_attempt = 0,
            .successful_on_retry = 0,
            .failed_after_retries = 0,
            .total_retries = 0,
            .total_jitter_added = 0.0,
            .budget_exceeded_count = 0,
            .backpressure_detected = 0,
            .error_class_counts = std.AutoHashMap(ErrorClass, u64).init(allocator),
            .recent_results = std.ArrayList(bool).empty,
        };
    }

    pub fn deinit(self: *EnhancedRetryMetrics) void {
        self.error_class_counts.deinit();
        self.recent_results.deinit();
    }
};

/// Enhanced retry decorator wraps an agent with enhanced retry logic.
pub const EnhancedRetryDecorator = struct {
    allocator: std.mem.Allocator,
    agent: Agent,
    config: EnhancedRetryConfig,
    metrics: EnhancedRetryMetrics,
    budget: RetryBudget,
    mutex: agksync.Mutex,

    pub fn init(
        allocator: std.mem.Allocator,
        agent: Agent,
        config: EnhancedRetryConfig,
    ) EnhancedRetryDecorator {
        return .{
            .allocator = allocator,
            .agent = agent,
            .config = config,
            .metrics = EnhancedRetryMetrics.init(allocator, config.backpressure_window),
            .budget = RetryBudget{
                .max_cost = config.max_cost_per_hour,
                .current_cost = 0.0,
                .max_retries_per_hour = config.max_retries_per_hour,
                .retry_count = 0,
                .window_start = agktime.milliTimestamp(),
            },
            .mutex = agksync.Mutex{},
        };
    }

    pub fn deinit(self: *EnhancedRetryDecorator) void {
        self.metrics.deinit();
    }

    pub fn name(self: *const EnhancedRetryDecorator) []const u8 {
        return self.agent.name();
    }

    pub fn capabilities(self: *const EnhancedRetryDecorator, allocator: std.mem.Allocator) ![][]const u8 {
        return self.agent.capabilities(allocator);
    }

    fn classifyError(self: *EnhancedRetryDecorator, err: anyerror) ErrorClass {
        _ = self;
        const err_name = @errorName(err);

        if (std.mem.indexOf(u8, err_name, "RateLimit") != null or
            std.mem.indexOf(u8, err_name, "429") != null)
        {
            return .rate_limit;
        } else if (std.mem.indexOf(u8, err_name, "Timeout") != null or
            std.mem.indexOf(u8, err_name, "TimedOut") != null)
        {
            return .timeout;
        } else if (std.mem.indexOf(u8, err_name, "500") != null or
            std.mem.indexOf(u8, err_name, "502") != null or
            std.mem.indexOf(u8, err_name, "503") != null)
        {
            return .server_error;
        } else if (std.mem.indexOf(u8, err_name, "400") != null or
            std.mem.indexOf(u8, err_name, "401") != null or
            std.mem.indexOf(u8, err_name, "403") != null or
            std.mem.indexOf(u8, err_name, "404") != null)
        {
            return .client_error;
        }

        return .unknown;
    }

    fn getStrategy(self: *EnhancedRetryDecorator, error_class: ErrorClass) ErrorStrategy {
        if (self.config.error_strategies.get(error_class)) |strategy| {
            return strategy;
        }

        return ErrorStrategy{
            .error_class = error_class,
            .max_retries = self.config.max_retries,
            .initial_delay_ms = self.config.initial_delay_ms,
            .max_delay_ms = self.config.max_delay_ms,
            .multiplier = self.config.multiplier,
            .should_retry = true,
        };
    }

    fn calculateBackoff(self: *EnhancedRetryDecorator, base_backoff_ms: u64, attempt: usize) u64 {
        const base_ms = @as(f64, @floatFromInt(base_backoff_ms));
        var prng = std.Random.DefaultPrng.init(@intCast(agktime.milliTimestamp()));
        const rand = prng.random();

        const jittered_ms: f64 = switch (self.config.jitter_type) {
            .none => base_ms,
            .full => rand.float(f64) * base_ms,
            .equal => blk: {
                const min_backoff = base_ms * self.config.jitter_min_ratio;
                break :blk min_backoff + rand.float(f64) * (base_ms - min_backoff);
            },
            .decorrelated => blk: {
                if (attempt == 1) {
                    break :blk base_ms;
                }
                const previous = self.calculateBackoff(base_backoff_ms, attempt - 1);
                const previous_ms = @as(f64, @floatFromInt(previous));
                var jittered = rand.float(f64) * previous_ms * 3.0 + base_ms;
                const max_ms = @as(f64, @floatFromInt(self.config.max_delay_ms));
                if (jittered > max_ms) {
                    jittered = max_ms;
                }
                break :blk jittered;
            },
        };

        return @intFromFloat(jittered_ms);
    }

    fn checkBudget(self: *EnhancedRetryDecorator, cost: f64) bool {
        if (!self.config.enable_budget) {
            return true;
        }

        self.mutex.lock();
        defer self.mutex.unlock();

        // Reset window if hour has passed
        const hour_in_ms = 3600000;
        if (agktime.milliTimestamp() - self.budget.window_start > hour_in_ms) {
            self.budget.current_cost = 0.0;
            self.budget.retry_count = 0;
            self.budget.window_start = agktime.milliTimestamp();
        }

        // Check cost budget
        if (self.budget.current_cost + cost > self.budget.max_cost) {
            self.metrics.budget_exceeded_count += 1;
            return false;
        }

        // Check retry count budget
        if (self.budget.retry_count >= self.budget.max_retries_per_hour) {
            self.metrics.budget_exceeded_count += 1;
            return false;
        }

        return true;
    }

    fn checkBackpressure(self: *EnhancedRetryDecorator) bool {
        if (!self.config.enable_backpressure) {
            return false;
        }

        self.mutex.lock();
        defer self.mutex.unlock();

        if (self.metrics.recent_results.items.len < self.config.backpressure_window) {
            return false;
        }

        // Calculate failure rate
        var failures: usize = 0;
        for (self.metrics.recent_results.items) |success| {
            if (!success) {
                failures += 1;
            }
        }

        const failure_rate = @as(f64, @floatFromInt(failures)) / @as(f64, @floatFromInt(self.metrics.recent_results.items.len));

        if (failure_rate > self.config.backpressure_threshold) {
            self.metrics.backpressure_detected += 1;
            return true;
        }

        return false;
    }

    pub fn process(self: *EnhancedRetryDecorator, message: Message) !Message {
        var last_error: ?anyerror = null;
        var error_class: ErrorClass = .unknown;
        var strategy = self.getStrategy(error_class);

        var attempt: usize = 1;
        while (attempt <= self.config.max_retries) : (attempt += 1) {
            {
                self.mutex.lock();
                self.metrics.total_attempts += 1;
                self.mutex.unlock();
            }

            // Check budget before attempt
            if (self.config.enable_budget) {
                if (!self.checkBudget(0.0)) {
                    return error.RetryBudgetExceeded;
                }
            }

            // Check backpressure
            if (self.checkBackpressure()) {
                agktime.sleep(5000 * std.time.ns_per_ms);
            }

            // Process message
            const result = self.agent.process(message);

            if (result) |response| {
                // Success
                self.mutex.lock();
                if (attempt == 1) {
                    self.metrics.successful_first_attempt += 1;
                } else {
                    self.metrics.successful_on_retry += 1;
                }
                try self.metrics.recent_results.append(true);
                if (self.metrics.recent_results.items.len > self.config.backpressure_window) {
                    _ = self.metrics.recent_results.orderedRemove(0);
                }
                self.mutex.unlock();

                return response;
            } else |err| {
                // Failure
                last_error = err;

                // Track failure for backpressure
                {
                    self.mutex.lock();
                    try self.metrics.recent_results.append(false);
                    if (self.metrics.recent_results.items.len > self.config.backpressure_window) {
                        _ = self.metrics.recent_results.orderedRemove(0);
                    }
                    self.mutex.unlock();
                }

                // Classify error
                error_class = self.classifyError(err);
                {
                    self.mutex.lock();
                    const entry = try self.metrics.error_class_counts.getOrPut(error_class);
                    if (entry.found_existing) {
                        entry.value_ptr.* += 1;
                    } else {
                        entry.value_ptr.* = 1;
                    }
                    self.mutex.unlock();
                }

                // Get strategy for error class
                strategy = self.getStrategy(error_class);

                // Check if should retry
                if (!strategy.should_retry) {
                    self.mutex.lock();
                    self.metrics.failed_after_retries += 1;
                    self.mutex.unlock();
                    return error.NonRetryableError;
                }

                // Check if exceeded max attempts for this error class
                if (attempt >= strategy.max_retries) {
                    break;
                }

                // Track retry
                {
                    self.mutex.lock();
                    self.metrics.total_retries += 1;
                    self.budget.retry_count += 1;
                    self.mutex.unlock();
                }

                // Calculate backoff with jitter
                const exp = @as(f64, @floatFromInt(attempt - 1));
                const base_backoff_ms_float = @as(f64, @floatFromInt(strategy.initial_delay_ms)) * std.math.pow(f64, strategy.multiplier, exp);
                var base_backoff_ms = @as(u64, @intFromFloat(base_backoff_ms_float));
                if (base_backoff_ms > strategy.max_delay_ms) {
                    base_backoff_ms = strategy.max_delay_ms;
                }
                const backoff_ms = self.calculateBackoff(base_backoff_ms, attempt);

                // Sleep with backoff
                agktime.sleep(backoff_ms * std.time.ns_per_ms);
            }
        }

        // All attempts failed
        self.mutex.lock();
        self.metrics.failed_after_retries += 1;
        self.mutex.unlock();

        return last_error orelse error.MaxRetryAttemptsExceeded;
    }

    pub fn getMetrics(self: *EnhancedRetryDecorator) EnhancedRetryMetrics {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.metrics;
    }
};

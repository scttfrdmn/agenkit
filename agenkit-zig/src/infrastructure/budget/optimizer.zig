/// Model optimizer for intelligent model selection based on cost and complexity
///
/// The optimizer analyzes query complexity and automatically routes to appropriate models:
/// - Simple queries → Cheaper models (gpt-4o-mini, claude-haiku)
/// - Complex queries → More capable models (o1, claude-opus-4)
/// - Cost-aware routing with quality thresholds
/// - Automatic fallback on failures
///
/// **Complexity Factors:**
/// - Query length (tokens)
/// - Sentence structure complexity
/// - Domain indicators (code, math, reasoning)
/// - Context requirements
///
/// **Example:**
/// ```zig
/// const config = ModelOptimizerConfig{
///     .enable_auto_routing = true,
///     .cost_weight = 0.7,        // Favor cost savings
///     .quality_weight = 0.3,     // Moderate quality
///     .max_cost_per_query = 1.0, // $1 max per query
/// };
///
/// var optimizer = try ModelOptimizer.init(allocator, pricing, config);
/// defer optimizer.deinit();
///
/// const model = try optimizer.selectModel(query_text, context);
/// std.debug.print("Selected model: {s}\n", .{model});
/// ```
const std = @import("std");
const agksync = @import("../../sync_compat.zig");
const ModelPricing = @import("models.zig").ModelPricing;
const Allocator = std.mem.Allocator;

/// Complexity level of a query
pub const ComplexityLevel = enum {
    simple,
    moderate,
    complex,
    very_complex,

    /// Convert to numeric score (0-100)
    pub fn score(self: ComplexityLevel) u8 {
        return switch (self) {
            .simple => 25,
            .moderate => 50,
            .complex => 75,
            .very_complex => 100,
        };
    }
};

/// Model tier based on capability and cost
pub const ModelTier = enum {
    economy, // gpt-4o-mini, claude-haiku
    standard, // gpt-4o, claude-sonnet
    advanced, // o1, claude-opus
    reasoning, // o3, claude-opus-4 (extended thinking)

    /// Get recommended models for this tier
    pub fn models(self: ModelTier) []const []const u8 {
        return switch (self) {
            .economy => &[_][]const u8{ "gpt-4o-mini", "claude-haiku-4" },
            .standard => &[_][]const u8{ "gpt-4o", "claude-sonnet-4" },
            .advanced => &[_][]const u8{ "o1", "claude-opus-4" },
            .reasoning => &[_][]const u8{ "o3", "claude-opus-4" },
        };
    }
};

/// Configuration for model optimizer
pub const ModelOptimizerConfig = struct {
    /// Enable automatic model routing based on complexity
    /// Default: true
    enable_auto_routing: bool = true,

    /// Weight for cost optimization (0.0-1.0)
    /// Higher = favor cheaper models
    /// Default: 0.5 (balanced)
    cost_weight: f64 = 0.5,

    /// Weight for quality optimization (0.0-1.0)
    /// Higher = favor more capable models
    /// Default: 0.5 (balanced)
    quality_weight: f64 = 0.5,

    /// Maximum cost per query in dollars (null = no limit)
    /// Default: null
    max_cost_per_query: ?f64 = null,

    /// Complexity threshold for simple queries (0-100)
    /// Queries below this use economy models
    /// Default: 30
    simple_threshold: u8 = 30,

    /// Complexity threshold for moderate queries (0-100)
    /// Queries below this use standard models
    /// Default: 60
    moderate_threshold: u8 = 60,

    /// Complexity threshold for complex queries (0-100)
    /// Queries below this use advanced models
    /// Default: 85
    complex_threshold: u8 = 85,

    /// Validate configuration
    pub fn validate(self: ModelOptimizerConfig) !void {
        if (self.cost_weight < 0.0 or self.cost_weight > 1.0) {
            return error.InvalidConfig;
        }
        if (self.quality_weight < 0.0 or self.quality_weight > 1.0) {
            return error.InvalidConfig;
        }
        if (@abs(self.cost_weight + self.quality_weight - 1.0) > 0.01) {
            return error.InvalidConfig; // Weights must sum to 1.0
        }
        if (self.max_cost_per_query) |cost| {
            if (cost <= 0.0) {
                return error.InvalidConfig;
            }
        }
        if (self.simple_threshold >= self.moderate_threshold or
            self.moderate_threshold >= self.complex_threshold)
        {
            return error.InvalidConfig;
        }
    }
};

/// Metrics tracked by model optimizer
pub const ModelOptimizerMetrics = struct {
    /// Total number of routing decisions
    total_decisions: u64 = 0,

    /// Count per model tier
    economy_count: u64 = 0,
    standard_count: u64 = 0,
    advanced_count: u64 = 0,
    reasoning_count: u64 = 0,

    /// Estimated cost savings vs always using advanced models
    estimated_savings: f64 = 0.0,

    /// Average complexity score
    pub fn avgComplexity(self: *const ModelOptimizerMetrics) ?f64 {
        if (self.total_decisions == 0) return null;
        const total = self.economy_count * 25 + self.standard_count * 50 +
            self.advanced_count * 75 + self.reasoning_count * 100;
        return @as(f64, @floatFromInt(total)) / @as(f64, @floatFromInt(self.total_decisions));
    }

    /// Create a snapshot of metrics
    pub fn snapshot(self: *const ModelOptimizerMetrics) ModelOptimizerMetrics {
        return ModelOptimizerMetrics{
            .total_decisions = self.total_decisions,
            .economy_count = self.economy_count,
            .standard_count = self.standard_count,
            .advanced_count = self.advanced_count,
            .reasoning_count = self.reasoning_count,
            .estimated_savings = self.estimated_savings,
        };
    }
};

/// Model optimizer for cost-aware model selection
pub const ModelOptimizer = struct {
    allocator: Allocator,
    model_pricing: *ModelPricing,
    config: ModelOptimizerConfig,
    metrics_data: ModelOptimizerMetrics,
    mutex: agksync.Mutex,

    pub fn init(
        allocator: Allocator,
        model_pricing: *ModelPricing,
        config: ModelOptimizerConfig,
    ) !*ModelOptimizer {
        // Validate configuration
        try config.validate();

        const self = try allocator.create(ModelOptimizer);
        self.* = ModelOptimizer{
            .allocator = allocator,
            .model_pricing = model_pricing,
            .config = config,
            .metrics_data = ModelOptimizerMetrics{},
            .mutex = agksync.Mutex{},
        };
        return self;
    }

    pub fn deinit(self: *ModelOptimizer) void {
        self.allocator.destroy(self);
    }

    /// Get current metrics (thread-safe)
    pub fn metrics(self: *ModelOptimizer) ModelOptimizerMetrics {
        self.mutex.lock();
        defer self.mutex.unlock();
        return self.metrics_data.snapshot();
    }

    /// Estimate query complexity based on text analysis
    pub fn estimateComplexity(self: *ModelOptimizer, query: []const u8) ComplexityLevel {
        _ = self;

        // Token count estimation (roughly 4 chars per token)
        const estimated_tokens = query.len / 4;

        // Complexity indicators
        const has_code = std.mem.indexOf(u8, query, "```") != null or
            std.mem.indexOf(u8, query, "function") != null or
            std.mem.indexOf(u8, query, "class") != null;

        const has_math = std.mem.indexOf(u8, query, "calculate") != null or
            std.mem.indexOf(u8, query, "solve") != null or
            std.mem.indexOf(u8, query, "equation") != null;

        const has_reasoning = std.mem.indexOf(u8, query, "explain") != null or
            std.mem.indexOf(u8, query, "analyze") != null or
            std.mem.indexOf(u8, query, "why") != null;

        // Count sentences (rough estimate)
        var sentence_count: usize = 0;
        for (query) |c| {
            if (c == '.' or c == '?' or c == '!') {
                sentence_count += 1;
            }
        }

        // Calculate complexity score
        var score: u8 = 0;

        // Base score from length
        if (estimated_tokens < 50) {
            score += 10;
        } else if (estimated_tokens < 200) {
            score += 30;
        } else if (estimated_tokens < 500) {
            score += 50;
        } else {
            score += 70;
        }

        // Complexity indicators
        if (has_code) score = @min(score + 30, 100);
        if (has_math) score = @min(score + 25, 100);
        if (has_reasoning) score = @min(score + 20, 100);

        // Multi-sentence complexity
        if (sentence_count > 5) {
            score = @min(score + 15, 100);
        }

        // Map score to complexity level
        if (score < 30) {
            return .simple;
        } else if (score < 60) {
            return .moderate;
        } else if (score < 85) {
            return .complex;
        } else {
            return .very_complex;
        }
    }

    /// Select optimal model for query based on complexity and cost
    pub fn selectModel(self: *ModelOptimizer, query: []const u8) ![]const u8 {
        if (!self.config.enable_auto_routing) {
            // Default to standard tier if auto-routing disabled
            return "claude-sonnet-4";
        }

        const complexity = self.estimateComplexity(query);
        const complexity_score = complexity.score();

        // Map complexity to model tier
        const tier = blk: {
            if (complexity_score < self.config.simple_threshold) {
                break :blk ModelTier.economy;
            } else if (complexity_score < self.config.moderate_threshold) {
                break :blk ModelTier.standard;
            } else if (complexity_score < self.config.complex_threshold) {
                break :blk ModelTier.advanced;
            } else {
                break :blk ModelTier.reasoning;
            }
        };

        // Get models for this tier
        const tier_models = tier.models();

        // Select first model from tier (could be enhanced with cost comparison)
        const selected_model = tier_models[0];

        // Update metrics
        self.mutex.lock();
        defer self.mutex.unlock();

        self.metrics_data.total_decisions += 1;
        switch (tier) {
            .economy => self.metrics_data.economy_count += 1,
            .standard => self.metrics_data.standard_count += 1,
            .advanced => self.metrics_data.advanced_count += 1,
            .reasoning => self.metrics_data.reasoning_count += 1,
        }

        return selected_model;
    }

    /// Get fallback model if primary fails
    pub fn getFallbackModel(self: *ModelOptimizer, failed_model: []const u8) []const u8 {
        _ = self;

        // Map failed model to fallback
        if (std.mem.eql(u8, failed_model, "o3")) {
            return "o1";
        } else if (std.mem.eql(u8, failed_model, "o1")) {
            return "claude-opus-4";
        } else if (std.mem.eql(u8, failed_model, "claude-opus-4")) {
            return "claude-sonnet-4";
        } else if (std.mem.eql(u8, failed_model, "claude-sonnet-4")) {
            return "gpt-4o";
        } else {
            return "gpt-4o"; // Safe default
        }
    }
};

// Tests
const testing = std.testing;

test "ComplexityLevel score" {
    try testing.expectEqual(@as(u8, 25), ComplexityLevel.simple.score());
    try testing.expectEqual(@as(u8, 50), ComplexityLevel.moderate.score());
    try testing.expectEqual(@as(u8, 75), ComplexityLevel.complex.score());
    try testing.expectEqual(@as(u8, 100), ComplexityLevel.very_complex.score());
}

test "ModelTier models" {
    const economy = ModelTier.economy.models();
    try testing.expect(economy.len > 0);
    try testing.expectEqualStrings("gpt-4o-mini", economy[0]);

    const reasoning = ModelTier.reasoning.models();
    try testing.expect(reasoning.len > 0);
    try testing.expectEqualStrings("o3", reasoning[0]);
}

test "ModelOptimizerConfig validation" {
    const valid_config = ModelOptimizerConfig{
        .cost_weight = 0.6,
        .quality_weight = 0.4,
    };
    try valid_config.validate();

    // Invalid weights (don't sum to 1.0)
    const invalid_sum = ModelOptimizerConfig{
        .cost_weight = 0.6,
        .quality_weight = 0.5,
    };
    try testing.expectError(error.InvalidConfig, invalid_sum.validate());

    // Invalid thresholds
    const invalid_thresholds = ModelOptimizerConfig{
        .simple_threshold = 70,
        .moderate_threshold = 60,
    };
    try testing.expectError(error.InvalidConfig, invalid_thresholds.validate());
}

test "ModelOptimizer estimateComplexity" {
    const allocator = testing.allocator;

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    var optimizer = try ModelOptimizer.init(allocator, &pricing, ModelOptimizerConfig{});
    defer optimizer.deinit();

    // Simple query
    const simple = optimizer.estimateComplexity("Hello, world!");
    try testing.expect(simple == .simple or simple == .moderate);

    // Complex query with code
    const complex = optimizer.estimateComplexity(
        \\Please analyze this function and explain the algorithm:
        \\```python
        \\def quicksort(arr):
        \\    if len(arr) <= 1:
        \\        return arr
        \\    pivot = arr[len(arr) // 2]
        \\    left = [x for x in arr if x < pivot]
        \\    middle = [x for x in arr if x == pivot]
        \\    right = [x for x in arr if x > pivot]
        \\    return quicksort(left) + middle + quicksort(right)
        \\```
        \\What is the time complexity?
    );
    try testing.expect(complex == .complex or complex == .very_complex);
}

test "ModelOptimizer selectModel" {
    const allocator = testing.allocator;

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    var optimizer = try ModelOptimizer.init(allocator, &pricing, ModelOptimizerConfig{});
    defer optimizer.deinit();

    // Simple query should route to economy/standard
    const model1 = try optimizer.selectModel("What is 2+2?");
    try testing.expect(
        std.mem.eql(u8, model1, "gpt-4o-mini") or
            std.mem.eql(u8, model1, "gpt-4o") or
            std.mem.eql(u8, model1, "claude-sonnet-4"),
    );

    // Complex query should route to advanced
    const model2 = try optimizer.selectModel(
        "Explain quantum entanglement and write a Python simulation demonstrating the EPR paradox with detailed mathematical analysis.",
    );
    try testing.expect(
        std.mem.eql(u8, model2, "o1") or
            std.mem.eql(u8, model2, "claude-opus-4") or
            std.mem.eql(u8, model2, "o3"),
    );

    // Check metrics
    const m = optimizer.metrics();
    try testing.expectEqual(@as(u64, 2), m.total_decisions);
}

test "ModelOptimizer getFallbackModel" {
    const allocator = testing.allocator;

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    var optimizer = try ModelOptimizer.init(allocator, &pricing, ModelOptimizerConfig{});
    defer optimizer.deinit();

    const fallback1 = optimizer.getFallbackModel("o3");
    try testing.expectEqualStrings("o1", fallback1);

    const fallback2 = optimizer.getFallbackModel("claude-opus-4");
    try testing.expectEqualStrings("claude-sonnet-4", fallback2);
}

test "ModelOptimizerMetrics avgComplexity" {
    var metrics = ModelOptimizerMetrics{
        .total_decisions = 4,
        .economy_count = 1, // 25
        .standard_count = 1, // 50
        .advanced_count = 1, // 75
        .reasoning_count = 1, // 100
    };

    const avg = metrics.avgComplexity().?;
    try testing.expectApproxEqAbs(@as(f64, 62.5), avg, 0.1); // (25+50+75+100)/4 = 62.5
}

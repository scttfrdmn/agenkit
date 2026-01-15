/// Budget tracking models and pricing data.
///
/// Provides cost tracking and model pricing for LLM usage (November 2025 rates).
///
/// Components:
///   - ModelPricing: Pricing data for all major LLM models
///   - Cost: Single cost record with token counts and costs
///
/// Example:
///   var pricing = ModelPricing.init(allocator);
///   defer pricing.deinit();
///   const cost = try pricing.calculate("claude-sonnet-4", 10000, .input);
///   std.debug.print("Cost: ${d:.4}\n", .{cost});
const std = @import("std");
const Allocator = std.mem.Allocator;

/// Direction for cost calculation (input or output tokens).
pub const Direction = enum {
    input,
    output,
    thinking, // Extended thinking tokens (o3, Claude 4)

    pub fn toString(self: Direction) []const u8 {
        return switch (self) {
            .input => "input",
            .output => "output",
            .thinking => "thinking",
        };
    }
};

/// ModelPricing provides pricing data for LLM models (November 2025 rates).
///
/// All prices are per 1 million tokens.
///
/// Example:
///   var pricing = ModelPricing.init(allocator);
///   defer pricing.deinit();
///   const cost = try pricing.calculate("gpt-4o", 100000, .input);
pub const ModelPricing = struct {
    allocator: Allocator,
    mutex: std.Thread.Mutex,
    pricing: std.StringHashMap(PricingData),

    pub const PricingData = struct {
        input: f64,
        output: f64,
        thinking: f64, // For models with extended thinking

        pub fn init(input: f64, output: f64, thinking: f64) PricingData {
            return .{
                .input = input,
                .output = output,
                .thinking = thinking,
            };
        }
    };

    pub fn init(allocator: Allocator) !ModelPricing {
        var pricing = std.StringHashMap(PricingData).init(allocator);

        // Initialize with default pricing (November 2025 rates)
        // We need to dupe the keys since they're string literals
        const models = [_]struct { name: []const u8, data: PricingData }{
            // OpenAI
            .{ .name = "gpt-4o", .data = PricingData.init(2.50, 10.00, 0.0) },
            .{ .name = "gpt-4-turbo", .data = PricingData.init(10.00, 30.00, 0.0) },
            .{ .name = "gpt-3.5-turbo", .data = PricingData.init(0.50, 1.50, 0.0) },
            .{ .name = "o3", .data = PricingData.init(5.00, 15.00, 10.00) },
            .{ .name = "o3-mini", .data = PricingData.init(1.00, 3.00, 2.00) },

            // Anthropic
            .{ .name = "claude-opus-4", .data = PricingData.init(15.00, 75.00, 20.00) },
            .{ .name = "claude-sonnet-4", .data = PricingData.init(3.00, 15.00, 5.00) },
            .{ .name = "claude-sonnet-4.5", .data = PricingData.init(3.00, 15.00, 5.00) },
            .{ .name = "claude-haiku-3", .data = PricingData.init(0.25, 1.25, 0.0) },

            // Google
            .{ .name = "gemini-2.0-flash-exp", .data = PricingData.init(0.00, 0.00, 0.0) }, // Free tier
            .{ .name = "gemini-pro", .data = PricingData.init(0.50, 1.50, 0.0) },

            // Default fallback
            .{ .name = "default", .data = PricingData.init(0.01, 0.01, 0.01) },
        };

        for (models) |model| {
            const key = try allocator.dupe(u8, model.name);
            try pricing.put(key, model.data);
        }

        return .{
            .allocator = allocator,
            .mutex = .{},
            .pricing = pricing,
        };
    }

    pub fn deinit(self: *ModelPricing) void {
        // Free all keys in the HashMap
        var iter = self.pricing.keyIterator();
        while (iter.next()) |key| {
            self.allocator.free(key.*);
        }
        self.pricing.deinit();
    }

    /// Calculate cost for a given number of tokens.
    ///
    /// Args:
    ///   model: Model identifier (e.g., "claude-sonnet-4")
    ///   tokens: Number of tokens
    ///   direction: input, output, or thinking
    ///
    /// Returns:
    ///   Cost in dollars
    ///
    /// Example:
    ///   const cost = try pricing.calculate("claude-opus-4", 100000, .input);
    ///   // Returns 1.50 ($15.00 per 1M tokens * 0.1M tokens)
    pub fn calculate(self: *ModelPricing, model: []const u8, tokens: usize, direction: Direction) !f64 {
        self.mutex.lock();
        defer self.mutex.unlock();

        const pricing_data = self.pricing.get(model) orelse blk: {
            std.log.warn("Unknown model '{s}', using default pricing", .{model});
            break :blk self.pricing.get("default").?;
        };

        const price_per_million = switch (direction) {
            .input => pricing_data.input,
            .output => pricing_data.output,
            .thinking => pricing_data.thinking,
        };

        return (@as(f64, @floatFromInt(tokens)) / 1_000_000.0) * price_per_million;
    }

    /// Get pricing data for a specific model.
    ///
    /// Args:
    ///   model: Model identifier
    ///
    /// Returns:
    ///   PricingData or null if not found
    ///
    /// Example:
    ///   if (pricing.getModelPricing("claude-sonnet-4")) |data| {
    ///       std.debug.print("Input: ${d:.2}/M, Output: ${d:.2}/M\n",
    ///           .{data.input, data.output});
    ///   }
    pub fn getModelPricing(self: *ModelPricing, model: []const u8) ?PricingData {
        self.mutex.lock();
        defer self.mutex.unlock();

        return self.pricing.get(model);
    }

    /// List all supported models.
    ///
    /// Returns:
    ///   Slice of model identifiers (caller owns memory)
    ///
    /// Example:
    ///   const models = try pricing.listModels();
    ///   defer allocator.free(models);
    ///   for (models) |model| {
    ///       std.debug.print("Model: {s}\n", .{model});
    ///   }
    pub fn listModels(self: *ModelPricing) ![]const []const u8 {
        self.mutex.lock();
        defer self.mutex.unlock();

        var models = std.ArrayList([]const u8).init(self.allocator);
        var iter = self.pricing.keyIterator();
        while (iter.next()) |key| {
            if (!std.mem.eql(u8, key.*, "default")) {
                const key_copy = try self.allocator.dupe(u8, key.*);
                try models.append(key_copy);
            }
        }

        return try models.toOwnedSlice();
    }

    /// Update pricing for a model (for testing or custom deployments).
    ///
    /// Args:
    ///   model: Model identifier
    ///   input_price: Price per 1M input tokens
    ///   output_price: Price per 1M output tokens
    ///   thinking_price: Price per 1M thinking tokens
    ///
    /// Example:
    ///   try pricing.updatePricing("custom-model", 1.0, 5.0, 2.0);
    pub fn updatePricing(self: *ModelPricing, model: []const u8, input_price: f64, output_price: f64, thinking_price: f64) !void {
        self.mutex.lock();
        defer self.mutex.unlock();

        const model_copy = try self.allocator.dupe(u8, model);
        try self.pricing.put(model_copy, PricingData.init(input_price, output_price, thinking_price));

        std.log.info("Updated pricing for {s}: ${d:.2}/M input, ${d:.2}/M output, ${d:.2}/M thinking", .{
            model,
            input_price,
            output_price,
            thinking_price,
        });
    }

    /// Estimate conversation cost for multiple turns.
    ///
    /// Args:
    ///   model: Model identifier
    ///   num_turns: Number of conversation turns
    ///   avg_input_tokens: Average input tokens per turn
    ///   avg_output_tokens: Average output tokens per turn
    ///
    /// Returns:
    ///   Estimated total cost in dollars
    ///
    /// Example:
    ///   const cost = try pricing.estimateConversationCost(
    ///       "claude-sonnet-4",
    ///       100,  // 100 turns
    ///       1000, // 1000 input tokens per turn
    ///       500,  // 500 output tokens per turn
    ///   );
    pub fn estimateConversationCost(
        self: *ModelPricing,
        model: []const u8,
        num_turns: usize,
        avg_input_tokens: usize,
        avg_output_tokens: usize,
    ) !f64 {
        const total_input = num_turns * avg_input_tokens;
        const total_output = num_turns * avg_output_tokens;

        const input_cost = try self.calculate(model, total_input, .input);
        const output_cost = try self.calculate(model, total_output, .output);

        return input_cost + output_cost;
    }

    /// Compare costs across different models.
    ///
    /// Args:
    ///   models: List of model identifiers
    ///   input_tokens: Number of input tokens
    ///   output_tokens: Number of output tokens
    ///
    /// Returns:
    ///   HashMap from model to total cost (caller owns memory)
    ///
    /// Example:
    ///   const comparison = try pricing.compareModels(
    ///       &[_][]const u8{"claude-haiku-3", "claude-sonnet-4", "claude-opus-4"},
    ///       100000, // input tokens
    ///       50000,  // output tokens
    ///   );
    ///   defer {
    ///       var iter = comparison.iterator();
    ///       while (iter.next()) |entry| {
    ///           allocator.free(entry.key_ptr.*);
    ///       }
    ///       comparison.deinit();
    ///   }
    pub fn compareModels(
        self: *ModelPricing,
        models: []const []const u8,
        input_tokens: usize,
        output_tokens: usize,
    ) !std.StringHashMap(f64) {
        var costs = std.StringHashMap(f64).init(self.allocator);

        for (models) |model| {
            const input_cost = try self.calculate(model, input_tokens, .input);
            const output_cost = try self.calculate(model, output_tokens, .output);
            const total_cost = input_cost + output_cost;

            const model_copy = try self.allocator.dupe(u8, model);
            try costs.put(model_copy, total_cost);
        }

        return costs;
    }
};

/// Cost represents a single cost record.
///
/// Fields:
///   - session_id: Session identifier
///   - agent_name: Agent name
///   - model: Model identifier
///   - input_tokens: Number of input tokens
///   - output_tokens: Number of output tokens
///   - thinking_tokens: Number of thinking/reasoning tokens
///   - input_cost: Cost for input tokens ($)
///   - output_cost: Cost for output tokens ($)
///   - thinking_cost: Cost for thinking tokens ($)
///   - total_cost: Total cost ($)
///   - timestamp: When cost was recorded (Unix millis)
///   - metadata: Additional metadata (JSON)
pub const Cost = struct {
    session_id: []const u8,
    agent_name: []const u8,
    model: []const u8,
    input_tokens: usize,
    output_tokens: usize,
    thinking_tokens: usize,
    input_cost: f64,
    output_cost: f64,
    thinking_cost: f64,
    total_cost: f64,
    timestamp: i64,
    metadata: std.json.Value,
    allocator: Allocator,

    /// Create a new Cost record.
    ///
    /// Args:
    ///   allocator: Memory allocator
    ///   session_id: Session identifier
    ///   agent_name: Agent name
    ///   model: Model identifier
    ///   input_tokens: Number of input tokens
    ///   output_tokens: Number of output tokens
    ///   thinking_tokens: Number of thinking tokens
    ///   pricing: ModelPricing instance for cost calculation
    ///
    /// Returns:
    ///   Cost record with calculated costs
    ///
    /// Example:
    ///   var cost = try Cost.init(
    ///       allocator,
    ///       "session-1",
    ///       "assistant",
    ///       "claude-sonnet-4",
    ///       1000,
    ///       500,
    ///       0,
    ///       &pricing
    ///   );
    ///   defer cost.deinit();
    pub fn init(
        allocator: Allocator,
        session_id: []const u8,
        agent_name: []const u8,
        model: []const u8,
        input_tokens: usize,
        output_tokens: usize,
        thinking_tokens: usize,
        pricing: *ModelPricing,
    ) !Cost {
        const input_cost = try pricing.calculate(model, input_tokens, .input);
        const output_cost = try pricing.calculate(model, output_tokens, .output);
        const thinking_cost = if (thinking_tokens > 0)
            try pricing.calculate(model, thinking_tokens, .thinking)
        else
            0.0;

        const total_cost = input_cost + output_cost + thinking_cost;

        return .{
            .session_id = try allocator.dupe(u8, session_id),
            .agent_name = try allocator.dupe(u8, agent_name),
            .model = try allocator.dupe(u8, model),
            .input_tokens = input_tokens,
            .output_tokens = output_tokens,
            .thinking_tokens = thinking_tokens,
            .input_cost = input_cost,
            .output_cost = output_cost,
            .thinking_cost = thinking_cost,
            .total_cost = total_cost,
            .timestamp = std.time.milliTimestamp(),
            .metadata = std.json.Value{ .object = std.json.ObjectMap.init(allocator) },
            .allocator = allocator,
        };
    }

    pub fn deinit(self: *Cost) void {
        self.allocator.free(self.session_id);
        self.allocator.free(self.agent_name);
        self.allocator.free(self.model);
        switch (self.metadata) {
            .object => |*obj| obj.deinit(),
            else => {},
        }
    }

    /// Convert Cost to JSON-serializable map.
    ///
    /// Returns:
    ///   JSON Value (caller owns memory)
    ///
    /// Example:
    ///   const json_value = try cost.toJson();
    ///   defer json_value.object.deinit();
    pub fn toJson(self: *const Cost) !std.json.Value {
        var obj = std.json.ObjectMap.init(self.allocator);

        try obj.put("session_id", .{ .string = self.session_id });
        try obj.put("agent_name", .{ .string = self.agent_name });
        try obj.put("model", .{ .string = self.model });
        try obj.put("input_tokens", .{ .integer = @intCast(self.input_tokens) });
        try obj.put("output_tokens", .{ .integer = @intCast(self.output_tokens) });
        try obj.put("thinking_tokens", .{ .integer = @intCast(self.thinking_tokens) });
        try obj.put("input_cost", .{ .float = self.input_cost });
        try obj.put("output_cost", .{ .float = self.output_cost });
        try obj.put("thinking_cost", .{ .float = self.thinking_cost });
        try obj.put("total_cost", .{ .float = self.total_cost });
        try obj.put("timestamp", .{ .integer = self.timestamp });
        try obj.put("metadata", self.metadata);

        return std.json.Value{ .object = obj };
    }
};

// Tests
test "ModelPricing creation" {
    const allocator = std.testing.allocator;

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    // Verify some default prices exist
    const claude_pricing = pricing.getModelPricing("claude-sonnet-4").?;
    try std.testing.expectEqual(@as(f64, 3.00), claude_pricing.input);
    try std.testing.expectEqual(@as(f64, 15.00), claude_pricing.output);
}

test "ModelPricing calculate" {
    const allocator = std.testing.allocator;

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    // Test input cost calculation
    const input_cost = try pricing.calculate("claude-opus-4", 100_000, .input);
    try std.testing.expectApproxEqAbs(@as(f64, 1.50), input_cost, 0.01);

    // Test output cost calculation
    const output_cost = try pricing.calculate("claude-opus-4", 100_000, .output);
    try std.testing.expectApproxEqAbs(@as(f64, 7.50), output_cost, 0.01);

    // Test unknown model defaults
    const default_cost = try pricing.calculate("unknown-model", 100_000, .input);
    try std.testing.expectApproxEqAbs(@as(f64, 0.001), default_cost, 0.0001);
}

test "ModelPricing updatePricing" {
    const allocator = std.testing.allocator;

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    // Update pricing
    try pricing.updatePricing("custom-model", 1.0, 5.0, 2.0);

    // Verify update
    const custom_pricing = pricing.getModelPricing("custom-model").?;
    try std.testing.expectEqual(@as(f64, 1.0), custom_pricing.input);
    try std.testing.expectEqual(@as(f64, 5.0), custom_pricing.output);
    try std.testing.expectEqual(@as(f64, 2.0), custom_pricing.thinking);
}

test "ModelPricing estimateConversationCost" {
    const allocator = std.testing.allocator;

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    const cost = try pricing.estimateConversationCost(
        "claude-sonnet-4",
        100, // 100 turns
        1000, // 1000 input tokens per turn
        500, // 500 output tokens per turn
    );

    // Expected: (100 * 1000 / 1M * 3.00) + (100 * 500 / 1M * 15.00)
    //         = (0.1 * 3.00) + (0.05 * 15.00)
    //         = 0.30 + 0.75 = 1.05
    try std.testing.expectApproxEqAbs(@as(f64, 1.05), cost, 0.01);
}

test "Cost creation" {
    const allocator = std.testing.allocator;

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    var cost = try Cost.init(
        allocator,
        "session-1",
        "assistant",
        "claude-sonnet-4",
        1000,
        500,
        0,
        &pricing,
    );
    defer cost.deinit();

    // Verify cost calculations
    try std.testing.expectApproxEqAbs(@as(f64, 0.003), cost.input_cost, 0.0001);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0075), cost.output_cost, 0.0001);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0105), cost.total_cost, 0.001);
}

test "Cost toJson" {
    const allocator = std.testing.allocator;

    var pricing = try ModelPricing.init(allocator);
    defer pricing.deinit();

    var cost = try Cost.init(
        allocator,
        "session-1",
        "assistant",
        "gpt-4o",
        2000,
        1000,
        0,
        &pricing,
    );
    defer cost.deinit();

    var json_value = try cost.toJson();
    defer json_value.object.deinit();

    // Verify JSON structure
    try std.testing.expect(json_value.object.get("session_id") != null);
    try std.testing.expect(json_value.object.get("total_cost") != null);
}

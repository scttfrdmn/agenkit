/// Optimization framework for hyperparameter tuning
///
/// This module provides infrastructure for optimizing agent configurations,
/// including search space definition and optimization algorithms.
///
/// Key design principles:
/// - Flexible search space (continuous, discrete, integer, categorical)
/// - Pluggable optimization algorithms
/// - History tracking for analysis
/// - Support for maximization and minimization
const std = @import("std");
const agktime = @import("../time_compat.zig");
const Allocator = std.mem.Allocator;

/// Parameter type in search space
pub const ParameterType = enum {
    continuous, // Float range [min, max]
    discrete, // Specific float values
    integer, // Integer range [min, max]
    categorical, // String choices

    pub fn toString(self: ParameterType) []const u8 {
        return switch (self) {
            .continuous => "continuous",
            .discrete => "discrete",
            .integer => "integer",
            .categorical => "categorical",
        };
    }
};

/// Parameter bounds for search space
pub const ParameterBounds = union(ParameterType) {
    continuous: struct { min: f64, max: f64 },
    discrete: []const f64,
    integer: struct { min: i64, max: i64 },
    categorical: []const []const u8,

    pub fn deinit(self: *ParameterBounds, allocator: Allocator) void {
        switch (self.*) {
            .discrete => |values| allocator.free(values),
            .categorical => |choices| {
                for (choices) |choice| {
                    allocator.free(choice);
                }
                allocator.free(choices);
            },
            else => {},
        }
    }
};

/// Parameter definition
pub const Parameter = struct {
    name: []const u8,
    param_type: ParameterType,
    bounds: ParameterBounds,
    allocator: Allocator,

    pub fn deinit(self: *Parameter) void {
        self.allocator.free(self.name);
        self.bounds.deinit(self.allocator);
    }
};

/// Configuration value (can be float, int, or string)
pub const ConfigValue = union(enum) {
    float: f64,
    int: i64,
    string: []const u8,

    pub fn deinit(self: *ConfigValue, allocator: Allocator) void {
        switch (self.*) {
            .string => |s| allocator.free(s),
            else => {},
        }
    }
};

/// Search space definition
pub const SearchSpace = struct {
    parameters: std.ArrayList(Parameter),
    allocator: Allocator,
    rng: std.Random.DefaultPrng,

    pub fn init(allocator: Allocator) !*SearchSpace {
        const self = try allocator.create(SearchSpace);
        const seed = @as(u64, @intCast(agktime.timestamp()));
        self.* = SearchSpace{
            .parameters = std.ArrayList(Parameter).empty,
            .allocator = allocator,
            .rng = std.Random.DefaultPrng.init(seed),
        };
        return self;
    }

    /// Add continuous parameter [min, max]
    pub fn addContinuous(self: *SearchSpace, name: []const u8, min: f64, max: f64) !void {
        const param = Parameter{
            .name = try self.allocator.dupe(u8, name),
            .param_type = .continuous,
            .bounds = .{ .continuous = .{ .min = min, .max = max } },
            .allocator = self.allocator,
        };
        try self.parameters.append(self.allocator, param);
    }

    /// Add discrete parameter (specific values)
    pub fn addDiscrete(self: *SearchSpace, name: []const u8, values: []const f64) !void {
        const param = Parameter{
            .name = try self.allocator.dupe(u8, name),
            .param_type = .discrete,
            .bounds = .{ .discrete = try self.allocator.dupe(f64, values) },
            .allocator = self.allocator,
        };
        try self.parameters.append(self.allocator, param);
    }

    /// Add integer parameter [min, max]
    pub fn addInteger(self: *SearchSpace, name: []const u8, min: i64, max: i64) !void {
        const param = Parameter{
            .name = try self.allocator.dupe(u8, name),
            .param_type = .integer,
            .bounds = .{ .integer = .{ .min = min, .max = max } },
            .allocator = self.allocator,
        };
        try self.parameters.append(self.allocator, param);
    }

    /// Add categorical parameter (choices)
    pub fn addCategorical(self: *SearchSpace, name: []const u8, choices: []const []const u8) !void {
        const choices_copy = try self.allocator.alloc([]const u8, choices.len);
        for (choices, 0..) |choice, i| {
            choices_copy[i] = try self.allocator.dupe(u8, choice);
        }

        const param = Parameter{
            .name = try self.allocator.dupe(u8, name),
            .param_type = .categorical,
            .bounds = .{ .categorical = choices_copy },
            .allocator = self.allocator,
        };
        try self.parameters.append(self.allocator, param);
    }

    /// Sample random configuration from search space
    pub fn sample(self: *SearchSpace) !std.StringHashMap(ConfigValue) {
        var config = std.StringHashMap(ConfigValue).init(self.allocator);
        const random = self.rng.random();

        for (self.parameters.items) |param| {
            const name_copy = try self.allocator.dupe(u8, param.name);

            const value = switch (param.bounds) {
                .continuous => |bounds| blk: {
                    const range = bounds.max - bounds.min;
                    const val = bounds.min + random.float(f64) * range;
                    break :blk ConfigValue{ .float = val };
                },
                .discrete => |values| blk: {
                    const idx = random.intRangeLessThan(usize, 0, values.len);
                    break :blk ConfigValue{ .float = values[idx] };
                },
                .integer => |bounds| blk: {
                    const val = random.intRangeAtMost(i64, bounds.min, bounds.max);
                    break :blk ConfigValue{ .int = val };
                },
                .categorical => |choices| blk: {
                    const idx = random.intRangeLessThan(usize, 0, choices.len);
                    const choice_copy = try self.allocator.dupe(u8, choices[idx]);
                    break :blk ConfigValue{ .string = choice_copy };
                },
            };

            try config.put(name_copy, value);
        }

        return config;
    }

    /// Validate configuration against search space
    pub fn validate(self: *const SearchSpace, config: std.StringHashMap(ConfigValue)) bool {
        // Check all parameters are present
        for (self.parameters.items) |param| {
            if (!config.contains(param.name)) {
                return false;
            }

            const value = config.get(param.name).?;

            // Check value matches parameter type and bounds
            const valid = switch (param.bounds) {
                .continuous => |bounds| blk: {
                    if (value != .float) break :blk false;
                    const val = value.float;
                    break :blk val >= bounds.min and val <= bounds.max;
                },
                .integer => |bounds| blk: {
                    if (value != .int) break :blk false;
                    const val = value.int;
                    break :blk val >= bounds.min and val <= bounds.max;
                },
                .discrete => |values| blk: {
                    if (value != .float) break :blk false;
                    const val = value.float;
                    for (values) |v| {
                        if (val == v) break :blk true;
                    }
                    break :blk false;
                },
                .categorical => |choices| blk: {
                    if (value != .string) break :blk false;
                    const val = value.string;
                    for (choices) |choice| {
                        if (std.mem.eql(u8, val, choice)) break :blk true;
                    }
                    break :blk false;
                },
            };

            if (!valid) return false;
        }

        return true;
    }

    pub fn deinit(self: *SearchSpace) void {
        for (self.parameters.items) |*param| {
            param.deinit();
        }
        self.parameters.deinit(self.allocator);
        self.allocator.destroy(self);
    }
};

/// Optimization history entry
pub const OptimizationStep = struct {
    config: std.StringHashMap(ConfigValue),
    score: f64,
    allocator: Allocator,

    pub fn deinit(self: *OptimizationStep) void {
        var it = self.config.iterator();
        while (it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            entry.value_ptr.deinit(self.allocator);
        }
        self.config.deinit();
    }
};

/// Optimization result
pub const OptimizationResult = struct {
    best_config: std.StringHashMap(ConfigValue),
    best_score: f64,
    n_iterations: usize,
    history: std.ArrayList(OptimizationStep),
    start_time: i64,
    end_time: i64,
    allocator: Allocator,

    pub fn init(allocator: Allocator) !*OptimizationResult {
        const self = try allocator.create(OptimizationResult);
        self.* = OptimizationResult{
            .best_config = std.StringHashMap(ConfigValue).init(allocator),
            .best_score = -std.math.inf(f64), // Start with worst possible
            .n_iterations = 0,
            .history = std.ArrayList(OptimizationStep).empty,
            .start_time = agktime.timestamp(),
            .end_time = 0,
            .allocator = allocator,
        };
        return self;
    }

    pub fn durationSecs(self: *const OptimizationResult) f64 {
        return @as(f64, @floatFromInt(self.end_time - self.start_time));
    }

    pub fn deinit(self: *OptimizationResult) void {
        var it = self.best_config.iterator();
        while (it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            entry.value_ptr.deinit(self.allocator);
        }
        self.best_config.deinit();

        for (self.history.items) |*step| {
            step.deinit();
        }
        self.history.deinit(self.allocator);

        self.allocator.destroy(self);
    }
};

/// Random search optimizer
pub const RandomSearchOptimizer = struct {
    search_space: *SearchSpace,
    maximize: bool,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        search_space: *SearchSpace,
        maximize: bool,
    ) !*RandomSearchOptimizer {
        const self = try allocator.create(RandomSearchOptimizer);
        self.* = RandomSearchOptimizer{
            .search_space = search_space,
            .maximize = maximize,
            .allocator = allocator,
        };
        return self;
    }

    /// Objective function type
    pub const ObjectiveFn = *const fn (std.StringHashMap(ConfigValue)) anyerror!f64;

    /// Run optimization
    pub fn optimize(
        self: *RandomSearchOptimizer,
        objective: ObjectiveFn,
        n_iterations: usize,
    ) !*OptimizationResult {
        const result = try OptimizationResult.init(self.allocator);
        result.n_iterations = n_iterations;

        for (0..n_iterations) |_| {
            // Sample random configuration
            var config = try self.search_space.sample();

            // Evaluate objective
            const score = try objective(config);

            // Update best if improved
            const is_better = if (self.maximize)
                score > result.best_score
            else
                score < result.best_score;

            if (is_better or result.history.items.len == 0) {
                // Clear old best config
                var old_it = result.best_config.iterator();
                while (old_it.next()) |entry| {
                    self.allocator.free(entry.key_ptr.*);
                    entry.value_ptr.deinit(self.allocator);
                }
                result.best_config.clearAndFree();

                // Copy new best config
                var it = config.iterator();
                while (it.next()) |entry| {
                    const key_copy = try self.allocator.dupe(u8, entry.key_ptr.*);
                    const value_copy = switch (entry.value_ptr.*) {
                        .float => |v| ConfigValue{ .float = v },
                        .int => |v| ConfigValue{ .int = v },
                        .string => |s| ConfigValue{ .string = try self.allocator.dupe(u8, s) },
                    };
                    try result.best_config.put(key_copy, value_copy);
                }

                result.best_score = score;
            }

            // Record in history
            const step = OptimizationStep{
                .config = config,
                .score = score,
                .allocator = self.allocator,
            };
            try result.history.append(self.allocator, step);
        }

        result.end_time = agktime.timestamp();
        return result;
    }

    pub fn deinit(self: *RandomSearchOptimizer) void {
        self.allocator.destroy(self);
    }
};

// Tests
test "SearchSpace continuous parameter" {
    const allocator = std.testing.allocator;

    const space = try SearchSpace.init(allocator);
    defer space.deinit();

    try space.addContinuous("temperature", 0.0, 1.0);

    try std.testing.expectEqual(@as(usize, 1), space.parameters.items.len);
    try std.testing.expectEqualStrings("temperature", space.parameters.items[0].name);
}

test "SearchSpace sample" {
    const allocator = std.testing.allocator;

    const space = try SearchSpace.init(allocator);
    defer space.deinit();

    try space.addContinuous("x", 0.0, 10.0);
    try space.addInteger("y", 1, 100);

    var config = try space.sample();
    defer {
        var it = config.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
            entry.value_ptr.deinit(allocator);
        }
        config.deinit();
    }

    try std.testing.expectEqual(@as(usize, 2), config.count());

    const x_val = config.get("x").?;
    try std.testing.expect(x_val == .float);
    try std.testing.expect(x_val.float >= 0.0 and x_val.float <= 10.0);

    const y_val = config.get("y").?;
    try std.testing.expect(y_val == .int);
    try std.testing.expect(y_val.int >= 1 and y_val.int <= 100);
}

test "SearchSpace validate" {
    const allocator = std.testing.allocator;

    const space = try SearchSpace.init(allocator);
    defer space.deinit();

    try space.addContinuous("x", 0.0, 10.0);

    var valid_config = std.StringHashMap(ConfigValue).init(allocator);
    defer {
        var it = valid_config.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
        }
        valid_config.deinit();
    }

    try valid_config.put(try allocator.dupe(u8, "x"), ConfigValue{ .float = 5.0 });

    try std.testing.expect(space.validate(valid_config));
}

test "RandomSearchOptimizer simple" {
    const allocator = std.testing.allocator;

    const space = try SearchSpace.init(allocator);
    defer space.deinit();

    try space.addContinuous("x", -10.0, 10.0);

    const optimizer = try RandomSearchOptimizer.init(allocator, space, false); // minimize
    defer optimizer.deinit();

    // Objective: minimize (x - 5)^2
    const objective = struct {
        fn eval(config: std.StringHashMap(ConfigValue)) !f64 {
            const x = config.get("x").?.float;
            const diff = x - 5.0;
            return diff * diff;
        }
    }.eval;

    var result = try optimizer.optimize(objective, 20);
    defer result.deinit();

    try std.testing.expectEqual(@as(usize, 20), result.n_iterations);
    try std.testing.expect(result.best_score < 100.0); // Should find something reasonable
}

test "OptimizationResult tracking" {
    const allocator = std.testing.allocator;

    const result = try OptimizationResult.init(allocator);
    defer result.deinit();

    result.n_iterations = 10;
    result.end_time = result.start_time + 5;

    try std.testing.expectEqual(@as(f64, 5.0), result.durationSecs());
}

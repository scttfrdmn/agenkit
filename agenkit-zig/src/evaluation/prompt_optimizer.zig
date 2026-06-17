/// Prompt optimization framework
///
/// This module provides automated prompt engineering with template variations
/// using grid search, random search, and genetic algorithms.
///
/// Key design principles:
/// - Template-based prompt generation
/// - Multiple optimization strategies
/// - Multi-metric evaluation
/// - AgentFactory pattern for creating agents from prompts
const std = @import("std");
const agktime = @import("../time_compat.zig");
const core = @import("core.zig");
const Allocator = std.mem.Allocator;

/// Optimization strategy
pub const OptimizationStrategy = enum {
    grid, // Exhaustive search
    random, // Random sampling
    genetic, // Genetic algorithm

    pub fn toString(self: OptimizationStrategy) []const u8 {
        return switch (self) {
            .grid => "Grid Search",
            .random => "Random Search",
            .genetic => "Genetic Algorithm",
        };
    }
};

/// Prompt configuration (variable assignments)
pub const PromptConfig = std.StringHashMap([]const u8);

/// Prompt evaluation scores
pub const PromptScores = std.StringHashMap(f64);

/// Optimization history entry
pub const OptimizationEntry = struct {
    config: PromptConfig,
    scores: PromptScores,
    allocator: Allocator,

    pub fn deinit(self: *OptimizationEntry) void {
        var config_it = self.config.iterator();
        while (config_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            self.allocator.free(entry.value_ptr.*);
        }
        self.config.deinit();

        var scores_it = self.scores.iterator();
        while (scores_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
        }
        self.scores.deinit();
    }
};

/// Prompt optimization result
pub const PromptOptimizationResult = struct {
    best_prompt: []const u8,
    best_config: PromptConfig,
    best_scores: PromptScores,
    history: std.ArrayList(OptimizationEntry),
    strategy_used: OptimizationStrategy,
    total_time_seconds: f64,
    allocator: Allocator,

    pub fn deinit(self: *PromptOptimizationResult) void {
        self.allocator.free(self.best_prompt);

        var config_it = self.best_config.iterator();
        while (config_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            self.allocator.free(entry.value_ptr.*);
        }
        self.best_config.deinit();

        var scores_it = self.best_scores.iterator();
        while (scores_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
        }
        self.best_scores.deinit();

        for (self.history.items) |*entry| {
            entry.deinit();
        }
        self.history.deinit();

        self.allocator.destroy(self);
    }
};

/// Agent factory function type
pub const AgentFactory = *const fn ([]const u8) anyerror!*anyopaque;

/// Evaluation function type
pub const EvaluationFn = *const fn (*anyopaque, []const core.TestCase) anyerror!PromptScores;

/// Prompt optimizer
pub const PromptOptimizer = struct {
    prompt_template: []const u8, // e.g., "You are a {role}. {instruction}"
    variations: std.StringHashMap(std.ArrayList([]const u8)), // Variable -> possible values
    agent_factory: AgentFactory,
    evaluation_fn: EvaluationFn,
    allocator: Allocator,
    rng: std.Random.DefaultPrng,

    pub fn init(
        allocator: Allocator,
        prompt_template: []const u8,
        variations: std.StringHashMap(std.ArrayList([]const u8)),
        agent_factory: AgentFactory,
        evaluation_fn: EvaluationFn,
    ) !*PromptOptimizer {
        const self = try allocator.create(PromptOptimizer);
        const seed = @as(u64, @intCast(agktime.timestamp()));
        self.* = PromptOptimizer{
            .prompt_template = try allocator.dupe(u8, prompt_template),
            .variations = variations,
            .agent_factory = agent_factory,
            .evaluation_fn = evaluation_fn,
            .allocator = allocator,
            .rng = std.Random.DefaultPrng.init(seed),
        };
        return self;
    }

    /// Optimize using grid search (exhaustive)
    pub fn optimizeGrid(
        self: *PromptOptimizer,
        test_cases: []const core.TestCase,
    ) !*PromptOptimizationResult {
        const start_time = agktime.timestamp();

        const result = try self.allocator.create(PromptOptimizationResult);
        result.* = PromptOptimizationResult{
            .best_prompt = try self.allocator.dupe(u8, ""),
            .best_config = PromptConfig.init(self.allocator),
            .best_scores = PromptScores.init(self.allocator),
            .history = std.ArrayList(OptimizationEntry).empty,
            .strategy_used = .grid,
            .total_time_seconds = 0.0,
            .allocator = self.allocator,
        };

        var best_avg_score: f64 = -std.math.inf(f64);

        // Generate all combinations
        var configs = try self.generateAllConfigs();
        defer {
            for (configs.items) |*config| {
                var it = config.iterator();
                while (it.next()) |entry| {
                    self.allocator.free(entry.key_ptr.*);
                    self.allocator.free(entry.value_ptr.*);
                }
                config.deinit();
            }
            configs.deinit(self.allocator);
        }

        for (configs.items) |*config| {
            const prompt = try self.formatPrompt(config);
            defer self.allocator.free(prompt);

            const scores = try self.evaluatePrompt(prompt, test_cases);
            const avg_score = try self.averageScore(&scores);

            // Update best if improved
            if (avg_score > best_avg_score) {
                self.allocator.free(result.best_prompt);
                result.best_prompt = try self.allocator.dupe(u8, prompt);

                // Clear old best config
                var old_it = result.best_config.iterator();
                while (old_it.next()) |entry| {
                    self.allocator.free(entry.key_ptr.*);
                    self.allocator.free(entry.value_ptr.*);
                }
                result.best_config.clearAndFree();

                // Copy new best config
                var it = config.iterator();
                while (it.next()) |entry| {
                    try result.best_config.put(
                        try self.allocator.dupe(u8, entry.key_ptr.*),
                        try self.allocator.dupe(u8, entry.value_ptr.*),
                    );
                }

                // Clear old best scores
                var old_scores_it = result.best_scores.iterator();
                while (old_scores_it.next()) |entry| {
                    self.allocator.free(entry.key_ptr.*);
                }
                result.best_scores.clearAndFree();

                // Copy new best scores
                var scores_it = scores.iterator();
                while (scores_it.next()) |entry| {
                    try result.best_scores.put(
                        try self.allocator.dupe(u8, entry.key_ptr.*),
                        entry.value_ptr.*,
                    );
                }

                best_avg_score = avg_score;
            }

            // Record in history
            var hist_config = PromptConfig.init(self.allocator);
            var it = config.iterator();
            while (it.next()) |entry| {
                try hist_config.put(
                    try self.allocator.dupe(u8, entry.key_ptr.*),
                    try self.allocator.dupe(u8, entry.value_ptr.*),
                );
            }

            var hist_scores = PromptScores.init(self.allocator);
            var scores_it = scores.iterator();
            while (scores_it.next()) |entry| {
                try hist_scores.put(
                    try self.allocator.dupe(u8, entry.key_ptr.*),
                    entry.value_ptr.*,
                );
            }

            try result.history.append(self.allocator, OptimizationEntry{
                .config = hist_config,
                .scores = hist_scores,
                .allocator = self.allocator,
            });

            // Clean up scores
            var cleanup_it = scores.iterator();
            while (cleanup_it.next()) |entry| {
                self.allocator.free(entry.key_ptr.*);
            }
            scores.deinit();
        }

        const end_time = agktime.timestamp();
        result.total_time_seconds = @as(f64, @floatFromInt(end_time - start_time));

        return result;
    }

    /// Optimize using random search
    pub fn optimizeRandom(
        self: *PromptOptimizer,
        test_cases: []const core.TestCase,
        n_samples: usize,
    ) !*PromptOptimizationResult {
        const start_time = agktime.timestamp();

        const result = try self.allocator.create(PromptOptimizationResult);
        result.* = PromptOptimizationResult{
            .best_prompt = try self.allocator.dupe(u8, ""),
            .best_config = PromptConfig.init(self.allocator),
            .best_scores = PromptScores.init(self.allocator),
            .history = std.ArrayList(OptimizationEntry).empty,
            .strategy_used = .random,
            .total_time_seconds = 0.0,
            .allocator = self.allocator,
        };

        var best_avg_score: f64 = -std.math.inf(f64);

        for (0..n_samples) |_| {
            var config = try self.sampleRandomConfig();
            defer {
                var it = config.iterator();
                while (it.next()) |entry| {
                    self.allocator.free(entry.key_ptr.*);
                    self.allocator.free(entry.value_ptr.*);
                }
                config.deinit();
            }

            const prompt = try self.formatPrompt(&config);
            defer self.allocator.free(prompt);

            const scores = try self.evaluatePrompt(prompt, test_cases);
            const avg_score = try self.averageScore(&scores);

            if (avg_score > best_avg_score) {
                self.allocator.free(result.best_prompt);
                result.best_prompt = try self.allocator.dupe(u8, prompt);

                var old_it = result.best_config.iterator();
                while (old_it.next()) |entry| {
                    self.allocator.free(entry.key_ptr.*);
                    self.allocator.free(entry.value_ptr.*);
                }
                result.best_config.clearAndFree();

                var it = config.iterator();
                while (it.next()) |entry| {
                    try result.best_config.put(
                        try self.allocator.dupe(u8, entry.key_ptr.*),
                        try self.allocator.dupe(u8, entry.value_ptr.*),
                    );
                }

                var old_scores_it = result.best_scores.iterator();
                while (old_scores_it.next()) |entry| {
                    self.allocator.free(entry.key_ptr.*);
                }
                result.best_scores.clearAndFree();

                var scores_it = scores.iterator();
                while (scores_it.next()) |entry| {
                    try result.best_scores.put(
                        try self.allocator.dupe(u8, entry.key_ptr.*),
                        entry.value_ptr.*,
                    );
                }

                best_avg_score = avg_score;
            }

            // Record history
            var hist_config = PromptConfig.init(self.allocator);
            var it = config.iterator();
            while (it.next()) |entry| {
                try hist_config.put(
                    try self.allocator.dupe(u8, entry.key_ptr.*),
                    try self.allocator.dupe(u8, entry.value_ptr.*),
                );
            }

            var hist_scores = PromptScores.init(self.allocator);
            var scores_it = scores.iterator();
            while (scores_it.next()) |entry| {
                try hist_scores.put(
                    try self.allocator.dupe(u8, entry.key_ptr.*),
                    entry.value_ptr.*,
                );
            }

            try result.history.append(self.allocator, OptimizationEntry{
                .config = hist_config,
                .scores = hist_scores,
                .allocator = self.allocator,
            });

            var cleanup_it = scores.iterator();
            while (cleanup_it.next()) |entry| {
                self.allocator.free(entry.key_ptr.*);
            }
            scores.deinit();
        }

        const end_time = agktime.timestamp();
        result.total_time_seconds = @as(f64, @floatFromInt(end_time - start_time));

        return result;
    }

    /// Optimize using genetic algorithm
    pub fn optimizeGenetic(
        self: *PromptOptimizer,
        test_cases: []const core.TestCase,
        population_size: usize,
        n_generations: usize,
        mutation_rate: f64,
    ) !*PromptOptimizationResult {
        const start_time = agktime.timestamp();

        const result = try self.allocator.create(PromptOptimizationResult);
        result.* = PromptOptimizationResult{
            .best_prompt = try self.allocator.dupe(u8, ""),
            .best_config = PromptConfig.init(self.allocator),
            .best_scores = PromptScores.init(self.allocator),
            .history = std.ArrayList(OptimizationEntry).empty,
            .strategy_used = .genetic,
            .total_time_seconds = 0.0,
            .allocator = self.allocator,
        };

        var best_avg_score: f64 = -std.math.inf(f64);

        // Initialize population
        var population = std.ArrayList(PromptConfig).empty;
        defer {
            for (population.items) |*config| {
                var it = config.iterator();
                while (it.next()) |entry| {
                    self.allocator.free(entry.key_ptr.*);
                    self.allocator.free(entry.value_ptr.*);
                }
                config.deinit();
            }
            population.deinit(self.allocator);
        }

        for (0..population_size) |_| {
            try population.append(self.allocator, try self.sampleRandomConfig());
        }

        // Evolutionary loop
        for (0..n_generations) |_| {
            // Evaluate population
            var fitness = std.ArrayList(f64).empty;
            defer fitness.deinit();

            for (population.items) |*config| {
                const prompt = try self.formatPrompt(config);
                defer self.allocator.free(prompt);

                const scores = try self.evaluatePrompt(prompt, test_cases);
                defer {
                    var it = scores.iterator();
                    while (it.next()) |entry| {
                        self.allocator.free(entry.key_ptr.*);
                    }
                    scores.deinit();
                }

                const avg_score = try self.averageScore(&scores);
                try fitness.append(avg_score);

                if (avg_score > best_avg_score) {
                    self.allocator.free(result.best_prompt);
                    result.best_prompt = try self.allocator.dupe(u8, prompt);

                    var old_it = result.best_config.iterator();
                    while (old_it.next()) |entry| {
                        self.allocator.free(entry.key_ptr.*);
                        self.allocator.free(entry.value_ptr.*);
                    }
                    result.best_config.clearAndFree();

                    var it = config.iterator();
                    while (it.next()) |entry| {
                        try result.best_config.put(
                            try self.allocator.dupe(u8, entry.key_ptr.*),
                            try self.allocator.dupe(u8, entry.value_ptr.*),
                        );
                    }

                    var scores_it = scores.iterator();
                    while (scores_it.next()) |entry| {
                        try result.best_scores.put(
                            try self.allocator.dupe(u8, entry.key_ptr.*),
                            entry.value_ptr.*,
                        );
                    }

                    best_avg_score = avg_score;
                }
            }

            // Selection and crossover
            var new_population = std.ArrayList(PromptConfig).empty;
            defer {
                for (new_population.items) |*config| {
                    var it = config.iterator();
                    while (it.next()) |entry| {
                        self.allocator.free(entry.key_ptr.*);
                        self.allocator.free(entry.value_ptr.*);
                    }
                    config.deinit();
                }
                new_population.deinit();
            }

            // Elitism: keep best
            const best_idx = self.findBestIndex(fitness.items);
            try new_population.append(try self.cloneConfig(&population.items[best_idx]));

            // Tournament selection and mutation
            while (new_population.items.len < population_size) {
                const parent_idx = try self.tournamentSelection(fitness.items);
                var child = try self.cloneConfig(&population.items[parent_idx]);

                // Mutation
                const random = self.rng.random();
                if (random.float(f64) < mutation_rate) {
                    try self.mutateConfig(&child);
                }

                try new_population.append(child);
            }

            // Replace population
            for (population.items) |*config| {
                var it = config.iterator();
                while (it.next()) |entry| {
                    self.allocator.free(entry.key_ptr.*);
                    self.allocator.free(entry.value_ptr.*);
                }
                config.deinit();
            }
            population.clearAndFree();

            for (new_population.items) |*config| {
                try population.append(try self.cloneConfig(config));
            }
        }

        const end_time = agktime.timestamp();
        result.total_time_seconds = @as(f64, @floatFromInt(end_time - start_time));

        return result;
    }

    /// Format prompt from configuration
    fn formatPrompt(self: *PromptOptimizer, config: *const PromptConfig) ![]const u8 {
        var result = std.ArrayList(u8).empty;
        defer result.deinit(self.allocator);

        var template_it = std.mem.tokenizeScalar(u8, self.prompt_template, '{');
        while (template_it.next()) |part| {
            if (std.mem.indexOf(u8, part, "}")) |close_idx| {
                const var_name = part[0..close_idx];
                const rest = part[close_idx + 1 ..];

                if (config.get(var_name)) |value| {
                    try result.appendSlice(self.allocator, value);
                } else {
                    try result.append(self.allocator, '{');
                    try result.appendSlice(self.allocator, var_name);
                    try result.append(self.allocator, '}');
                }
                try result.appendSlice(self.allocator, rest);
            } else {
                try result.appendSlice(self.allocator, part);
            }
        }

        return try result.toOwnedSlice(self.allocator);
    }

    /// Evaluate prompt with test cases
    fn evaluatePrompt(self: *PromptOptimizer, prompt: []const u8, test_cases: []const core.TestCase) !PromptScores {
        const agent = try self.agent_factory(prompt);
        return try self.evaluation_fn(agent, test_cases);
    }

    /// Calculate average score
    fn averageScore(self: *PromptOptimizer, scores: *const PromptScores) !f64 {
        _ = self;
        var sum: f64 = 0.0;
        var count: usize = 0;

        var it = scores.iterator();
        while (it.next()) |entry| {
            sum += entry.value_ptr.*;
            count += 1;
        }

        return if (count > 0) sum / @as(f64, @floatFromInt(count)) else 0.0;
    }

    /// Generate all possible configurations
    fn generateAllConfigs(self: *PromptOptimizer) !std.ArrayList(PromptConfig) {
        var result = std.ArrayList(PromptConfig).empty;

        var var_names = std.ArrayList([]const u8).empty;
        defer var_names.deinit();

        var var_options = std.ArrayList(std.ArrayList([]const u8)).empty;
        defer var_options.deinit();

        var it = self.variations.iterator();
        while (it.next()) |entry| {
            try var_names.append(entry.key_ptr.*);
            try var_options.append(entry.value_ptr.*);
        }

        // Generate combinations recursively
        var current_config = PromptConfig.init(self.allocator);
        defer current_config.deinit();

        try self.generateCombinations(&result, &current_config, var_names.items, var_options.items, 0);

        return result;
    }

    /// Recursive combination generation
    fn generateCombinations(
        self: *PromptOptimizer,
        result: *std.ArrayList(PromptConfig),
        current: *PromptConfig,
        var_names: []const []const u8,
        var_options: []const std.ArrayList([]const u8),
        depth: usize,
    ) !void {
        if (depth >= var_names.len) {
            // Copy current config to result
            var new_config = PromptConfig.init(self.allocator);
            var it = current.iterator();
            while (it.next()) |entry| {
                try new_config.put(
                    try self.allocator.dupe(u8, entry.key_ptr.*),
                    try self.allocator.dupe(u8, entry.value_ptr.*),
                );
            }
            try result.append(new_config);
            return;
        }

        const var_name = var_names[depth];
        const options = var_options[depth];

        for (options.items) |option| {
            try current.put(var_name, option);
            try self.generateCombinations(result, current, var_names, var_options, depth + 1);
        }
    }

    /// Sample random configuration
    fn sampleRandomConfig(self: *PromptOptimizer) !PromptConfig {
        var config = PromptConfig.init(self.allocator);
        const random = self.rng.random();

        var it = self.variations.iterator();
        while (it.next()) |entry| {
            const var_name = entry.key_ptr.*;
            const options = entry.value_ptr.*;

            if (options.items.len > 0) {
                const idx = random.intRangeLessThan(usize, 0, options.items.len);
                try config.put(
                    try self.allocator.dupe(u8, var_name),
                    try self.allocator.dupe(u8, options.items[idx]),
                );
            }
        }

        return config;
    }

    /// Clone configuration
    fn cloneConfig(self: *PromptOptimizer, config: *const PromptConfig) !PromptConfig {
        var new_config = PromptConfig.init(self.allocator);
        var it = config.iterator();
        while (it.next()) |entry| {
            try new_config.put(
                try self.allocator.dupe(u8, entry.key_ptr.*),
                try self.allocator.dupe(u8, entry.value_ptr.*),
            );
        }
        return new_config;
    }

    /// Mutate configuration
    fn mutateConfig(self: *PromptOptimizer, config: *PromptConfig) !void {
        const random = self.rng.random();

        // Pick random variable to mutate
        var var_names = std.ArrayList([]const u8).empty;
        defer var_names.deinit();

        var it = config.iterator();
        while (it.next()) |entry| {
            try var_names.append(entry.key_ptr.*);
        }

        if (var_names.items.len == 0) return;

        const var_idx = random.intRangeLessThan(usize, 0, var_names.items.len);
        const var_name = var_names.items[var_idx];

        if (self.variations.get(var_name)) |options| {
            if (options.items.len > 0) {
                const new_idx = random.intRangeLessThan(usize, 0, options.items.len);
                const old_value = config.get(var_name).?;
                self.allocator.free(old_value);
                try config.put(var_name, try self.allocator.dupe(u8, options.items[new_idx]));
            }
        }
    }

    /// Find best index in fitness array
    fn findBestIndex(self: *PromptOptimizer, fitness: []const f64) usize {
        _ = self;
        var best_idx: usize = 0;
        var best_fitness = fitness[0];

        for (fitness, 0..) |f, i| {
            if (f > best_fitness) {
                best_fitness = f;
                best_idx = i;
            }
        }

        return best_idx;
    }

    /// Tournament selection
    fn tournamentSelection(self: *PromptOptimizer, fitness: []const f64) !usize {
        const random = self.rng.random();
        const tournament_size = 3;

        var best_idx = random.intRangeLessThan(usize, 0, fitness.len);
        var best_fitness = fitness[best_idx];

        for (1..tournament_size) |_| {
            const idx = random.intRangeLessThan(usize, 0, fitness.len);
            if (fitness[idx] > best_fitness) {
                best_idx = idx;
                best_fitness = fitness[idx];
            }
        }

        return best_idx;
    }

    pub fn deinit(self: *PromptOptimizer) void {
        self.allocator.free(self.prompt_template);

        var it = self.variations.iterator();
        while (it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            for (entry.value_ptr.items) |value| {
                self.allocator.free(value);
            }
            entry.value_ptr.deinit(self.allocator);
        }
        self.variations.deinit();

        self.allocator.destroy(self);
    }
};

// Tests
test "OptimizationStrategy toString" {
    try std.testing.expectEqualStrings("Grid Search", OptimizationStrategy.grid.toString());
    try std.testing.expectEqualStrings("Random Search", OptimizationStrategy.random.toString());
    try std.testing.expectEqualStrings("Genetic Algorithm", OptimizationStrategy.genetic.toString());
}

test "PromptOptimizer formatPrompt" {
    const allocator = std.testing.allocator;

    var variations = std.StringHashMap(std.ArrayList([]const u8)).init(allocator);
    defer variations.deinit();

    const template = "You are a {role}. {instruction}";

    const factory = struct {
        fn create(_: []const u8) !*anyopaque {
            return undefined;
        }
    }.create;

    const eval_fn = struct {
        fn eval(_: *anyopaque, _: []const core.TestCase) !PromptScores {
            return PromptScores.init(std.testing.allocator);
        }
    }.eval;

    const optimizer = try PromptOptimizer.init(allocator, template, variations, factory, eval_fn);
    defer optimizer.deinit();

    var config = PromptConfig.init(allocator);
    defer {
        var it = config.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
            allocator.free(entry.value_ptr.*);
        }
        config.deinit();
    }

    try config.put(try allocator.dupe(u8, "role"), try allocator.dupe(u8, "assistant"));
    try config.put(try allocator.dupe(u8, "instruction"), try allocator.dupe(u8, "Be helpful"));

    const prompt = try optimizer.formatPrompt(&config);
    defer allocator.free(prompt);

    try std.testing.expectEqualStrings("You are a assistant. Be helpful", prompt);
}

test "PromptOptimizer sampleRandomConfig" {
    const allocator = std.testing.allocator;

    var variations = std.StringHashMap(std.ArrayList([]const u8)).init(allocator);

    var roles = std.ArrayList([]const u8).empty;
    try roles.append(allocator, try allocator.dupe(u8, "assistant"));
    try roles.append(allocator, try allocator.dupe(u8, "expert"));
    try variations.put(try allocator.dupe(u8, "role"), roles);

    const template = "You are a {role}";

    const factory = struct {
        fn create(_: []const u8) !*anyopaque {
            return undefined;
        }
    }.create;

    const eval_fn = struct {
        fn eval(_: *anyopaque, _: []const core.TestCase) !PromptScores {
            return PromptScores.init(std.testing.allocator);
        }
    }.eval;

    const optimizer = try PromptOptimizer.init(allocator, template, variations, factory, eval_fn);
    defer optimizer.deinit(); // This will free variations

    var config = try optimizer.sampleRandomConfig();
    defer {
        var it = config.iterator();
        while (it.next()) |entry| {
            allocator.free(entry.key_ptr.*);
            allocator.free(entry.value_ptr.*);
        }
        config.deinit();
    }

    try std.testing.expect(config.contains("role"));
}

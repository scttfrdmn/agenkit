/// Core evaluation types and interfaces
///
/// This module provides the foundation types for the evaluation framework,
/// including test cases, metrics, and evaluation results.
///
/// Key design principles:
/// - Explicit memory management with allocators
/// - Type-safe metric definitions
/// - Composable evaluation components
const std = @import("std");
const Agent = @import("../agent.zig").Agent;
const Message = @import("../message.zig").Message;
const Allocator = std.mem.Allocator;

/// Error types for evaluation operations
pub const EvaluationError = error{
    InvalidConfig,
    EmptyTestCases,
    MetricFailed,
    NoMetrics,
    AllocationFailed,
};

/// Test case for evaluating agents
pub const TestCase = struct {
    input: []const u8,
    expected: Expected,
    metadata: std.StringHashMap([]const u8),
    tags: []const []const u8,
    allocator: Allocator,

    pub const Expected = union(enum) {
        /// A fragment that must appear somewhere in the output, compared
        /// case-insensitively. Named `contains` rather than `exact` because that is
        /// what it means — see `validate` (#820).
        contains: []const u8,
        functional: *const fn ([]const u8) bool,
    };

    /// Create a new test case matched by a case-insensitive substring check.
    ///
    /// `expected` is a fragment to find in the output, not the whole output: an agent
    /// answering "The answer is 42." passes `expected = "42"`. This is the
    /// cross-language contract — see `validate`.
    pub fn initContains(
        allocator: Allocator,
        input: []const u8,
        expected: []const u8,
    ) !*TestCase {
        const self = try allocator.create(TestCase);
        self.* = TestCase{
            .input = try allocator.dupe(u8, input),
            .expected = .{ .contains = try allocator.dupe(u8, expected) },
            .metadata = std.StringHashMap([]const u8).init(allocator),
            .tags = &[_][]const u8{},
            .allocator = allocator,
        };
        return self;
    }

    /// Create a new test case with functional validation
    pub fn initFunctional(
        allocator: Allocator,
        input: []const u8,
        validator: *const fn ([]const u8) bool,
    ) !*TestCase {
        const self = try allocator.create(TestCase);
        self.* = TestCase{
            .input = try allocator.dupe(u8, input),
            .expected = .{ .functional = validator },
            .metadata = std.StringHashMap([]const u8).init(allocator),
            .tags = &[_][]const u8{},
            .allocator = allocator,
        };
        return self;
    }

    /// Validate output against expected result.
    ///
    /// A string `expected` is a **case-insensitive substring** of the output, matching
    /// Python (`expected.lower() in output.lower()`), Go, TypeScript, and every core's
    /// `AccuracyMetric`. This used to be `mem.eql`, which failed any realistic agent
    /// reply: `SimpleQABenchmark` expects "42", "Paris", "Not necessarily", and an
    /// agent answering "The answer is 42." scored zero (#820).
    ///
    /// Case-insensitive rather than exact-case because that is what the other cores
    /// default to; theirs is a `case_sensitive` toggle defaulting to false, and this
    /// type has no config to hang a toggle on. Callers needing case sensitivity or any
    /// other rule use `initFunctional`.
    pub fn validate(self: *const TestCase, output: []const u8) bool {
        return switch (self.expected) {
            .contains => |expected| containsIgnoreCase(output, expected),
            .functional => |validator| validator(output),
        };
    }

    /// Case-insensitive `indexOf`, allocation-free.
    ///
    /// `std.ascii.lowerString` needs a destination buffer, and `validate` has no
    /// allocator, so the comparison is done in place a byte at a time. ASCII-only, like
    /// the `lowerString`-based paths elsewhere in this subsystem.
    fn containsIgnoreCase(haystack: []const u8, needle: []const u8) bool {
        if (needle.len == 0) return true;
        if (needle.len > haystack.len) return false;

        var start: usize = 0;
        while (start + needle.len <= haystack.len) : (start += 1) {
            var i: usize = 0;
            while (i < needle.len) : (i += 1) {
                if (std.ascii.toLower(haystack[start + i]) != std.ascii.toLower(needle[i])) break;
            } else return true;
        }
        return false;
    }

    /// Add metadata to test case
    pub fn addMetadata(self: *TestCase, key: []const u8, value: []const u8) !void {
        const key_copy = try self.allocator.dupe(u8, key);
        const value_copy = try self.allocator.dupe(u8, value);
        try self.metadata.put(key_copy, value_copy);
    }

    /// Set tags for test case
    pub fn setTags(self: *TestCase, tags: []const []const u8) !void {
        const tags_copy = try self.allocator.alloc([]const u8, tags.len);
        for (tags, 0..) |tag, i| {
            tags_copy[i] = try self.allocator.dupe(u8, tag);
        }
        self.tags = tags_copy;
    }

    /// Clean up resources
    pub fn deinit(self: *TestCase) void {
        self.allocator.free(self.input);
        switch (self.expected) {
            .contains => |expected| self.allocator.free(expected),
            .functional => {},
        }

        var metadata_it = self.metadata.iterator();
        while (metadata_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
            self.allocator.free(entry.value_ptr.*);
        }
        self.metadata.deinit();

        for (self.tags) |tag| {
            self.allocator.free(tag);
        }
        if (self.tags.len > 0) {
            self.allocator.free(self.tags);
        }

        self.allocator.destroy(self);
    }
};

/// Error record for tracking evaluation failures
pub const ErrorRecord = struct {
    test_case_index: usize,
    error_type: []const u8,
    message: []const u8,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        index: usize,
        error_type: []const u8,
        message: []const u8,
    ) !*ErrorRecord {
        const self = try allocator.create(ErrorRecord);
        self.* = ErrorRecord{
            .test_case_index = index,
            .error_type = try allocator.dupe(u8, error_type),
            .message = try allocator.dupe(u8, message),
            .allocator = allocator,
        };
        return self;
    }

    pub fn deinit(self: *ErrorRecord) void {
        self.allocator.free(self.error_type);
        self.allocator.free(self.message);
        self.allocator.destroy(self);
    }
};

/// Result of evaluating an agent
pub const EvaluationResult = struct {
    session_id: []const u8,
    n_cases: usize,
    n_passed: usize,
    metrics: std.StringHashMap(f64),
    errors: std.ArrayList(*ErrorRecord),
    allocator: Allocator,

    pub fn init(allocator: Allocator, session_id: []const u8) !*EvaluationResult {
        const self = try allocator.create(EvaluationResult);
        self.* = EvaluationResult{
            .session_id = try allocator.dupe(u8, session_id),
            .n_cases = 0,
            .n_passed = 0,
            .metrics = std.StringHashMap(f64).init(allocator),
            .errors = std.ArrayList(*ErrorRecord).empty,
            .allocator = allocator,
        };
        return self;
    }

    /// Calculate success rate
    pub fn successRate(self: *const EvaluationResult) f64 {
        if (self.n_cases == 0) return 0.0;
        return @as(f64, @floatFromInt(self.n_passed)) / @as(f64, @floatFromInt(self.n_cases));
    }

    /// Add a metric value
    pub fn addMetric(self: *EvaluationResult, name: []const u8, value: f64) !void {
        const name_copy = try self.allocator.dupe(u8, name);
        try self.metrics.put(name_copy, value);
    }

    /// Get a metric value
    pub fn getMetric(self: *const EvaluationResult, name: []const u8) ?f64 {
        return self.metrics.get(name);
    }

    /// Add an error record
    pub fn addError(self: *EvaluationResult, error_record: *ErrorRecord) !void {
        try self.errors.append(self.allocator, error_record);
    }

    /// Clean up resources
    pub fn deinit(self: *EvaluationResult) void {
        self.allocator.free(self.session_id);

        var metrics_it = self.metrics.iterator();
        while (metrics_it.next()) |entry| {
            self.allocator.free(entry.key_ptr.*);
        }
        self.metrics.deinit();

        for (self.errors.items) |error_record| {
            error_record.deinit();
        }
        self.errors.deinit(self.allocator);

        self.allocator.destroy(self);
    }
};

/// Metric interface for evaluation
pub const Metric = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        name: *const fn (ptr: *anyopaque) []const u8,
        measure: *const fn (
            ptr: *anyopaque,
            agent: Agent,
            input: Message,
            output: Message,
            allocator: Allocator,
        ) anyerror!f64,
        aggregate: *const fn (
            ptr: *anyopaque,
            measurements: []const f64,
            allocator: Allocator,
        ) anyerror!std.StringHashMap(f64),
        deinit: *const fn (ptr: *anyopaque) void,
    };

    /// Get the metric's name
    pub fn name(self: Metric) []const u8 {
        return self.vtable.name(self.ptr);
    }

    /// Measure a single interaction
    pub fn measure(
        self: Metric,
        agent: Agent,
        input: Message,
        output: Message,
        allocator: Allocator,
    ) !f64 {
        return self.vtable.measure(self.ptr, agent, input, output, allocator);
    }

    /// Aggregate measurements into summary statistics
    pub fn aggregate(
        self: Metric,
        measurements: []const f64,
        allocator: Allocator,
    ) !std.StringHashMap(f64) {
        return self.vtable.aggregate(self.ptr, measurements, allocator);
    }

    /// Clean up resources
    pub fn deinit(self: Metric) void {
        self.vtable.deinit(self.ptr);
    }
};

/// Evaluator for running test cases against an agent
pub const Evaluator = struct {
    agent: Agent,
    metrics: []const Metric,
    allocator: Allocator,

    pub fn init(
        allocator: Allocator,
        agent: Agent,
        metrics: []const Metric,
    ) !*Evaluator {
        const self = try allocator.create(Evaluator);
        self.* = Evaluator{
            .agent = agent,
            .metrics = metrics,
            .allocator = allocator,
        };
        return self;
    }

    /// Evaluate agent on test cases
    pub fn evaluate(
        self: *Evaluator,
        test_cases: []const *TestCase,
        session_id: []const u8,
    ) !*EvaluationResult {
        if (test_cases.len == 0) return EvaluationError.EmptyTestCases;

        const result = try EvaluationResult.init(self.allocator, session_id);
        result.n_cases = test_cases.len;

        // Run each test case
        for (test_cases, 0..) |test_case, i| {
            const input_msg = Message.init(self.allocator, "user", test_case.input);
            defer input_msg.deinit();

            // Process with agent
            const agent_result = self.agent.process(input_msg) catch |err| {
                const error_record = try ErrorRecord.init(
                    self.allocator,
                    i,
                    "processing_error",
                    @errorName(err),
                );
                try result.addError(error_record);
                continue;
            };

            const output_msg = try agent_result.unwrap();
            defer output_msg.deinit();

            // Validate output
            const output_content = output_msg.content orelse "";
            const is_valid = test_case.validate(output_content);

            if (is_valid) {
                result.n_passed += 1;
            } else {
                const error_record = try ErrorRecord.init(
                    self.allocator,
                    i,
                    "validation_failed",
                    "Output did not match expected result",
                );
                try result.addError(error_record);
            }

            // Measure with metrics
            for (self.metrics) |metric| {
                const value = metric.measure(
                    self.agent,
                    input_msg,
                    output_msg,
                    self.allocator,
                ) catch |err| {
                    const error_record = try ErrorRecord.init(
                        self.allocator,
                        i,
                        "metric_error",
                        @errorName(err),
                    );
                    try result.addError(error_record);
                    continue;
                };

                // Store metric (keyed by metric name + test index for now)
                const metric_key = try std.fmt.allocPrint(
                    self.allocator,
                    "{s}_{d}",
                    .{ metric.name(), i },
                );
                try result.addMetric(metric_key, value);
            }
        }

        return result;
    }

    pub fn deinit(self: *Evaluator) void {
        self.allocator.destroy(self);
    }
};

// Tests
test "TestCase with substring match" {
    const allocator = std.testing.allocator;

    const test_case = try TestCase.initContains(allocator, "input", "expected");
    defer test_case.deinit();

    try std.testing.expect(test_case.validate("expected"));
    try std.testing.expect(!test_case.validate("wrong"));
}

test "TestCase matches an expected fragment inside agent prose" {
    const allocator = std.testing.allocator;

    // The reason this is a substring check and not `mem.eql`: benchmarks store the
    // *fragment* to look for, and agents answer in sentences. Under the old exact
    // comparison every one of these scored zero (#820).
    const test_case = try TestCase.initContains(allocator, "What is 15 + 27?", "42");
    defer test_case.deinit();

    try std.testing.expect(test_case.validate("42"));
    try std.testing.expect(test_case.validate("The answer is 42."));
    try std.testing.expect(test_case.validate("15 + 27 = 42, so the total is 42 items."));
    try std.testing.expect(!test_case.validate("The answer is 41."));

    // A prefix of the expected fragment is not a match — the needle must appear whole.
    const paris = try TestCase.initContains(allocator, "Capital of France?", "Paris");
    defer paris.deinit();
    try std.testing.expect(!paris.validate("Par"));
    try std.testing.expect(paris.validate("It is Paris, in northern France."));
}

test "TestCase substring match ignores case" {
    const allocator = std.testing.allocator;

    // Case-insensitive by default, matching Python's `expected.lower() in
    // output.lower()` and the `case_sensitive = false` default of every core's
    // AccuracyMetric.
    const test_case = try TestCase.initContains(allocator, "Capital of France?", "Paris");
    defer test_case.deinit();

    try std.testing.expect(test_case.validate("paris"));
    try std.testing.expect(test_case.validate("PARIS"));
    try std.testing.expect(test_case.validate("The capital is PaRiS."));
    try std.testing.expect(!test_case.validate("Lyon"));
}

test "TestCase substring match edge cases" {
    const allocator = std.testing.allocator;

    // An empty expected value matches anything: nothing was asked for. Guarding this
    // explicitly because the naive loop bound would read past the end otherwise.
    const empty = try TestCase.initContains(allocator, "input", "");
    defer empty.deinit();
    try std.testing.expect(empty.validate(""));
    try std.testing.expect(empty.validate("anything at all"));

    // An expected value longer than the output cannot match.
    const long = try TestCase.initContains(allocator, "input", "a very long expected value");
    defer long.deinit();
    try std.testing.expect(!long.validate("short"));
    try std.testing.expect(!long.validate(""));

    // A match at the very end of the output still counts — an off-by-one in the loop
    // bound would miss it.
    const tail = try TestCase.initContains(allocator, "input", "end");
    defer tail.deinit();
    try std.testing.expect(tail.validate("this is the end"));
}

test "TestCase with functional validator" {
    const allocator = std.testing.allocator;

    const validator = struct {
        fn isValid(output: []const u8) bool {
            return output.len > 5;
        }
    }.isValid;

    const test_case = try TestCase.initFunctional(allocator, "input", validator);
    defer test_case.deinit();

    try std.testing.expect(test_case.validate("hello world"));
    try std.testing.expect(!test_case.validate("hi"));
}

test "EvaluationResult success rate" {
    const allocator = std.testing.allocator;

    const result = try EvaluationResult.init(allocator, "test-session");
    defer result.deinit();

    result.n_cases = 10;
    result.n_passed = 7;

    try std.testing.expectEqual(@as(f64, 0.7), result.successRate());
}

test "EvaluationResult with metrics" {
    const allocator = std.testing.allocator;

    const result = try EvaluationResult.init(allocator, "test-session");
    defer result.deinit();

    try result.addMetric("accuracy", 0.85);
    try result.addMetric("latency", 123.45);

    try std.testing.expectEqual(@as(f64, 0.85), result.getMetric("accuracy").?);
    try std.testing.expectEqual(@as(f64, 123.45), result.getMetric("latency").?);
    try std.testing.expect(result.getMetric("nonexistent") == null);
}

/// Standardized benchmark suites for agent evaluation
///
/// This module provides pre-configured test suites for common evaluation
/// scenarios, from simple Q&A to extreme-scale (25M+ token) testing.
///
/// Key design principles:
/// - Reusable benchmark definitions
/// - Configurable difficulty levels
/// - Extreme-scale testing support
/// - Domain-specific test suites
const std = @import("std");
const core = @import("core.zig");
const Allocator = std.mem.Allocator;

/// Benchmark interface for test suite generation
pub const Benchmark = struct {
    ptr: *anyopaque,
    vtable: *const VTable,

    pub const VTable = struct {
        name: *const fn (ptr: *anyopaque) []const u8,
        description: *const fn (ptr: *anyopaque) []const u8,
        generateTestCases: *const fn (
            ptr: *anyopaque,
            allocator: Allocator,
        ) anyerror!std.ArrayList(*core.TestCase),
        deinit: *const fn (ptr: *anyopaque) void,
    };

    pub fn name(self: Benchmark) []const u8 {
        return self.vtable.name(self.ptr);
    }

    pub fn description(self: Benchmark) []const u8 {
        return self.vtable.description(self.ptr);
    }

    pub fn generateTestCases(
        self: Benchmark,
        allocator: Allocator,
    ) !std.ArrayList(*core.TestCase) {
        return self.vtable.generateTestCases(self.ptr, allocator);
    }

    pub fn deinit(self: Benchmark) void {
        self.vtable.deinit(self.ptr);
    }
};

/// Simple Q&A benchmark - basic reasoning and knowledge
pub const SimpleQABenchmark = struct {
    allocator: Allocator,

    pub fn init(allocator: Allocator) !*SimpleQABenchmark {
        const self = try allocator.create(SimpleQABenchmark);
        self.* = SimpleQABenchmark{
            .allocator = allocator,
        };
        return self;
    }

    pub fn asBenchmark(self: *SimpleQABenchmark) Benchmark {
        return Benchmark{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .description = descriptionImpl,
                .generateTestCases = generateImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "Simple Q&A";
    }

    fn descriptionImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "Basic reasoning and knowledge questions";
    }

    fn generateImpl(
        ptr: *anyopaque,
        allocator: Allocator,
    ) anyerror!std.ArrayList(*core.TestCase) {
        _ = ptr;
        var cases = std.ArrayList(*core.TestCase).empty;

        // Math questions
        const tc1 = try core.TestCase.initContains(allocator, "What is 15 + 27?", "42");
        try tc1.addMetadata("category", "math");
        try tc1.addMetadata("difficulty", "easy");
        try cases.append(allocator, tc1);

        const tc2 = try core.TestCase.initContains(allocator, "What is 144 ÷ 12?", "12");
        try tc2.addMetadata("category", "math");
        try tc2.addMetadata("difficulty", "easy");
        try cases.append(allocator, tc2);

        // Knowledge questions
        const tc3 = try core.TestCase.initContains(
            allocator,
            "What is the capital of France?",
            "Paris",
        );
        try tc3.addMetadata("category", "knowledge");
        try tc3.addMetadata("difficulty", "easy");
        try cases.append(allocator, tc3);

        // Reasoning questions
        const lengthValidator = struct {
            fn validate(output: []const u8) bool {
                return output.len >= 10 and output.len <= 200;
            }
        }.validate;

        const tc4 = try core.TestCase.initFunctional(
            allocator,
            "Explain why the sky is blue in one sentence.",
            lengthValidator,
        );
        try tc4.addMetadata("category", "reasoning");
        try tc4.addMetadata("difficulty", "medium");
        try cases.append(allocator, tc4);

        // Logic question
        const tc5 = try core.TestCase.initContains(
            allocator,
            "If all roses are flowers and some flowers fade quickly, can all roses fade quickly?",
            "Not necessarily",
        );
        try tc5.addMetadata("category", "logic");
        try tc5.addMetadata("difficulty", "medium");
        try cases.append(allocator, tc5);

        return cases;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *SimpleQABenchmark = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

/// Needle in haystack benchmark - information retrieval
pub const NeedleInHaystackBenchmark = struct {
    allocator: Allocator,
    context_length: usize,
    needle_count: usize,
    /// Owned `needle_in_haystack_{context_length}`, freed in deinit.
    ///
    /// Precomputed because the vtable's `name` returns `[]const u8` with no allocator to
    /// format with. The name is a registry key in some cores, so it has to encode
    /// `context_length` to match Python, Go, Rust, C++ and TypeScript — see #790.
    name: []const u8,

    pub fn init(
        allocator: Allocator,
        context_length: usize,
        needle_count: usize,
    ) !*NeedleInHaystackBenchmark {
        const name = try std.fmt.allocPrint(
            allocator,
            "needle_in_haystack_{d}",
            .{context_length},
        );
        errdefer allocator.free(name);

        const self = try allocator.create(NeedleInHaystackBenchmark);
        self.* = NeedleInHaystackBenchmark{
            .allocator = allocator,
            .context_length = context_length,
            .needle_count = needle_count,
            .name = name,
        };
        return self;
    }

    pub fn asBenchmark(self: *NeedleInHaystackBenchmark) Benchmark {
        return Benchmark{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .description = descriptionImpl,
                .generateTestCases = generateImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *NeedleInHaystackBenchmark = @ptrCast(@alignCast(ptr));
        return self.name;
    }

    fn descriptionImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "Information retrieval from large context";
    }

    fn generateImpl(
        ptr: *anyopaque,
        allocator: Allocator,
    ) anyerror!std.ArrayList(*core.TestCase) {
        const self: *NeedleInHaystackBenchmark = @ptrCast(@alignCast(ptr));
        var cases = std.ArrayList(*core.TestCase).empty;
        errdefer {
            for (cases.items) |tc| tc.deinit();
            cases.deinit(allocator);
        }

        // Generate haystack (filler content)
        var haystack = std.ArrayList(u8).empty;
        defer haystack.deinit(allocator);

        const filler = "This is irrelevant information that serves as distraction. ";
        const filler_reps = self.context_length / filler.len;

        for (0..filler_reps) |_| {
            try haystack.appendSlice(allocator, filler);
        }

        // Embed one distinct needle per requested count.
        //
        // Needles are generated rather than drawn from a fixed array: this core used
        // to hold three hardcoded strings and slice them to `@min(3, needle_count)`,
        // so any `needle_count` above 3 silently embedded only 3. The wording matches
        // Python, Go, Rust and TypeScript so the same benchmark measures the same
        // thing in every core (#799).
        for (0..self.needle_count) |i| {
            const needle = try std.fmt.allocPrint(
                allocator,
                "\nThe secret code for vault {d} is ALPHA-{d:0>4}-OMEGA.\n",
                .{ i, i },
            );
            defer allocator.free(needle);
            try haystack.appendSlice(allocator, needle);
        }

        const context_tokens_str = try std.fmt.allocPrint(allocator, "{d}", .{self.context_length});
        defer allocator.free(context_tokens_str);

        const total_needles_str = try std.fmt.allocPrint(allocator, "{d}", .{self.needle_count});
        defer allocator.free(total_needles_str);

        // One test case per needle, each asking for *that* needle's fact.
        //
        // The loop used to `break` on its first iteration, so `needle_count` bounded a
        // loop that ran once and the benchmark measured retrieval of a single fact
        // N-times-embedded rather than of N distinct facts.
        for (0..self.needle_count) |i| {
            const input = try std.fmt.allocPrint(
                allocator,
                "Context:\n{s}\n\nQuestion: What is the secret code for vault {d}?",
                .{ haystack.items, i },
            );
            defer allocator.free(input);

            const expected = try std.fmt.allocPrint(allocator, "ALPHA-{d:0>4}-OMEGA", .{i});
            defer allocator.free(expected);

            const tc = try core.TestCase.initContains(allocator, input, expected);
            errdefer tc.deinit();

            try tc.addMetadata("category", "retrieval");
            try tc.addMetadata("context_tokens", context_tokens_str);

            const position_str = try std.fmt.allocPrint(allocator, "{d}", .{i});
            defer allocator.free(position_str);
            try tc.addMetadata("needle_position", position_str);
            try tc.addMetadata("total_needles", total_needles_str);

            try cases.append(allocator, tc);
        }

        return cases;
    }

    /// Frees the benchmark and its owned `name`.
    ///
    /// Callers must use this rather than `allocator.destroy` directly, which would leak
    /// the name.
    pub fn deinit(self: *NeedleInHaystackBenchmark) void {
        self.allocator.free(self.name);
        self.allocator.destroy(self);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *NeedleInHaystackBenchmark = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

/// Extreme scale benchmark - 1M+ token contexts
pub const ExtremeScaleBenchmark = struct {
    allocator: Allocator,
    target_tokens: usize,

    pub fn init(allocator: Allocator, target_tokens: usize) !*ExtremeScaleBenchmark {
        const self = try allocator.create(ExtremeScaleBenchmark);
        self.* = ExtremeScaleBenchmark{
            .allocator = allocator,
            .target_tokens = target_tokens,
        };
        return self;
    }

    pub fn asBenchmark(self: *ExtremeScaleBenchmark) Benchmark {
        return Benchmark{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .description = descriptionImpl,
                .generateTestCases = generateImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "Extreme Scale";
    }

    fn descriptionImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "Tests at 1M-25M token scale";
    }

    fn generateImpl(
        ptr: *anyopaque,
        allocator: Allocator,
    ) anyerror!std.ArrayList(*core.TestCase) {
        const self: *ExtremeScaleBenchmark = @ptrCast(@alignCast(ptr));
        var cases = std.ArrayList(*core.TestCase).empty;

        // Generate massive context
        const tokens_per_char = 4; // Approximate
        const target_chars = self.target_tokens * tokens_per_char;

        const input = try std.fmt.allocPrint(
            allocator,
            "Process this large context of approximately {d} tokens. Summarize the key points.",
            .{self.target_tokens},
        );

        const validator = struct {
            fn validate(output: []const u8) bool {
                // Validate that output is reasonable length
                return output.len > 20 and output.len < 1000;
            }
        }.validate;

        const tc = try core.TestCase.initFunctional(allocator, input, validator);
        try tc.addMetadata("category", "extreme_scale");

        const target_tokens_str = try std.fmt.allocPrint(
            allocator,
            "{d}",
            .{self.target_tokens},
        );
        defer allocator.free(target_tokens_str);
        try tc.addMetadata("target_tokens", target_tokens_str);

        const target_chars_str = try std.fmt.allocPrint(
            allocator,
            "{d}",
            .{target_chars},
        );
        defer allocator.free(target_chars_str);
        try tc.addMetadata("target_chars", target_chars_str);

        try cases.append(allocator, tc);

        allocator.free(input);

        return cases;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ExtremeScaleBenchmark = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

/// Information retention benchmark - multi-turn fact recall
pub const InformationRetentionBenchmark = struct {
    allocator: Allocator,
    num_facts: usize,

    pub fn init(allocator: Allocator, num_facts: usize) !*InformationRetentionBenchmark {
        const self = try allocator.create(InformationRetentionBenchmark);
        self.* = InformationRetentionBenchmark{
            .allocator = allocator,
            .num_facts = num_facts,
        };
        return self;
    }

    pub fn asBenchmark(self: *InformationRetentionBenchmark) Benchmark {
        return Benchmark{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .description = descriptionImpl,
                .generateTestCases = generateImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "Information Retention";
    }

    fn descriptionImpl(ptr: *anyopaque) []const u8 {
        _ = ptr;
        return "Multi-turn conversations with fact recall";
    }

    fn generateImpl(
        ptr: *anyopaque,
        allocator: Allocator,
    ) anyerror!std.ArrayList(*core.TestCase) {
        const self: *InformationRetentionBenchmark = @ptrCast(@alignCast(ptr));
        var cases = std.ArrayList(*core.TestCase).empty;

        const facts = [_][]const u8{
            "The Eiffel Tower is 330 meters tall",
            "Water boils at 100 degrees Celsius",
            "The speed of light is 299,792 km/s",
            "Mount Everest is 8,849 meters high",
            "A year has 365.25 days on average",
        };

        // Create test cases that require recalling earlier facts
        for (facts[0..@min(facts.len, self.num_facts)], 0..) |fact, i| {
            const input = try std.fmt.allocPrint(
                allocator,
                "Fact {d}: {s}\n\nQuestion: What was fact {d}?",
                .{ i + 1, fact, i + 1 },
            );

            const validator = struct {
                fn validate(output: []const u8) bool {
                    return output.len > 10;
                }
            }.validate;

            const tc = try core.TestCase.initFunctional(allocator, input, validator);
            try tc.addMetadata("category", "retention");
            const fact_number_str = try std.fmt.allocPrint(
                allocator,
                "{d}",
                .{i + 1},
            );
            defer allocator.free(fact_number_str);
            try tc.addMetadata("fact_number", fact_number_str);
            try cases.append(allocator, tc);

            allocator.free(input);
        }

        return cases;
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *InformationRetentionBenchmark = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }
};

/// Benchmark suite - collection of benchmarks
pub const BenchmarkSuite = struct {
    name_str: []const u8,
    benchmarks: std.ArrayList(Benchmark),
    allocator: Allocator,

    pub fn init(allocator: Allocator, name_str: []const u8) !*BenchmarkSuite {
        const self = try allocator.create(BenchmarkSuite);
        self.* = BenchmarkSuite{
            .name_str = try allocator.dupe(u8, name_str),
            .benchmarks = std.ArrayList(Benchmark).empty,
            .allocator = allocator,
        };
        return self;
    }

    pub fn addBenchmark(self: *BenchmarkSuite, benchmark: Benchmark) !void {
        try self.benchmarks.append(self.allocator, benchmark);
    }

    pub fn generateAllTestCases(
        self: *const BenchmarkSuite,
        allocator: Allocator,
    ) !std.ArrayList(*core.TestCase) {
        var all_cases = std.ArrayList(*core.TestCase).empty;

        for (self.benchmarks.items) |benchmark| {
            var cases = try benchmark.generateTestCases(allocator);
            defer cases.deinit(allocator);

            for (cases.items) |case| {
                try all_cases.append(allocator, case);
            }
        }

        return all_cases;
    }

    /// Predefined standard suite
    pub fn standard(allocator: Allocator) !*BenchmarkSuite {
        const suite = try BenchmarkSuite.init(allocator, "Standard Suite");

        const simple_qa = try SimpleQABenchmark.init(allocator);
        try suite.addBenchmark(simple_qa.asBenchmark());

        return suite;
    }

    /// Predefined extreme scale suite
    pub fn extremeScale(allocator: Allocator) !*BenchmarkSuite {
        const suite = try BenchmarkSuite.init(allocator, "Extreme Scale Suite");

        const extreme_1m = try ExtremeScaleBenchmark.init(allocator, 1000000);
        try suite.addBenchmark(extreme_1m.asBenchmark());

        const extreme_10m = try ExtremeScaleBenchmark.init(allocator, 10000000);
        try suite.addBenchmark(extreme_10m.asBenchmark());

        return suite;
    }

    /// Predefined quick suite
    pub fn quick(allocator: Allocator) !*BenchmarkSuite {
        const suite = try BenchmarkSuite.init(allocator, "Quick Suite");

        const simple_qa = try SimpleQABenchmark.init(allocator);
        try suite.addBenchmark(simple_qa.asBenchmark());

        return suite;
    }

    pub fn deinit(self: *BenchmarkSuite) void {
        self.allocator.free(self.name_str);

        for (self.benchmarks.items) |benchmark| {
            benchmark.deinit();
        }
        self.benchmarks.deinit(self.allocator);

        self.allocator.destroy(self);
    }
};

// Tests
test "SimpleQABenchmark generates test cases" {
    const allocator = std.testing.allocator;

    const benchmark = try SimpleQABenchmark.init(allocator);
    defer allocator.destroy(benchmark);

    var cases = try benchmark.asBenchmark().generateTestCases(allocator);
    defer {
        for (cases.items) |tc| tc.deinit();
        cases.deinit(allocator);
    }

    try std.testing.expectEqual(@as(usize, 5), cases.items.len);

    // Check first case
    try std.testing.expectEqualStrings("What is 15 + 27?", cases.items[0].input);
}

test "SimpleQABenchmark cases accept realistic agent prose" {
    const allocator = std.testing.allocator;

    const benchmark = try SimpleQABenchmark.init(allocator);
    defer allocator.destroy(benchmark);

    var cases = try benchmark.asBenchmark().generateTestCases(allocator);
    defer {
        for (cases.items) |tc| tc.deinit();
        cases.deinit(allocator);
    }

    // This benchmark's expected values are fragments — "42", "12", "Paris", "Not
    // necessarily". Under the old `mem.eql` comparison an agent had to emit the fragment
    // and nothing else, so a correct agent answering in a sentence scored zero on four
    // of the five cases and the benchmark measured near-zero accuracy (#820).
    try std.testing.expect(cases.items[0].validate("15 + 27 = 42"));
    try std.testing.expect(!cases.items[0].validate("15 + 27 = 43"));

    try std.testing.expect(cases.items[1].validate("144 divided by 12 is 12."));

    try std.testing.expect(cases.items[2].validate("The capital of France is Paris."));
    try std.testing.expect(cases.items[2].validate("paris"));
    try std.testing.expect(!cases.items[2].validate("The capital of France is Lyon."));

    try std.testing.expect(cases.items[4].validate("No, not necessarily — some roses may not."));
}

test "NeedleInHaystackBenchmark configuration" {
    const allocator = std.testing.allocator;

    const benchmark = try NeedleInHaystackBenchmark.init(allocator, 1000, 3);
    defer benchmark.deinit();

    try std.testing.expectEqual(@as(usize, 1000), benchmark.context_length);
    try std.testing.expectEqual(@as(usize, 3), benchmark.needle_count);

    // Encodes context_length, matching Python, Go, Rust, C++ and TypeScript. This core
    // used to return a constant "Needle in Haystack" for every size (#790).
    try std.testing.expectEqualStrings("needle_in_haystack_1000", benchmark.asBenchmark().name());
}

test "NeedleInHaystackBenchmark generates one test case per needle" {
    const allocator = std.testing.allocator;

    // The count is the whole point of the parameter: `generateImpl` used to `break` on
    // its first iteration, so every needle_count produced exactly one case (#799). A
    // count above the 3 hardcoded needles this core used to hold is checked too, since
    // that array is what bounded the old loop.
    for ([_]usize{ 1, 3, 5 }) |needle_count| {
        const benchmark = try NeedleInHaystackBenchmark.init(allocator, 1000, needle_count);
        defer benchmark.deinit();

        var cases = try benchmark.asBenchmark().generateTestCases(allocator);
        defer {
            for (cases.items) |tc| tc.deinit();
            cases.deinit(allocator);
        }

        try std.testing.expectEqual(needle_count, cases.items.len);
    }
}

test "NeedleInHaystackBenchmark asks for each needle by its own vault" {
    const allocator = std.testing.allocator;

    const benchmark = try NeedleInHaystackBenchmark.init(allocator, 1000, 4);
    defer benchmark.deinit();

    var cases = try benchmark.asBenchmark().generateTestCases(allocator);
    defer {
        for (cases.items) |tc| tc.deinit();
        cases.deinit(allocator);
    }

    // Counting the cases is not enough: N copies of the *same* question would satisfy
    // that while still measuring one fact N times, which is what this core did. Each
    // case must name its own vault and expect its own code.
    for (cases.items, 0..) |tc, i| {
        const question = try std.fmt.allocPrint(allocator, "vault {d}?", .{i});
        defer allocator.free(question);
        try std.testing.expect(std.mem.indexOf(u8, tc.input, question) != null);

        const code = try std.fmt.allocPrint(allocator, "ALPHA-{d:0>4}-OMEGA", .{i});
        defer allocator.free(code);
        try std.testing.expectEqualStrings(code, tc.expected.contains);

        // Every needle is embedded in the shared context, so each case can be answered
        // from its own input.
        try std.testing.expect(std.mem.indexOf(u8, tc.input, code) != null);
    }
}

test "NeedleInHaystackBenchmark records needle position and total in metadata" {
    const allocator = std.testing.allocator;

    const benchmark = try NeedleInHaystackBenchmark.init(allocator, 1000, 3);
    defer benchmark.deinit();

    var cases = try benchmark.asBenchmark().generateTestCases(allocator);
    defer {
        for (cases.items) |tc| tc.deinit();
        cases.deinit(allocator);
    }

    for (cases.items, 0..) |tc, i| {
        const want_position = try std.fmt.allocPrint(allocator, "{d}", .{i});
        defer allocator.free(want_position);

        try std.testing.expectEqualStrings("retrieval", tc.metadata.get("category").?);
        try std.testing.expectEqualStrings("1000", tc.metadata.get("context_tokens").?);
        try std.testing.expectEqualStrings(want_position, tc.metadata.get("needle_position").?);
        try std.testing.expectEqualStrings("3", tc.metadata.get("total_needles").?);
    }
}

test "ExtremeScaleBenchmark target tokens" {
    const allocator = std.testing.allocator;

    const benchmark = try ExtremeScaleBenchmark.init(allocator, 1000000);
    defer allocator.destroy(benchmark);

    var cases = try benchmark.asBenchmark().generateTestCases(allocator);
    defer {
        for (cases.items) |tc| tc.deinit();
        cases.deinit(allocator);
    }

    try std.testing.expectEqual(@as(usize, 1), cases.items.len);
}

test "BenchmarkSuite standard" {
    const allocator = std.testing.allocator;

    const suite = try BenchmarkSuite.standard(allocator);
    defer suite.deinit();

    try std.testing.expectEqual(@as(usize, 1), suite.benchmarks.items.len);
}

test "BenchmarkSuite generateAllTestCases" {
    const allocator = std.testing.allocator;

    const suite = try BenchmarkSuite.init(allocator, "Test Suite");
    defer suite.deinit();

    const simple_qa = try SimpleQABenchmark.init(allocator);
    try suite.addBenchmark(simple_qa.asBenchmark());

    var all_cases = try suite.generateAllTestCases(allocator);
    defer {
        for (all_cases.items) |tc| tc.deinit();
        all_cases.deinit(allocator);
    }

    try std.testing.expect(all_cases.items.len > 0);
}

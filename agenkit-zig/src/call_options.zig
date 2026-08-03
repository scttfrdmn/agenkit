/// Per-call inference options for a single agent invocation.
///
/// The channel a caller uses to influence *how* one call runs, as opposed to
/// `Message`, which carries *what* the call is about. It exists because wrappers
/// need to vary inference settings per invocation of an agent they did not
/// construct: `SelfConsistencyAgent` samples the same prompt N times and takes a
/// majority vote, so sample diversity *is* the technique, and temperature is the
/// knob that produces it (#801).
///
/// Reached through the optional `Agent.processWith` capability rather than by
/// widening `process()`. Agents that do not provide it fall back to `process()`,
/// so nothing breaks — but a caller can ask with `Agent.supportsOptions()` when
/// it needs to know, and `SelfConsistencyAgent.temperatureApplied()` reports the
/// answer rather than leaving a dropped temperature invisible.
///
/// This type lives in core rather than under `adapter/`, matching Python's
/// `interfaces.py`, Go's `agenkit`, TypeScript's `src/core/call-options.ts`,
/// Rust's `src/core/call_options.rs` and C++'s `core/call_options.hpp`. Adapters
/// are built on core, not the other way round, and `agent.zig` needs this type.
/// `adapter/llm.zig` re-exports it so every adapter keeps its existing spelling.
///
/// Every field is optional and `null` means "unset", never a default. That
/// distinction is the whole point: an agent must be able to tell "the caller did
/// not ask for a temperature" from "the caller asked for 0.0" (greedy decoding),
/// which is a real request. Sending a defaulted value downstream would silently
/// override whatever the agent or provider was configured with.
///
/// Example:
/// ```zig
/// var options = CallOptions.init(allocator);
/// defer options.deinit();
/// try options.withTemperature(0.9);
///
/// const result = try agent.processWith(message, &options);
/// ```
const std = @import("std");
const Allocator = std.mem.Allocator;

/// Call options for LLM requests
pub const CallOptions = struct {
    /// Sampling temperature (typically 0.0-2.0)
    temperature: ?f64 = null,

    /// Maximum tokens to generate
    max_tokens: ?usize = null,

    /// Nucleus sampling parameter
    top_p: ?f64 = null,

    /// Provider-specific options
    extra: std.StringHashMap([]const u8),

    /// Initialize call options
    ///
    /// Allocation-free: `StringHashMap.init` only records the allocator, so an
    /// empty `CallOptions` costs nothing and a wrapper can build one per call to
    /// mean "no options" without a heap round trip.
    pub fn init(allocator: Allocator) CallOptions {
        return CallOptions{
            .extra = std.StringHashMap([]const u8).init(allocator),
        };
    }

    /// Set temperature (must be between 0 and 2)
    pub fn withTemperature(self: *CallOptions, temperature: f64) !void {
        if (temperature < 0.0 or temperature > 2.0) {
            return error.InvalidTemperature;
        }
        self.temperature = temperature;
    }

    /// Set max tokens (must be positive)
    pub fn withMaxTokens(self: *CallOptions, max_tokens: usize) !void {
        if (max_tokens == 0) {
            return error.InvalidMaxTokens;
        }
        self.max_tokens = max_tokens;
    }

    /// Set top_p (must be between 0 and 1)
    pub fn withTopP(self: *CallOptions, top_p: f64) !void {
        if (top_p < 0.0 or top_p > 1.0) {
            return error.InvalidTopP;
        }
        self.top_p = top_p;
    }

    /// Add provider-specific option
    pub fn withExtra(self: *CallOptions, key: []const u8, value: []const u8) !void {
        try self.extra.put(key, value);
    }

    /// Check every set field against its documented range.
    ///
    /// The `with*` builders validate on the way in, but the fields are public,
    /// so struct-literal construction (`.{ .temperature = 9.0, .extra = ... }`)
    /// bypasses them entirely. This is the guard on that path, and it is the one
    /// callers who accept a temperature from configuration should use — it keeps
    /// the bounds in a single place so a technique's validation cannot drift
    /// apart from the options' own.
    pub fn validate(self: CallOptions) error{ InvalidTemperature, InvalidMaxTokens, InvalidTopP }!void {
        if (self.temperature) |t| {
            if (t < 0.0 or t > 2.0) return error.InvalidTemperature;
        }
        if (self.max_tokens) |m| {
            if (m == 0) return error.InvalidMaxTokens;
        }
        if (self.top_p) |p| {
            if (p < 0.0 or p > 1.0) return error.InvalidTopP;
        }
    }

    /// Report whether any option is set.
    ///
    /// Lets a caller skip the `processWith` path entirely when it has nothing to
    /// say, rather than handing an agent an all-null options object and making it
    /// look like a request that was made.
    pub fn isEmpty(self: CallOptions) bool {
        return self.temperature == null and
            self.max_tokens == null and
            self.top_p == null and
            self.extra.count() == 0;
    }

    /// Overlay `override`'s set fields onto a copy of `self`.
    ///
    /// Merged field by field, not by wholesale replacement. A `null` field in
    /// `override` means "did not ask", not "clear it" — replacing the struct
    /// would let a caller forwarding an optional variable erase the base's
    /// configuration. This is what lets `SelfConsistencyAgent` impose its own
    /// temperature while every other option a caller set passes through
    /// untouched.
    ///
    /// **The result borrows one input's `extra` map and must not be deinited.**
    /// Merging two maps would require an allocator and a failure path for what
    /// is otherwise an infallible field copy; instead the non-empty map wins by
    /// reference, and ownership stays with whichever input it came from. Both
    /// inputs must outlive the result.
    pub fn merge(self: CallOptions, override: CallOptions) CallOptions {
        return CallOptions{
            .temperature = override.temperature orelse self.temperature,
            .max_tokens = override.max_tokens orelse self.max_tokens,
            .top_p = override.top_p orelse self.top_p,
            .extra = if (override.extra.count() > 0) override.extra else self.extra,
        };
    }

    /// Clean up resources
    pub fn deinit(self: *CallOptions) void {
        self.extra.deinit();
    }
};

// ============================================================================
// Tests
// ============================================================================

test "CallOptions initialization" {
    const allocator = std.testing.allocator;

    var options = CallOptions.init(allocator);
    defer options.deinit();

    try std.testing.expect(options.temperature == null);
    try std.testing.expect(options.max_tokens == null);
    try std.testing.expect(options.top_p == null);
}

test "CallOptions with values" {
    const allocator = std.testing.allocator;

    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(0.7);
    try options.withMaxTokens(1024);
    try options.withTopP(0.9);

    try std.testing.expectEqual(@as(f64, 0.7), options.temperature.?);
    try std.testing.expectEqual(@as(usize, 1024), options.max_tokens.?);
    try std.testing.expectEqual(@as(f64, 0.9), options.top_p.?);
}

test "CallOptions with extra" {
    const allocator = std.testing.allocator;

    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withExtra("frequency_penalty", "0.5");
    try options.withExtra("presence_penalty", "0.3");

    try std.testing.expect(options.extra.contains("frequency_penalty"));
    try std.testing.expect(options.extra.contains("presence_penalty"));
}

// ============================================================================
// Temperature Validation Tests
// ============================================================================

test "CallOptions valid temperature 0" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(0.0);
    try std.testing.expectEqual(@as(f64, 0.0), options.temperature.?);
}

test "CallOptions valid temperature 1" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(1.0);
    try std.testing.expectEqual(@as(f64, 1.0), options.temperature.?);
}

test "CallOptions valid temperature 2" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(2.0);
    try std.testing.expectEqual(@as(f64, 2.0), options.temperature.?);
}

test "CallOptions invalid temperature negative" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTemperature(-0.5);
    try std.testing.expectError(error.InvalidTemperature, result);
}

test "CallOptions invalid temperature too high" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTemperature(3.0);
    try std.testing.expectError(error.InvalidTemperature, result);
}

// ============================================================================
// Max Tokens Validation Tests
// ============================================================================

test "CallOptions valid max_tokens" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withMaxTokens(1024);
    try std.testing.expectEqual(@as(usize, 1024), options.max_tokens.?);
}

test "CallOptions invalid max_tokens zero" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withMaxTokens(0);
    try std.testing.expectError(error.InvalidMaxTokens, result);
}

// ============================================================================
// Top P Validation Tests
// ============================================================================

test "CallOptions valid top_p" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTopP(0.9);
    try std.testing.expectEqual(@as(f64, 0.9), options.top_p.?);
}

test "CallOptions invalid top_p negative" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTopP(-0.1);
    try std.testing.expectError(error.InvalidTopP, result);
}

test "CallOptions invalid top_p too high" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    const result = options.withTopP(1.5);
    try std.testing.expectError(error.InvalidTopP, result);
}

// ============================================================================
// Boundary Value Tests
// ============================================================================

test "CallOptions boundary temperature exactly 0" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(0.0);
    try std.testing.expectEqual(@as(f64, 0.0), options.temperature.?);
}

test "CallOptions boundary temperature exactly 2" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTemperature(2.0);
    try std.testing.expectEqual(@as(f64, 2.0), options.temperature.?);
}

test "CallOptions boundary max_tokens exactly 1" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withMaxTokens(1);
    try std.testing.expectEqual(@as(usize, 1), options.max_tokens.?);
}

test "CallOptions boundary top_p exactly 0" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTopP(0.0);
    try std.testing.expectEqual(@as(f64, 0.0), options.top_p.?);
}

test "CallOptions boundary top_p exactly 1" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.withTopP(1.0);
    try std.testing.expectEqual(@as(f64, 1.0), options.top_p.?);
}

// ============================================================================
// validate() — the struct-literal path the builders cannot guard
// ============================================================================

test "CallOptions validate accepts an all-unset options object" {
    const allocator = std.testing.allocator;
    var options = CallOptions.init(allocator);
    defer options.deinit();

    try options.validate();
}

test "CallOptions validate rejects what the builders reject" {
    const allocator = std.testing.allocator;

    // The fields are public, so this bypasses withTemperature entirely — which
    // is exactly why validate() exists.
    for ([_]struct { opts: CallOptions, want: anyerror }{
        .{ .opts = .{ .temperature = -0.1, .extra = std.StringHashMap([]const u8).init(allocator) }, .want = error.InvalidTemperature },
        .{ .opts = .{ .temperature = 2.1, .extra = std.StringHashMap([]const u8).init(allocator) }, .want = error.InvalidTemperature },
        .{ .opts = .{ .max_tokens = 0, .extra = std.StringHashMap([]const u8).init(allocator) }, .want = error.InvalidMaxTokens },
        .{ .opts = .{ .top_p = -0.1, .extra = std.StringHashMap([]const u8).init(allocator) }, .want = error.InvalidTopP },
        .{ .opts = .{ .top_p = 1.1, .extra = std.StringHashMap([]const u8).init(allocator) }, .want = error.InvalidTopP },
    }) |case| {
        var opts = case.opts;
        defer opts.deinit();
        try std.testing.expectError(case.want, opts.validate());
    }
}

test "CallOptions validate accepts the boundaries" {
    const allocator = std.testing.allocator;

    // 0.0 and 2.0 are valid temperatures, and 0.0 is a real request (greedy
    // decoding), not an absent one.
    var opts = CallOptions{
        .temperature = 0.0,
        .max_tokens = 1,
        .top_p = 0.0,
        .extra = std.StringHashMap([]const u8).init(allocator),
    };
    defer opts.deinit();
    try opts.validate();

    opts.temperature = 2.0;
    opts.top_p = 1.0;
    try opts.validate();
}

// ============================================================================
// isEmpty()
// ============================================================================

test "CallOptions isEmpty is true only when nothing was asked for" {
    const allocator = std.testing.allocator;

    var options = CallOptions.init(allocator);
    defer options.deinit();
    try std.testing.expect(options.isEmpty());

    // temperature 0.0 is a request for greedy decoding, not an absent option.
    try options.withTemperature(0.0);
    try std.testing.expect(!options.isEmpty());
}

test "CallOptions isEmpty accounts for each field" {
    const allocator = std.testing.allocator;

    {
        var options = CallOptions.init(allocator);
        defer options.deinit();
        try options.withMaxTokens(1);
        try std.testing.expect(!options.isEmpty());
    }
    {
        var options = CallOptions.init(allocator);
        defer options.deinit();
        try options.withTopP(0.5);
        try std.testing.expect(!options.isEmpty());
    }
    {
        // A provider-specific option alone is still something the caller asked
        // for; treating extra-only options as empty would silently drop them.
        var options = CallOptions.init(allocator);
        defer options.deinit();
        try options.withExtra("frequency_penalty", "0.5");
        try std.testing.expect(!options.isEmpty());
    }
}

// ============================================================================
// merge() — field-by-field, never wholesale
// ============================================================================

test "CallOptions merge lets the override win per field" {
    const allocator = std.testing.allocator;

    var base = CallOptions.init(allocator);
    defer base.deinit();
    try base.withTemperature(0.2);
    try base.withMaxTokens(100);

    var override = CallOptions.init(allocator);
    defer override.deinit();
    try override.withTemperature(0.9);

    const merged = base.merge(override);

    try std.testing.expectEqual(@as(f64, 0.9), merged.temperature.?);
    // max_tokens was unset in the override, which means "did not ask" — not
    // "clear it". Replacing the struct wholesale would have dropped it.
    try std.testing.expectEqual(@as(usize, 100), merged.max_tokens.?);
    try std.testing.expect(merged.top_p == null);
}

test "CallOptions merge treats an override temperature of 0 as a real request" {
    const allocator = std.testing.allocator;

    var base = CallOptions.init(allocator);
    defer base.deinit();
    try base.withTemperature(1.5);

    var override = CallOptions.init(allocator);
    defer override.deinit();
    try override.withTemperature(0.0);

    // `orelse` on an optional distinguishes 0.0 from unset; a truthiness test
    // would let the base's 1.5 survive and silently override greedy decoding.
    const merged = base.merge(override);
    try std.testing.expectEqual(@as(f64, 0.0), merged.temperature.?);
}

test "CallOptions merge keeps the base's extra when the override has none" {
    const allocator = std.testing.allocator;

    var base = CallOptions.init(allocator);
    defer base.deinit();
    try base.withExtra("frequency_penalty", "0.5");

    var override = CallOptions.init(allocator);
    defer override.deinit();
    try override.withTemperature(0.9);

    // The merged view borrows base's map; it is not deinited here, and both
    // inputs outlive it.
    const merged = base.merge(override);
    try std.testing.expectEqual(@as(usize, 1), merged.extra.count());
    try std.testing.expectEqualStrings("0.5", merged.extra.get("frequency_penalty").?);
    try std.testing.expectEqual(@as(f64, 0.9), merged.temperature.?);
}

test "CallOptions merge of two empty option sets is still empty" {
    const allocator = std.testing.allocator;

    var base = CallOptions.init(allocator);
    defer base.deinit();
    var override = CallOptions.init(allocator);
    defer override.deinit();

    try std.testing.expect(base.merge(override).isEmpty());
}

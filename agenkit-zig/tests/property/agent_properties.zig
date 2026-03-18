/// Property-based tests for Agent interface and composition patterns
///
/// Verifies invariants of EchoAgent, FailingAgent, and SequentialAgent
/// using random inputs. Each property runs 50 times.
///
/// Run with: zig build test

const std = @import("std");
const testing = std.testing;
const agenkit = @import("agenkit");
const Agent = agenkit.Agent;
const AgentError = agenkit.AgentError;
const Message = agenkit.Message;
const Role = agenkit.Role;
const Result = agenkit.Result;
const EchoAgent = agenkit.EchoAgent;
const SequentialAgent = agenkit.patterns.SequentialAgent;

const framework = @import("framework.zig");

const ITERATIONS: u32 = 50;
const SEED: u64 = 0xfeedface;

// ---------------------------------------------------------------------------
// Property 1: EchoAgent always returns Role.assistant regardless of input role
// ---------------------------------------------------------------------------

fn propEchoAgentReturnsAssistantRole(rng: std.Random, allocator: std.mem.Allocator) !void {
    const input_role = framework.randomRole(rng);

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var msg = try Message.withText(allocator, input_role, "hello");
    defer msg.deinit();

    const result = try echo.agent().process(msg);
    try testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    try testing.expectEqual(Role.assistant, response.role);
}

test "echo_agent_returns_assistant_role" {
    try framework.runProperty(
        "echo_agent_returns_assistant_role",
        ITERATIONS,
        SEED,
        testing.allocator,
        propEchoAgentReturnsAssistantRole,
    );
}

// ---------------------------------------------------------------------------
// Property 2: EchoAgent output content equals input content
// ---------------------------------------------------------------------------

fn propEchoAgentContentPreserved(rng: std.Random, allocator: std.mem.Allocator) !void {
    const text = try framework.randomText(rng, allocator, 128);
    defer allocator.free(text);

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var msg = try Message.withText(allocator, .user, text);
    defer msg.deinit();

    const result = try echo.agent().process(msg);
    try testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    const out = try response.contentAsText();
    try testing.expectEqualStrings(text, out);
}

test "echo_agent_content_preserved" {
    try framework.runProperty(
        "echo_agent_content_preserved",
        ITERATIONS,
        SEED + 1,
        testing.allocator,
        propEchoAgentContentPreserved,
    );
}

// ---------------------------------------------------------------------------
// Property 3: agent.name() returns identical bytes on repeated calls
// ---------------------------------------------------------------------------

fn propAgentNameIsStable(_: std.Random, allocator: std.mem.Allocator) !void {
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    const ag = echo.agent();
    const name1 = ag.name();
    const name2 = ag.name();
    const name3 = ag.name();

    try testing.expectEqualStrings(name1, name2);
    try testing.expectEqualStrings(name2, name3);
}

test "agent_name_is_stable" {
    try framework.runProperty(
        "agent_name_is_stable",
        ITERATIONS,
        SEED + 2,
        testing.allocator,
        propAgentNameIsStable,
    );
}

// ---------------------------------------------------------------------------
// Property 4: SequentialAgent(echo, echo) output equals input content
// ---------------------------------------------------------------------------

fn propSequentialPreservesFinalContent(rng: std.Random, allocator: std.mem.Allocator) !void {
    const text = try framework.randomText(rng, allocator, 64);
    defer allocator.free(text);

    var echo1 = try EchoAgent.init(allocator);
    var echo2 = try EchoAgent.init(allocator);
    // SequentialAgent does NOT own inner agents, so deinit them separately
    defer echo1.agent().deinit();
    defer echo2.agent().deinit();

    const agents = [_]Agent{ echo1.agent(), echo2.agent() };
    var seq = try SequentialAgent.init(allocator, &agents, "test-seq");
    defer seq.agent().deinit();

    var msg = try Message.withText(allocator, .user, text);
    defer msg.deinit();

    const result = try seq.agent().process(msg);
    try testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    const out = try response.contentAsText();
    try testing.expectEqualStrings(text, out);
}

test "sequential_preserves_final_content" {
    try framework.runProperty(
        "sequential_preserves_final_content",
        ITERATIONS,
        SEED + 3,
        testing.allocator,
        propSequentialPreservesFinalContent,
    );
}

// ---------------------------------------------------------------------------
// Property 5: empty-string message passes through SequentialAgent unchanged
// ---------------------------------------------------------------------------

fn propSequentialEmptyInputPassthrough(_: std.Random, allocator: std.mem.Allocator) !void {
    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    const agents = [_]Agent{echo.agent()};
    var seq = try SequentialAgent.init(allocator, &agents, "passthrough");
    defer seq.agent().deinit();

    var msg = try Message.withText(allocator, .user, "");
    defer msg.deinit();

    const result = try seq.agent().process(msg);
    try testing.expect(result.isOk());

    var response = try result.unwrap();
    defer response.deinit();

    const out = try response.contentAsText();
    try testing.expectEqualStrings("", out);
}

test "sequential_empty_input_passthrough" {
    try framework.runProperty(
        "sequential_empty_input_passthrough",
        ITERATIONS,
        SEED + 4,
        testing.allocator,
        propSequentialEmptyInputPassthrough,
    );
}

// ---------------------------------------------------------------------------
// Property 6: FailingAgent.process always returns .err
// ---------------------------------------------------------------------------

fn propFailingAgentAlwaysErrors(rng: std.Random, allocator: std.mem.Allocator) !void {
    const role = framework.randomRole(rng);
    const text = try framework.randomText(rng, allocator, 32);
    defer allocator.free(text);

    var failing = try framework.FailingAgent.init(allocator);
    defer failing.deinit();

    var msg = try Message.withText(allocator, role, text);
    defer msg.deinit();

    const outcome = failing.agent().process(msg);
    if (outcome) |res| {
        // Result type — must be .err
        try testing.expect(res.isErr());
    } else |_| {
        // Direct error — also acceptable
    }
}

test "failing_agent_always_errors" {
    try framework.runProperty(
        "failing_agent_always_errors",
        ITERATIONS,
        SEED + 5,
        testing.allocator,
        propFailingAgentAlwaysErrors,
    );
}

// ---------------------------------------------------------------------------
// Property 7: Result discriminant integrity — .ok is never also .err
// ---------------------------------------------------------------------------

fn propResultOkNotErr(rng: std.Random, allocator: std.mem.Allocator) !void {
    const text = try framework.randomText(rng, allocator, 16);
    defer allocator.free(text);

    const msg = try Message.withText(allocator, .user, text);
    const ok_result = Result{ .ok = msg };

    try testing.expect(ok_result.isOk());
    try testing.expect(!ok_result.isErr());

    // Consume/deinit the message via unwrap
    var unwrapped = try ok_result.unwrap();
    unwrapped.deinit();

    const err_result = Result{ .err = AgentError.ProcessingFailed };
    try testing.expect(!err_result.isOk());
    try testing.expect(err_result.isErr());
}

test "result_ok_not_err" {
    try framework.runProperty(
        "result_ok_not_err",
        ITERATIONS,
        SEED + 6,
        testing.allocator,
        propResultOkNotErr,
    );
}

// ---------------------------------------------------------------------------
// Property 8: agent deinit is safe after process completes
// ---------------------------------------------------------------------------

fn propAgentDeinitIsSafe(rng: std.Random, allocator: std.mem.Allocator) !void {
    const text = try framework.randomText(rng, allocator, 32);
    defer allocator.free(text);

    var echo = try EchoAgent.init(allocator);

    var msg = try Message.withText(allocator, .user, text);
    defer msg.deinit();

    const result = try echo.agent().process(msg);
    if (result.isOk()) {
        var response = try result.unwrap();
        response.deinit();
    }

    // deinit must not panic
    echo.agent().deinit();
}

test "agent_deinit_is_safe" {
    try framework.runProperty(
        "agent_deinit_is_safe",
        ITERATIONS,
        SEED + 7,
        testing.allocator,
        propAgentDeinitIsSafe,
    );
}

// ---------------------------------------------------------------------------
// Property 9: input Message role is not mutated as a side effect of process()
// ---------------------------------------------------------------------------

fn propMessageRoleNotMutatedByAgent(rng: std.Random, allocator: std.mem.Allocator) !void {
    const role = framework.randomRole(rng);

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var msg = try Message.withText(allocator, role, "test");
    defer msg.deinit();

    const result = try echo.agent().process(msg);
    if (result.isOk()) {
        var response = try result.unwrap();
        defer response.deinit();
    }

    // Input message role must be unchanged after process()
    try testing.expectEqual(role, msg.role);
}

test "message_role_not_mutated_by_agent" {
    try framework.runProperty(
        "message_role_not_mutated_by_agent",
        ITERATIONS,
        SEED + 8,
        testing.allocator,
        propMessageRoleNotMutatedByAgent,
    );
}

// ---------------------------------------------------------------------------
// Property 10: multiple process calls with same input produce same output
// ---------------------------------------------------------------------------

fn propMultipleProcessCallsConsistent(rng: std.Random, allocator: std.mem.Allocator) !void {
    const text = try framework.randomText(rng, allocator, 64);
    defer allocator.free(text);

    var echo = try EchoAgent.init(allocator);
    defer echo.agent().deinit();

    var msg = try Message.withText(allocator, .user, text);
    defer msg.deinit();

    const result1 = try echo.agent().process(msg);
    try testing.expect(result1.isOk());
    var response1 = try result1.unwrap();
    defer response1.deinit();

    const result2 = try echo.agent().process(msg);
    try testing.expect(result2.isOk());
    var response2 = try result2.unwrap();
    defer response2.deinit();

    const out1 = try response1.contentAsText();
    const out2 = try response2.contentAsText();

    try testing.expectEqualStrings(out1, out2);
    try testing.expectEqual(response1.role, response2.role);
}

test "multiple_process_calls_consistent" {
    try framework.runProperty(
        "multiple_process_calls_consistent",
        ITERATIONS,
        SEED + 9,
        testing.allocator,
        propMultipleProcessCallsConsistent,
    );
}

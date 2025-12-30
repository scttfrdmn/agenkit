//! Fallback Pattern Example
//!
//! This example demonstrates the Fallback pattern for automatic failover
//! across multiple agents. Agents are tried in sequence until one succeeds.
//!
//! Build: zig build
//! Run: zig build run-fallback

const std = @import("std");
const agenkit = @import("agenkit");

const Agent = agenkit.Agent;
const Message = agenkit.Message;
const FallbackAgent = agenkit.patterns.FallbackAgent;

/// Mock agent that can be configured to succeed or fail
const MockServiceAgent = struct {
    allocator: std.mem.Allocator,
    name: []const u8,
    service_type: []const u8,
    should_fail: bool,

    pub fn init(allocator: std.mem.Allocator, name: []const u8, service_type: []const u8, should_fail: bool) !*MockServiceAgent {
        const self = try allocator.create(MockServiceAgent);
        self.* = .{
            .allocator = allocator,
            .name = try allocator.dupe(u8, name),
            .service_type = try allocator.dupe(u8, service_type),
            .should_fail = should_fail,
        };
        return self;
    }

    pub fn agent(self: *MockServiceAgent) Agent {
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

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *MockServiceAgent = @ptrCast(@alignCast(ptr));
        return self.name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const self: *MockServiceAgent = @ptrCast(@alignCast(ptr));
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = try allocator.dupe(u8, self.service_type);
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) agenkit.AgentError!agenkit.Result {
        const self: *MockServiceAgent = @ptrCast(@alignCast(ptr));

        std.debug.print("  Trying {s}...", .{self.name});

        if (self.should_fail) {
            std.debug.print(" FAILED\n", .{});
            return agenkit.AgentError.ProcessingFailed;
        }

        const content = message.contentAsText() catch return agenkit.AgentError.ProcessingFailed;

        // Build response
        const response = std.fmt.allocPrint(
            self.allocator,
            "{s} processed by {s}: {s}",
            .{ self.service_type, self.name, content },
        ) catch return agenkit.AgentError.ProcessingFailed;
        defer self.allocator.free(response);

        std.debug.print(" SUCCESS\n", .{});

        const response_msg = Message.withText(self.allocator, .assistant, response) catch return agenkit.AgentError.ProcessingFailed;
        return agenkit.Result{ .ok = response_msg };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *MockServiceAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *MockServiceAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }

    pub fn deinit(self: *MockServiceAgent) void {
        self.allocator.free(self.name);
        self.allocator.free(self.service_type);
        self.allocator.destroy(self);
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Fallback Pattern Example ===\n\n", .{});

    // ========================================================================
    // Example 1: LLM Provider Fallback
    // ========================================================================
    std.debug.print("Example 1: LLM Provider Fallback (Primary Succeeds)\n", .{});
    std.debug.print("----------------------------------------------------\n", .{});

    // Create LLM provider agents
    var gpt4 = try MockServiceAgent.init(allocator, "GPT-4", "LLM", false);
    defer gpt4.deinit();

    var claude = try MockServiceAgent.init(allocator, "Claude", "LLM", false);
    defer claude.deinit();

    var gemini = try MockServiceAgent.init(allocator, "Gemini", "LLM", false);
    defer gemini.deinit();

    // Create fallback with all providers
    const llm_agents = [_]Agent{ gpt4.agent(), claude.agent(), gemini.agent() };
    var llm_fallback = try FallbackAgent.init(allocator, &llm_agents, "LLMFallback");
    defer llm_fallback.deinit();

    // Test with primary succeeding
    std.debug.print("\nInput: \"Explain quantum computing\"\n", .{});

    var msg1 = try Message.withText(allocator, .user, "Explain quantum computing");
    defer msg1.deinit();

    const result1 = llm_fallback.agent().process(msg1) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };

    switch (result1) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("Response: {s}\n", .{response_text});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    // ========================================================================
    // Example 2: Service Degradation with Fallback
    // ========================================================================
    std.debug.print("\n\nExample 2: Service Degradation (Primary Fails, Backup Succeeds)\n", .{});
    std.debug.print("----------------------------------------------------------------\n", .{});

    // Create service agents: primary fails, backup succeeds
    var primary_service = try MockServiceAgent.init(allocator, "PrimaryService", "API", true);
    defer primary_service.deinit();

    var backup_service = try MockServiceAgent.init(allocator, "BackupService", "API", false);
    defer backup_service.deinit();

    var cache_service = try MockServiceAgent.init(allocator, "CacheService", "API", false);
    defer cache_service.deinit();

    // Create fallback
    const service_agents = [_]Agent{ primary_service.agent(), backup_service.agent(), cache_service.agent() };
    var service_fallback = try FallbackAgent.init(allocator, &service_agents, "ServiceFallback");
    defer service_fallback.deinit();

    std.debug.print("\nInput: \"Get user data\"\n", .{});

    var msg2 = try Message.withText(allocator, .user, "Get user data");
    defer msg2.deinit();

    const result2 = service_fallback.agent().process(msg2) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        return;
    };

    switch (result2) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("Response: {s}\n", .{response_text});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    // ========================================================================
    // Example 3: All Services Fail
    // ========================================================================
    std.debug.print("\n\nExample 3: All Services Fail\n", .{});
    std.debug.print("-----------------------------\n", .{});

    // Create failing agents
    var fail1 = try MockServiceAgent.init(allocator, "Service1", "API", true);
    defer fail1.deinit();

    var fail2 = try MockServiceAgent.init(allocator, "Service2", "API", true);
    defer fail2.deinit();

    var fail3 = try MockServiceAgent.init(allocator, "Service3", "API", true);
    defer fail3.deinit();

    // Create fallback
    const fail_agents = [_]Agent{ fail1.agent(), fail2.agent(), fail3.agent() };
    var fail_fallback = try FallbackAgent.init(allocator, &fail_agents, "FailFallback");
    defer fail_fallback.deinit();

    std.debug.print("\nInput: \"Critical request\"\n", .{});

    var msg3 = try Message.withText(allocator, .user, "Critical request");
    defer msg3.deinit();

    const result3 = fail_fallback.agent().process(msg3) catch |err| {
        std.debug.print("All services failed: {}\n", .{err});
        std.debug.print("In production, would log all attempts for diagnostics\n", .{});
        std.debug.print("\n=== Fallback Pattern Complete ===\n\n", .{});
        return;
    };

    switch (result3) {
        .ok => |response| {
            var mutable_response = response;
            defer mutable_response.deinit();
            const response_text = mutable_response.contentAsText() catch "No content";
            std.debug.print("Response: {s}\n", .{response_text});
        },
        .err => |e| {
            std.debug.print("Error: {}\n", .{e});
        },
    }

    std.debug.print("\n=== Fallback Pattern Complete ===\n\n", .{});
}

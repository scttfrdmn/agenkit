/// Graph-of-Thought Reasoning Technique
///
/// Represents reasoning as a directed graph where nodes are thoughts/conclusions
/// and edges represent logical connections. More flexible than tree-based
/// approaches, allows for complex multi-hop reasoning and thought combination.
///
/// This technique is particularly effective for:
/// - Multi-hop reasoning problems
/// - Problems with multiple interconnected concepts
/// - Situations requiring synthesis of multiple reasoning chains
///
/// Reference:
/// - Paper: https://arxiv.org/abs/2308.09687
/// - "Graph of Thoughts: Solving Elaborate Problems with Large Language Models"
const std = @import("std");
const Agent = @import("../../agent.zig").Agent;
const AgentError = @import("../../agent.zig").AgentError;
const Result = @import("../../agent.zig").Result;
const StreamCallbacks = @import("../../agent.zig").StreamCallbacks;
const Message = @import("../../message.zig").Message;
const Role = @import("../../message.zig").Role;
const IntrospectionResult = @import("../../introspection.zig").IntrospectionResult;
const createDefaultIntrospectionResult = @import("../../introspection.zig").createDefaultIntrospectionResult;
const Allocator = std.mem.Allocator;
const ReasoningGraph = @import("reasoning_graph.zig").ReasoningGraph;
const EdgeType = @import("reasoning_graph.zig").EdgeType;

/// Aggregation strategy for combining reasoning paths
pub const AggregatorType = enum {
    path_based,
    node_based,
};

/// Configuration for GraphOfThought
pub const GraphOfThoughtConfig = struct {
    max_nodes: usize = 20,
    max_edges: usize = 40,
    aggregator: AggregatorType = .path_based,
    allow_cycles: bool = false,
};

/// Graph-of-Thought agent
pub const GraphOfThoughtAgent = struct {
    allocator: Allocator,
    base_agent: Agent,
    config: GraphOfThoughtConfig,
    agent_name: []const u8,

    pub fn init(
        allocator: Allocator,
        base_agent: Agent,
        config: GraphOfThoughtConfig,
    ) !*GraphOfThoughtAgent {
        const self = try allocator.create(GraphOfThoughtAgent);
        self.* = GraphOfThoughtAgent{
            .allocator = allocator,
            .base_agent = base_agent,
            .config = config,
            .agent_name = "graph_of_thought",
        };
        return self;
    }

    pub fn agent(self: *GraphOfThoughtAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *GraphOfThoughtAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 5);
        caps[0] = "reasoning";
        caps[1] = "graph_reasoning";
        caps[2] = "multi_hop";
        caps[3] = "path_aggregation";
        caps[4] = "graph_of_thought";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *GraphOfThoughtAgent = @ptrCast(@alignCast(ptr));

        // Allocation failures are mapped to ProcessingFailed rather than
        // propagated: the vtable signature is AgentError!Result, which does not
        // include Allocator.Error.
        return self.processInner(message) catch |err| switch (err) {
            error.OutOfMemory => Result{ .err = AgentError.ProcessingFailed },
            else => |e| Result{ .err = e },
        };
    }

    /// The real body, allowed to fail with Allocator.Error.
    ///
    /// Split out so `try` can be used on allocating calls; processImpl narrows
    /// the error set back down to what the Agent vtable declares.
    fn processInner(self: *GraphOfThoughtAgent, message: Message) (AgentError || Allocator.Error)!Result {
        const problem = message.contentAsText() catch {
            return Result{ .err = AgentError.InvalidInput };
        };

        // Build reasoning graph
        var graph = self.buildGraph(problem) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        defer graph.deinit();

        // Find reasoning paths
        const reasoning_paths = self.findReasoningPaths(&graph) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        defer {
            for (reasoning_paths) |path| {
                self.allocator.free(path);
            }
            self.allocator.free(reasoning_paths);
        }

        // Aggregate paths
        const final_answer = self.aggregatePaths(&graph, reasoning_paths) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        defer self.allocator.free(final_answer);

        const stats = graph.statistics(self.allocator) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        // Build response
        var response = try Message.withText(self.allocator, .assistant, final_answer);
        errdefer response.deinit();

        // Only static string literals and scalars are emitted here. The graph
        // and the reasoning_paths that the Python core also exposes are owned by
        // locals that are freed before this function returns, and Message.deinit
        // does not free top-level metadata strings, so a dynamically allocated
        // one would leak.
        try response.setMetadata("technique", .{ .string = "graph_of_thought" });
        try response.setMetadata("num_nodes", .{ .integer = @as(i64, @intCast(stats.num_nodes)) });
        try response.setMetadata("num_edges", .{ .integer = @as(i64, @intCast(stats.num_edges)) });
        try response.setMetadata("num_paths", .{ .integer = @as(i64, @intCast(reasoning_paths.len)) });
        try response.setMetadata("has_cycles", .{ .bool = stats.has_cycles });
        try response.setMetadata("premise_count", .{ .integer = @as(i64, @intCast(stats.premise_count)) });
        try response.setMetadata("intermediate_count", .{ .integer = @as(i64, @intCast(stats.intermediate_count)) });
        try response.setMetadata("conclusion_count", .{ .integer = @as(i64, @intCast(stats.conclusion_count)) });

        const aggregator_str = switch (self.config.aggregator) {
            .path_based => "path_based",
            .node_based => "node_based",
        };
        try response.setMetadata("aggregator", .{ .string = aggregator_str });
        try response.setMetadata("allow_cycles", .{ .bool = self.config.allow_cycles });

        return Result{ .ok = response };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!IntrospectionResult {
        const self: *GraphOfThoughtAgent = @ptrCast(@alignCast(ptr));
        const caps = try self.agent().capabilities(allocator);
        defer allocator.free(caps);
        return createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *GraphOfThoughtAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }

    /// Call the wrapped agent with a one-shot prompt.
    ///
    /// The returned slice is owned by the caller. contentAsText only borrows
    /// from the response Message, which is freed here, so the text must be
    /// duped — the previous version returned the borrowed slice, which callers
    /// then read and freed: a use-after-free followed by a double free.
    fn llmCall(self: *GraphOfThoughtAgent, prompt: []const u8) ![]const u8 {
        var msg = try Message.withText(self.allocator, .user, prompt);
        defer msg.deinit();

        const result = try self.base_agent.process(msg);
        var response_msg = try result.unwrap();
        defer response_msg.deinit();

        const text = try response_msg.contentAsText();
        return try self.allocator.dupe(u8, text);
    }

    // Helper: Generate premises
    fn generatePremises(self: *GraphOfThoughtAgent, problem: []const u8) ![][]const u8 {
        var prompt_buf = std.ArrayListUnmanaged(u8).empty;
        defer prompt_buf.deinit(self.allocator);

        try prompt_buf.appendSlice(self.allocator, "Identify the key facts and premises for this problem.\n");
        try prompt_buf.appendSlice(self.allocator, "List 2-4 foundational facts or assumptions, one per line.\n\n");
        try prompt_buf.print(self.allocator, "Problem: {s}\n\n", .{problem});
        try prompt_buf.appendSlice(self.allocator, "Premises:");

        const response = try self.llmCall(prompt_buf.items);
        defer self.allocator.free(response);

        return try self.parseLines(response, 4);
    }

    // Helper: Generate thoughts
    fn generateThoughts(self: *GraphOfThoughtAgent, problem: []const u8, existing: []const []const u8, max_new: usize) ![][]const u8 {
        var prompt_buf = std.ArrayListUnmanaged(u8).empty;
        defer prompt_buf.deinit(self.allocator);

        if (existing.len > 0) {
            try prompt_buf.print(self.allocator, "Given this problem and existing thoughts, generate {d} new insights or conclusions.\n\n", .{max_new});
            try prompt_buf.print(self.allocator, "Problem: {s}\n\n", .{problem});
            try prompt_buf.appendSlice(self.allocator, "Existing thoughts:\n");
            for (existing) |thought| {
                try prompt_buf.print(self.allocator, "- {s}\n", .{thought});
            }
            try prompt_buf.appendSlice(self.allocator, "\nNew thoughts (one per line):");
        } else {
            try prompt_buf.print(self.allocator, "Generate {d} initial thoughts or insights about this problem.\n\n", .{max_new});
            try prompt_buf.print(self.allocator, "Problem: {s}\n\n", .{problem});
            try prompt_buf.appendSlice(self.allocator, "Thoughts (one per line):");
        }

        const response = try self.llmCall(prompt_buf.items);
        defer self.allocator.free(response);

        return try self.parseLines(response, max_new);
    }

    // Helper: Identify connection
    fn identifyConnection(self: *GraphOfThoughtAgent, thought1: []const u8, thought2: []const u8) !?EdgeType {
        var prompt_buf = std.ArrayListUnmanaged(u8).empty;
        defer prompt_buf.deinit(self.allocator);

        try prompt_buf.appendSlice(self.allocator, "Analyze the logical relationship between these two statements.\n\n");
        try prompt_buf.print(self.allocator, "Statement 1: {s}\n\n", .{thought1});
        try prompt_buf.print(self.allocator, "Statement 2: {s}\n\n", .{thought2});
        try prompt_buf.appendSlice(self.allocator, "Does statement 2:\n");
        try prompt_buf.appendSlice(self.allocator, "- SUPPORT statement 1 (provides evidence or reasoning for it)\n");
        try prompt_buf.appendSlice(self.allocator, "- DEPEND on statement 1 (requires it to be true)\n");
        try prompt_buf.appendSlice(self.allocator, "- CONTRADICT statement 1 (conflicts with it)\n");
        try prompt_buf.appendSlice(self.allocator, "- REFINE statement 1 (improves or clarifies it)\n");
        try prompt_buf.appendSlice(self.allocator, "- NO_RELATION (no clear logical connection)\n\n");
        try prompt_buf.appendSlice(self.allocator, "Answer with one word: SUPPORT, DEPEND, CONTRADICT, REFINE, or NO_RELATION");

        const response = try self.llmCall(prompt_buf.items);
        defer self.allocator.free(response);

        // Convert to uppercase for comparison
        const upper = try self.allocator.alloc(u8, response.len);
        defer self.allocator.free(upper);
        for (response, 0..) |c, i| {
            upper[i] = std.ascii.toUpper(c);
        }

        if (std.mem.indexOf(u8, upper, "SUPPORT") != null) {
            return EdgeType.supports;
        } else if (std.mem.indexOf(u8, upper, "DEPEND") != null) {
            return EdgeType.depends_on;
        } else if (std.mem.indexOf(u8, upper, "CONTRADICT") != null) {
            return EdgeType.contradicts;
        } else if (std.mem.indexOf(u8, upper, "REFINE") != null) {
            return EdgeType.refines;
        }

        return null;
    }

    // Helper: Parse lines from response
    fn parseLines(self: *GraphOfThoughtAgent, text: []const u8, max_lines: usize) ![][]const u8 {
        var lines = std.ArrayListUnmanaged([]const u8).empty;
        errdefer {
            for (lines.items) |line| {
                self.allocator.free(line);
            }
            lines.deinit(self.allocator);
        }

        var iter = std.mem.splitScalar(u8, text, '\n');
        while (iter.next()) |line| {
            if (lines.items.len >= max_lines) break;

            const trimmed = std.mem.trim(u8, line, " \t\r\n");
            if (trimmed.len == 0 or trimmed[0] == '#') continue;

            // Remove numbering and bullets. The multi-byte bullet is matched as
            // a string: "•" is U+2022, three bytes in UTF-8, so the original
            // `c == '•'` compared a u8 against 8226 and never fired, leaving
            // the raw bytes in the parsed thought.
            var start: usize = 0;
            while (start < trimmed.len) {
                if (std.mem.startsWith(u8, trimmed[start..], "•")) {
                    start += "•".len;
                    continue;
                }
                const c = trimmed[start];
                if (std.ascii.isDigit(c) or c == '.' or c == '-' or c == '*') {
                    start += 1;
                } else {
                    break;
                }
            }

            const cleaned = std.mem.trim(u8, trimmed[start..], " \t");
            if (cleaned.len > 0) {
                try lines.append(self.allocator, try self.allocator.dupe(u8, cleaned));
            }
        }

        return try lines.toOwnedSlice(self.allocator);
    }

    // Build reasoning graph
    fn buildGraph(self: *GraphOfThoughtAgent, problem: []const u8) !ReasoningGraph {
        var graph = ReasoningGraph.init(self.allocator);
        errdefer graph.deinit();

        // Generate premises
        const premises = try self.generatePremises(problem);
        defer {
            for (premises) |p| {
                self.allocator.free(p);
            }
            self.allocator.free(premises);
        }

        var node_ids = std.ArrayListUnmanaged(usize).empty;
        defer node_ids.deinit(self.allocator);

        for (premises) |premise| {
            const id = try graph.addNode(premise, .premise, 0.9);
            try node_ids.append(self.allocator, id);
        }

        // Generate intermediate thoughts
        var all_thoughts = std.ArrayListUnmanaged([]const u8).empty;
        defer {
            for (all_thoughts.items) |t| {
                self.allocator.free(t);
            }
            all_thoughts.deinit(self.allocator);
        }

        for (premises) |p| {
            try all_thoughts.append(self.allocator, try self.allocator.dupe(u8, p));
        }

        while (graph.nodeCount() < self.config.max_nodes) {
            const max_new = @min(3, self.config.max_nodes - graph.nodeCount());
            if (max_new == 0) break;

            const new_thoughts = self.generateThoughts(problem, all_thoughts.items, max_new) catch break;
            defer {
                for (new_thoughts) |t| {
                    self.allocator.free(t);
                }
                self.allocator.free(new_thoughts);
            }

            if (new_thoughts.len == 0) break;

            for (new_thoughts) |thought| {
                if (graph.nodeCount() >= self.config.max_nodes) break;

                const id = try graph.addNode(thought, .intermediate, 0.7);
                try node_ids.append(self.allocator, id);
                try all_thoughts.append(self.allocator, try self.allocator.dupe(u8, thought));
            }
        }

        // Identify connections
        var edge_count: usize = 0;
        for (node_ids.items, 0..) |id1, i| {
            if (edge_count >= self.config.max_edges) break;

            for (node_ids.items[i + 1 ..]) |id2| {
                if (edge_count >= self.config.max_edges) break;

                const node1 = graph.getNode(id1) orelse continue;
                const node2 = graph.getNode(id2) orelse continue;

                // The edge type is resolved before addEdge runs, so no node
                // pointer is held across a graph mutation.
                const maybe_edge = self.identifyConnection(node1.content, node2.content) catch continue;
                const edge_type = maybe_edge orelse continue;

                graph.addEdge(id1, id2, edge_type, 0.8) catch continue;
                edge_count += 1;
            }
        }

        // Generate conclusion
        if (graph.nodeCount() < self.config.max_nodes) {
            var conclusion_prompt = std.ArrayListUnmanaged(u8).empty;
            defer conclusion_prompt.deinit(self.allocator);

            try conclusion_prompt.appendSlice(self.allocator, "Based on all these thoughts, what is the final conclusion?\n\n");
            try conclusion_prompt.print(self.allocator, "Problem: {s}\n\n", .{problem});
            try conclusion_prompt.appendSlice(self.allocator, "Thoughts:\n");
            for (all_thoughts.items) |t| {
                try conclusion_prompt.print(self.allocator, "- {s}\n", .{t});
            }
            try conclusion_prompt.appendSlice(self.allocator, "\nFinal conclusion:");

            if (self.llmCall(conclusion_prompt.items)) |conclusion| {
                defer self.allocator.free(conclusion);

                const trimmed = std.mem.trim(u8, conclusion, " \t\r\n");
                if (trimmed.len > 0) {
                    const conclusion_id = try graph.addNode(trimmed, .conclusion, 0.8);

                    // Connect to recent thoughts
                    const connect_count = @min(3, node_ids.items.len);
                    for (node_ids.items[node_ids.items.len - connect_count ..]) |recent_id| {
                        if (edge_count >= self.config.max_edges) break;
                        // edge_count only advances when the edge is actually
                        // added; the previous version counted failures too.
                        graph.addEdge(recent_id, conclusion_id, .supports, 0.9) catch continue;
                        edge_count += 1;
                    }
                }
            } else |_| {}
        }

        return graph;
    }

    // Find reasoning paths
    fn findReasoningPaths(self: *GraphOfThoughtAgent, graph: *const ReasoningGraph) ![][]usize {
        const premises = try graph.getPremises(self.allocator);
        defer self.allocator.free(premises);

        const conclusions = try graph.getConclusions(self.allocator);
        defer self.allocator.free(conclusions);

        var all_paths = std.ArrayListUnmanaged([]usize).empty;
        errdefer {
            for (all_paths.items) |path| {
                self.allocator.free(path);
            }
            all_paths.deinit(self.allocator);
        }

        for (premises) |premise| {
            for (conclusions) |conclusion| {
                const paths = try graph.findPaths(self.allocator, premise.id, conclusion.id, 6);
                // findPaths returns owned inner slices; freeing only the outer
                // slice, as the previous version did, leaked every path.
                defer {
                    for (paths) |path| {
                        self.allocator.free(path);
                    }
                    self.allocator.free(paths);
                }

                for (paths) |path| {
                    try all_paths.append(self.allocator, try self.allocator.dupe(usize, path));
                }
            }
        }

        return try all_paths.toOwnedSlice(self.allocator);
    }

    // Aggregate paths
    fn aggregatePaths(self: *GraphOfThoughtAgent, graph: *const ReasoningGraph, paths: []const []usize) ![]const u8 {
        if (paths.len == 0) {
            // No paths - use conclusion nodes
            const conclusions = try graph.getConclusions(self.allocator);
            defer self.allocator.free(conclusions);

            if (conclusions.len > 0) {
                return try self.allocator.dupe(u8, conclusions[0].content);
            }

            return try self.allocator.dupe(u8, "Unable to reach conclusion");
        }

        if (self.config.aggregator == .path_based) {
            // Find best path
            var best_path = paths[0];
            var best_score = graph.getPathScore(best_path);

            for (paths[1..]) |path| {
                const score = graph.getPathScore(path);
                if (score > best_score) {
                    best_score = score;
                    best_path = path;
                }
            }

            const conclusion_node = graph.getNode(best_path[best_path.len - 1]) orelse {
                return try self.allocator.dupe(u8, "Unable to reach conclusion");
            };

            return try self.allocator.dupe(u8, conclusion_node.content);
        }

        // Node-based aggregation
        var node_counts = std.AutoHashMap(usize, usize).init(self.allocator);
        defer node_counts.deinit();

        for (paths) |path| {
            for (path) |node_id| {
                const count = node_counts.get(node_id) orelse 0;
                try node_counts.put(node_id, count + 1);
            }
        }

        var best_node_id: usize = 0;
        var best_score: f64 = 0.0;
        var found_any = false;

        var iter = node_counts.iterator();
        while (iter.next()) |entry| {
            if (graph.getNode(entry.key_ptr.*)) |node| {
                const score = @as(f64, @floatFromInt(entry.value_ptr.*)) * node.confidence;
                if (!found_any or score > best_score) {
                    found_any = true;
                    best_score = score;
                    best_node_id = entry.key_ptr.*;
                }
            }
        }

        // found_any guards the fallback. The previous version seeded best_score
        // to -1.0 and best_node_id to 0, so if no path node resolved it silently
        // answered with node 0's content instead of admitting defeat.
        if (!found_any) {
            return try self.allocator.dupe(u8, "Unable to reach conclusion");
        }

        const best_node = graph.getNode(best_node_id) orelse {
            return try self.allocator.dupe(u8, "Unable to reach conclusion");
        };

        return try self.allocator.dupe(u8, best_node.content);
    }
};

// ============================================================================
// Tests
// ============================================================================

const MockAgent = @import("../../test_utils.zig").MockAgent;

/// Script used by the end-to-end tests.
///
/// MockAgent cycles its responses, and the empty entry makes generateThoughts
/// parse zero lines, which ends graph growth — otherwise the default max_nodes
/// of 20 drives ~190 pairwise identifyConnection calls per test.
const script = [_][]const u8{
    "1. Premise A\n2. Premise B",
    "1. Thought 1",
    "",
    "SUPPORT",
    "Final conclusion",
};

test "GraphOfThought name and capabilities" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"response"});
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
    const got_agent = got.agent();
    defer got_agent.deinit();

    try testing.expectEqualStrings("graph_of_thought", got_agent.name());

    const caps = try got_agent.capabilities(allocator);
    defer allocator.free(caps);
    try testing.expectEqual(@as(usize, 5), caps.len);
    try testing.expectEqualStrings("reasoning", caps[0]);
    try testing.expectEqualStrings("graph_reasoning", caps[1]);
    try testing.expectEqualStrings("multi_hop", caps[2]);
    try testing.expectEqualStrings("path_aggregation", caps[3]);
    try testing.expectEqualStrings("graph_of_thought", caps[4]);
}

test "GraphOfThought custom config" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"response"});
    defer mock.deinit();

    const config = GraphOfThoughtConfig{
        .max_nodes = 15,
        .max_edges = 30,
        .aggregator = .node_based,
        .allow_cycles = true,
    };
    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), config);
    defer got.agent().deinit();

    try testing.expectEqual(@as(usize, 15), got.config.max_nodes);
    try testing.expectEqual(@as(usize, 30), got.config.max_edges);
    try testing.expectEqual(AggregatorType.node_based, got.config.aggregator);
    try testing.expectEqual(true, got.config.allow_cycles);
}

test "GraphOfThought default config" {
    const testing = std.testing;

    const config = GraphOfThoughtConfig{};
    try testing.expectEqual(@as(usize, 20), config.max_nodes);
    try testing.expectEqual(@as(usize, 40), config.max_edges);
    try testing.expectEqual(AggregatorType.path_based, config.aggregator);
    try testing.expectEqual(false, config.allow_cycles);
}

test "GraphOfThought basic functionality" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &script);
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
    const got_agent = got.agent();
    defer got_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Test problem");
    defer msg.deinit();

    var response = try (try got_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expect((try response.contentAsText()).len > 0);
    try testing.expectEqualStrings("graph_of_thought", response.getMetadata("technique").?.string);
    try testing.expect(response.getMetadata("num_nodes").?.integer > 0);
}

test "GraphOfThought max_nodes enforcement" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &script);
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{ .max_nodes = 3 });
    const got_agent = got.agent();
    defer got_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    var response = try (try got_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expect(response.getMetadata("num_nodes").?.integer <= 3);
}

test "GraphOfThought max_edges enforcement" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Every connection query answers SUPPORT, so the only thing holding the
    // edge count down is max_edges.
    var mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Premise A\n2. Premise B\n3. Premise C\n4. Premise D",
        "",
        "SUPPORT",
    });
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{ .max_edges = 2 });
    const got_agent = got.agent();
    defer got_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    var response = try (try got_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expect(response.getMetadata("num_edges").?.integer <= 2);
}

test "GraphOfThought path_based aggregation" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &script);
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{ .aggregator = .path_based });
    const got_agent = got.agent();
    defer got_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    var response = try (try got_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expect((try response.contentAsText()).len > 0);
    try testing.expectEqualStrings("path_based", response.getMetadata("aggregator").?.string);
}

test "GraphOfThought node_based aggregation" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &script);
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{ .aggregator = .node_based });
    const got_agent = got.agent();
    defer got_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    var response = try (try got_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expect((try response.contentAsText()).len > 0);
    try testing.expectEqualStrings("node_based", response.getMetadata("aggregator").?.string);
}

test "GraphOfThought metadata completeness" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &script);
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
    const got_agent = got.agent();
    defer got_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    var response = try (try got_agent.process(msg)).unwrap();
    defer response.deinit();

    for ([_][]const u8{
        "technique",
        "num_nodes",
        "num_edges",
        "num_paths",
        "has_cycles",
        "premise_count",
        "intermediate_count",
        "conclusion_count",
        "aggregator",
        "allow_cycles",
    }) |key| {
        try testing.expect(response.getMetadata(key) != null);
    }

    // The node-type counts must add up to the reported node total.
    const stats_sum = response.getMetadata("premise_count").?.integer +
        response.getMetadata("intermediate_count").?.integer +
        response.getMetadata("conclusion_count").?.integer;
    try testing.expectEqual(response.getMetadata("num_nodes").?.integer, stats_sum);
}

test "GraphOfThought allow_cycles is reported, not silently dropped" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &script);
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{ .allow_cycles = true });
    const got_agent = got.agent();
    defer got_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    var response = try (try got_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expectEqual(true, response.getMetadata("allow_cycles").?.bool);
}

test "AggregatorType enum values" {
    const testing = std.testing;

    try testing.expect(AggregatorType.path_based != AggregatorType.node_based);
    try testing.expectEqual(@as(usize, 2), std.meta.fields(AggregatorType).len);
}

test "GraphOfThought response role" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &script);
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
    const got_agent = got.agent();
    defer got_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    var response = try (try got_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expectEqual(Role.assistant, response.role);
}

test "GraphOfThought parseLines strips numbering and bullets" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
    defer got.agent().deinit();

    const lines = try got.parseLines("1. First\n- Second\n\n# comment\n* Third\n• Fourth", 10);
    defer {
        for (lines) |line| allocator.free(line);
        allocator.free(lines);
    }

    try testing.expectEqual(@as(usize, 4), lines.len);
    try testing.expectEqualStrings("First", lines[0]);
    try testing.expectEqualStrings("Second", lines[1]);
    try testing.expectEqualStrings("Third", lines[2]);
    // "•" is three UTF-8 bytes; a byte-wise comparison leaves them in place.
    try testing.expectEqualStrings("Fourth", lines[3]);
}

test "GraphOfThought parseLines honours max_lines" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
    defer got.agent().deinit();

    const lines = try got.parseLines("a\nb\nc\nd\ne", 2);
    defer {
        for (lines) |line| allocator.free(line);
        allocator.free(lines);
    }

    try testing.expectEqual(@as(usize, 2), lines.len);
}

test "GraphOfThought identifyConnection maps each keyword" {
    const testing = std.testing;

    const cases = [_]struct { reply: []const u8, want: ?EdgeType }{
        .{ .reply = "SUPPORT", .want = .supports },
        .{ .reply = "depend", .want = .depends_on },
        .{ .reply = "This CONTRADICTS it", .want = .contradicts },
        .{ .reply = "refine", .want = .refines },
        .{ .reply = "NO_RELATION", .want = null },
    };

    for (cases) |case| {
        var gpa = std.heap.DebugAllocator(.{}){};
        defer _ = gpa.deinit();
        const allocator = gpa.allocator();

        var mock = try MockAgent.init(allocator, &[_][]const u8{case.reply});
        defer mock.deinit();

        var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
        defer got.agent().deinit();

        try testing.expectEqual(case.want, try got.identifyConnection("a", "b"));
    }
}

test "GraphOfThought aggregatePaths falls back when there are no paths" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
    defer got.agent().deinit();

    var graph = ReasoningGraph.init(allocator);
    defer graph.deinit();

    // No conclusion node at all.
    _ = try graph.addNode("just a premise", .premise, 0.9);
    const empty = try got.aggregatePaths(&graph, &[_][]usize{});
    defer allocator.free(empty);
    try testing.expectEqualStrings("Unable to reach conclusion", empty);

    // With a conclusion node, that node's content is used.
    _ = try graph.addNode("the conclusion", .conclusion, 0.8);
    const found = try got.aggregatePaths(&graph, &[_][]usize{});
    defer allocator.free(found);
    try testing.expectEqualStrings("the conclusion", found);
}

test "GraphOfThought aggregatePaths picks the highest-scoring path" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{ .aggregator = .path_based });
    defer got.agent().deinit();

    var graph = ReasoningGraph.init(allocator);
    defer graph.deinit();

    const p = try graph.addNode("premise", .premise, 0.9);
    const weak = try graph.addNode("weak conclusion", .conclusion, 0.1);
    const strong = try graph.addNode("strong conclusion", .conclusion, 0.9);
    try graph.addEdge(p, weak, .supports, 0.1);
    try graph.addEdge(p, strong, .supports, 0.9);

    var weak_path = [_]usize{ p, weak };
    var strong_path = [_]usize{ p, strong };

    // Deliberately listed weakest-first so a "keep the first" bug would fail.
    const answer = try got.aggregatePaths(&graph, &[_][]usize{ &weak_path, &strong_path });
    defer allocator.free(answer);
    try testing.expectEqualStrings("strong conclusion", answer);
}

test "GraphOfThought aggregatePaths node_based weights by frequency and confidence" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{ .aggregator = .node_based });
    defer got.agent().deinit();

    var graph = ReasoningGraph.init(allocator);
    defer graph.deinit();

    const rare = try graph.addNode("rare", .premise, 0.9);
    const common = try graph.addNode("common", .intermediate, 0.8);
    const tail = try graph.addNode("tail", .conclusion, 0.1);

    var path_a = [_]usize{ rare, common, tail };
    var path_b = [_]usize{ common, tail };

    // "common" appears twice at confidence 0.8 (1.6) and outscores "rare" at
    // 0.9 once, so the winner is neither the first nor the last node seen.
    const answer = try got.aggregatePaths(&graph, &[_][]usize{ &path_a, &path_b });
    defer allocator.free(answer);
    try testing.expectEqualStrings("common", answer);
}

test "GraphOfThought aggregatePaths node_based admits defeat when no node resolves" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{ .aggregator = .node_based });
    defer got.agent().deinit();

    var graph = ReasoningGraph.init(allocator);
    defer graph.deinit();

    // Node 0 exists and would be a plausible-looking answer, but no id on the
    // path is in the graph, so nothing was actually aggregated.
    const zero = try graph.addNode("node zero", .premise, 0.9);
    try testing.expectEqual(@as(usize, 0), zero);

    var dangling = [_]usize{ 41, 42 };

    // The guard must fire. Seeding best_node_id to 0 instead — as the original
    // did — silently returns "node zero", an answer that was never on any path.
    const answer = try got.aggregatePaths(&graph, &[_][]usize{&dangling});
    defer allocator.free(answer);
    try testing.expectEqualStrings("Unable to reach conclusion", answer);
}

test "GraphOfThought findReasoningPaths connects premises to conclusions" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
    defer got.agent().deinit();

    var graph = ReasoningGraph.init(allocator);
    defer graph.deinit();

    const p = try graph.addNode("premise", .premise, 0.9);
    const mid = try graph.addNode("middle", .intermediate, 0.7);
    const c = try graph.addNode("conclusion", .conclusion, 0.8);
    // Unreachable from the premise: proves paths are traversed, not enumerated.
    _ = try graph.addNode("orphan conclusion", .conclusion, 0.8);
    try graph.addEdge(p, mid, .supports, 0.8);
    try graph.addEdge(mid, c, .supports, 0.8);

    const paths = try got.findReasoningPaths(&graph);
    defer {
        for (paths) |path| allocator.free(path);
        allocator.free(paths);
    }

    try testing.expectEqual(@as(usize, 1), paths.len);
    try testing.expectEqualSlices(usize, &[_]usize{ p, mid, c }, paths[0]);
}

/// Callback sink that records whether it was ever invoked.
///
/// Used to prove processStream rejects outright rather than emitting a partial
/// stream before failing.
const RecordingSink = struct {
    messages: usize = 0,
    errors: usize = 0,
    completions: usize = 0,
    last_error: ?AgentError = null,

    fn onMessage(ptr: *anyopaque, message: Message) void {
        _ = message;
        const self: *RecordingSink = @ptrCast(@alignCast(ptr));
        self.messages += 1;
    }

    fn onError(ptr: *anyopaque, err: AgentError) void {
        const self: *RecordingSink = @ptrCast(@alignCast(ptr));
        self.errors += 1;
        self.last_error = err;
    }

    fn onComplete(ptr: *anyopaque) void {
        const self: *RecordingSink = @ptrCast(@alignCast(ptr));
        self.completions += 1;
    }

    fn callbacks(self: *RecordingSink) StreamCallbacks {
        return StreamCallbacks{
            .ptr = self,
            .on_message_fn = onMessage,
            .on_error_fn = onError,
            .on_complete_fn = onComplete,
        };
    }
};

test "GraphOfThought process_stream is not implemented" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
    const got_agent = got.agent();
    defer got_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    var sink = RecordingSink{};
    try testing.expectError(
        AgentError.NotImplemented,
        got_agent.processStream(msg, sink.callbacks()),
    );

    // Nothing was emitted, not even an error callback.
    try testing.expectEqual(@as(usize, 0), sink.messages);
    try testing.expectEqual(@as(usize, 0), sink.errors);
    try testing.expectEqual(@as(usize, 0), sink.completions);
    try testing.expectEqual(@as(?AgentError, null), sink.last_error);
}

test "GraphOfThought introspection reports name and capabilities" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var got = try GraphOfThoughtAgent.init(allocator, mock.agent(), .{});
    const got_agent = got.agent();
    defer got_agent.deinit();

    var info = try got_agent.introspect(allocator);
    defer info.deinit();

    try testing.expectEqualStrings("graph_of_thought", info.agent_name);
    try testing.expectEqual(@as(usize, 5), info.capabilities.len);
    try testing.expectEqualStrings("graph_of_thought", info.capabilities[4]);
}

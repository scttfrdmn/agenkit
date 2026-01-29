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
const Message = @import("../../message.zig").Message;
const Allocator = std.mem.Allocator;
const ReasoningGraph = @import("reasoning_graph.zig").ReasoningGraph;
const NodeType = @import("reasoning_graph.zig").NodeType;
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

        // Build response
        var response = Message.withText(self.allocator, .assistant, final_answer) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        // Add metadata
        const stats = graph.statistics(self.allocator) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        response.setMetadata("technique", .{ .string = "graph_of_thought" }) catch {};
        response.setMetadata("num_nodes", .{ .integer = @intCast(stats.num_nodes) }) catch {};
        response.setMetadata("num_edges", .{ .integer = @intCast(stats.num_edges) }) catch {};
        response.setMetadata("num_paths", .{ .integer = @intCast(reasoning_paths.len) }) catch {};

        return Result{ .ok = response };
    }

    fn processStreamImpl(
        ptr: *anyopaque,
        message: Message,
        stream_callback: *const fn (chunk: []const u8, userdata: ?*anyopaque) void,
        userdata: ?*anyopaque,
    ) AgentError!void {
        const self: *GraphOfThoughtAgent = @ptrCast(@alignCast(ptr));
        _ = self;
        _ = message;
        _ = stream_callback;
        _ = userdata;
        return AgentError.NotSupported;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const u8 {
        _ = ptr;
        return try allocator.dupe(u8, "GraphOfThought agent for multi-hop reasoning");
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *GraphOfThoughtAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }

    // Helper: Call LLM
    fn llmCall(self: *GraphOfThoughtAgent, prompt: []const u8) ![]const u8 {
        var msg = try Message.withText(self.allocator, .user, prompt);
        defer msg.deinit();

        var result = try self.base_agent.vtable.process(self.base_agent.ptr, msg);
        if (result == .err) {
            return error.LLMCallFailed;
        }

        var response_msg = result.ok;
        defer response_msg.deinit();

        return response_msg.contentAsText() catch error.InvalidResponse;
    }

    // Helper: Generate premises
    fn generatePremises(self: *GraphOfThoughtAgent, problem: []const u8) ![][]const u8 {
        var prompt_buf = std.ArrayList(u8).init(self.allocator);
        defer prompt_buf.deinit();

        const writer = prompt_buf.writer();
        try writer.print("Identify the key facts and premises for this problem.\n", .{});
        try writer.print("List 2-4 foundational facts or assumptions, one per line.\n\n", .{});
        try writer.print("Problem: {s}\n\n", .{problem});
        try writer.print("Premises:", .{});

        const response = try self.llmCall(prompt_buf.items);
        defer self.allocator.free(response);

        return try self.parseLines(response, 4);
    }

    // Helper: Generate thoughts
    fn generateThoughts(self: *GraphOfThoughtAgent, problem: []const u8, existing: []const []const u8, max_new: usize) ![][]const u8 {
        var prompt_buf = std.ArrayList(u8).init(self.allocator);
        defer prompt_buf.deinit();

        const writer = prompt_buf.writer();
        if (existing.len > 0) {
            try writer.print("Given this problem and existing thoughts, generate {d} new insights or conclusions.\n\n", .{max_new});
            try writer.print("Problem: {s}\n\n", .{problem});
            try writer.print("Existing thoughts:\n", .{});
            for (existing) |thought| {
                try writer.print("- {s}\n", .{thought});
            }
            try writer.print("\nNew thoughts (one per line):", .{});
        } else {
            try writer.print("Generate {d} initial thoughts or insights about this problem.\n\n", .{max_new});
            try writer.print("Problem: {s}\n\n", .{problem});
            try writer.print("Thoughts (one per line):", .{});
        }

        const response = try self.llmCall(prompt_buf.items);
        defer self.allocator.free(response);

        return try self.parseLines(response, max_new);
    }

    // Helper: Identify connection
    fn identifyConnection(self: *GraphOfThoughtAgent, thought1: []const u8, thought2: []const u8) !?EdgeType {
        var prompt_buf = std.ArrayList(u8).init(self.allocator);
        defer prompt_buf.deinit();

        const writer = prompt_buf.writer();
        try writer.print("Analyze the logical relationship between these two statements.\n\n", .{});
        try writer.print("Statement 1: {s}\n\n", .{thought1});
        try writer.print("Statement 2: {s}\n\n", .{thought2});
        try writer.print("Does statement 2:\n", .{});
        try writer.print("- SUPPORT statement 1 (provides evidence or reasoning for it)\n", .{});
        try writer.print("- DEPEND on statement 1 (requires it to be true)\n", .{});
        try writer.print("- CONTRADICT statement 1 (conflicts with it)\n", .{});
        try writer.print("- REFINE statement 1 (improves or clarifies it)\n", .{});
        try writer.print("- NO_RELATION (no clear logical connection)\n\n", .{});
        try writer.print("Answer with one word: SUPPORT, DEPEND, CONTRADICT, REFINE, or NO_RELATION", .{});

        const response = try self.llmCall(prompt_buf.items);
        defer self.allocator.free(response);

        // Convert to uppercase for comparison
        var upper = try self.allocator.alloc(u8, response.len);
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
        var lines = std.ArrayList([]const u8).init(self.allocator);
        defer {
            for (lines.items) |line| {
                self.allocator.free(line);
            }
            lines.deinit();
        }

        var iter = std.mem.splitScalar(u8, text, '\n');
        while (iter.next()) |line| {
            if (lines.items.len >= max_lines) break;

            var trimmed = std.mem.trim(u8, line, " \t\r\n");
            if (trimmed.len == 0 or trimmed[0] == '#') continue;

            // Remove numbering and bullets
            var start: usize = 0;
            while (start < trimmed.len) {
                const c = trimmed[start];
                if (std.ascii.isDigit(c) or c == '.' or c == '-' or c == '*' or c == '•') {
                    start += 1;
                } else {
                    break;
                }
            }

            const cleaned = std.mem.trim(u8, trimmed[start..], " \t");
            if (cleaned.len > 0) {
                try lines.append(try self.allocator.dupe(u8, cleaned));
            }
        }

        return try lines.toOwnedSlice();
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

        var premise_ids = std.ArrayList(usize).init(self.allocator);
        defer premise_ids.deinit();

        for (premises) |premise| {
            const id = try graph.addNode(premise, .premise, 0.9);
            try premise_ids.append(id);
        }

        // Generate intermediate thoughts
        var all_thoughts = std.ArrayList([]const u8).init(self.allocator);
        defer {
            for (all_thoughts.items) |t| {
                self.allocator.free(t);
            }
            all_thoughts.deinit();
        }

        for (premises) |p| {
            try all_thoughts.append(try self.allocator.dupe(u8, p));
        }

        var node_ids = std.ArrayList(usize).init(self.allocator);
        defer node_ids.deinit();

        try node_ids.appendSlice(premise_ids.items);

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
                try node_ids.append(id);
                try all_thoughts.append(try self.allocator.dupe(u8, thought));
            }
        }

        // Identify connections
        var edge_count: usize = 0;
        for (node_ids.items, 0..) |id1, i| {
            if (edge_count >= self.config.max_edges) break;

            for (node_ids.items[i + 1 ..], i + 1..) |id2, _| {
                if (edge_count >= self.config.max_edges) break;

                const node1 = graph.getNode(id1) orelse continue;
                const node2 = graph.getNode(id2) orelse continue;

                if (self.identifyConnection(node1.content, node2.content)) |maybe_edge| {
                    if (maybe_edge) |edge_type| {
                        graph.addEdge(id1, id2, edge_type, 0.8) catch continue;
                        edge_count += 1;
                    }
                } else |_| {}
            }
        }

        // Generate conclusion
        if (graph.nodeCount() < self.config.max_nodes) {
            var conclusion_prompt = std.ArrayList(u8).init(self.allocator);
            defer conclusion_prompt.deinit();

            const writer = conclusion_prompt.writer();
            try writer.print("Based on all these thoughts, what is the final conclusion?\n\n", .{});
            try writer.print("Problem: {s}\n\n", .{problem});
            try writer.print("Thoughts:\n", .{});
            for (all_thoughts.items) |t| {
                try writer.print("- {s}\n", .{t});
            }
            try writer.print("\nFinal conclusion:", .{});

            if (self.llmCall(conclusion_prompt.items)) |conclusion| {
                defer self.allocator.free(conclusion);

                const trimmed = std.mem.trim(u8, conclusion, " \t\r\n");
                const conclusion_id = try graph.addNode(trimmed, .conclusion, 0.8);

                // Connect to recent thoughts
                const connect_count = @min(3, node_ids.items.len);
                for (node_ids.items[node_ids.items.len - connect_count ..]) |recent_id| {
                    if (edge_count >= self.config.max_edges) break;
                    graph.addEdge(recent_id, conclusion_id, .supports, 0.9) catch {};
                    edge_count += 1;
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

        var all_paths = std.ArrayList([]usize).init(self.allocator);
        defer {
            for (all_paths.items) |path| {
                self.allocator.free(path);
            }
            all_paths.deinit();
        }

        for (premises) |premise| {
            for (conclusions) |conclusion| {
                const paths = try graph.findPaths(self.allocator, premise.id, conclusion.id, 6);
                defer self.allocator.free(paths);

                for (paths) |path| {
                    try all_paths.append(try self.allocator.dupe(usize, path));
                }
            }
        }

        return try all_paths.toOwnedSlice();
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
        } else {
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
            var best_score: f64 = -1.0;

            var iter = node_counts.iterator();
            while (iter.next()) |entry| {
                if (graph.getNode(entry.key_ptr.*)) |node| {
                    const score = @as(f64, @floatFromInt(entry.value_ptr.*)) * node.confidence;
                    if (score > best_score) {
                        best_score = score;
                        best_node_id = entry.key_ptr.*;
                    }
                }
            }

            const best_node = graph.getNode(best_node_id) orelse {
                return try self.allocator.dupe(u8, "Unable to reach conclusion");
            };

            return try self.allocator.dupe(u8, best_node.content);
        }
    }
};

// ============================================================================
// Tests
// ============================================================================

test "GraphOfThought name and capabilities" {
    const testing = std.testing;
    const MockAgent = @import("../../test_utils.zig").MockAgent;

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"response"});
    defer mock.deinit();

    const config = GraphOfThoughtConfig{};
    var agent = try GraphOfThoughtAgent.init(allocator, mock.agent(), config);
    defer agent.allocator.destroy(agent);

    const got_agent = agent.agent();
    try testing.expectEqualStrings("graph_of_thought", got_agent.name());

    const caps = try got_agent.capabilities(allocator);
    defer allocator.free(caps);
    try testing.expect(caps.len == 5);
    try testing.expectEqualStrings("reasoning", caps[0]);
    try testing.expectEqualStrings("graph_reasoning", caps[1]);
    try testing.expectEqualStrings("multi_hop", caps[2]);
}

test "GraphOfThought custom config" {
    const testing = std.testing;
    const MockAgent = @import("../../test_utils.zig").MockAgent;

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
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
    var agent = try GraphOfThoughtAgent.init(allocator, mock.agent(), config);
    defer agent.allocator.destroy(agent);

    try testing.expectEqual(@as(usize, 15), agent.config.max_nodes);
    try testing.expectEqual(@as(usize, 30), agent.config.max_edges);
    try testing.expectEqual(AggregatorType.node_based, agent.config.aggregator);
    try testing.expectEqual(true, agent.config.allow_cycles);
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
    const MockAgent = @import("../../test_utils.zig").MockAgent;

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Premise A\n2. Premise B",
        "1. Thought 1",
        "",
        "SUPPORT",
        "Final conclusion",
    });
    defer mock.deinit();

    const config = GraphOfThoughtConfig{};
    var agent = try GraphOfThoughtAgent.init(allocator, mock.agent(), config);
    defer agent.allocator.destroy(agent);

    const msg = try Message.withText(allocator, .user, "Test problem");
    defer msg.deinit();

    const got_agent = agent.agent();
    const result = try got_agent.process(msg);
    defer result.ok.deinit();

    try testing.expect(result.ok.content.string.len > 0);
    try testing.expect(result.ok.metadata.contains("technique"));
    try testing.expectEqualStrings("graph_of_thought", result.ok.metadata.get("technique").?.string);
}

test "GraphOfThought max_nodes enforcement" {
    const testing = std.testing;
    const MockAgent = @import("../../test_utils.zig").MockAgent;

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Premise A\n2. Premise B",
        "1. Thought 1",
        "",
        "SUPPORT",
        "Final conclusion",
    });
    defer mock.deinit();

    const config = GraphOfThoughtConfig{ .max_nodes = 3 };
    var agent = try GraphOfThoughtAgent.init(allocator, mock.agent(), config);
    defer agent.allocator.destroy(agent);

    const msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const got_agent = agent.agent();
    const result = try got_agent.process(msg);
    defer result.ok.deinit();

    const num_nodes = result.ok.metadata.get("num_nodes").?.integer;
    try testing.expect(num_nodes <= 3);
}

test "GraphOfThought path_based aggregation" {
    const testing = std.testing;
    const MockAgent = @import("../../test_utils.zig").MockAgent;

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Premise A",
        "1. Thought 1",
        "",
        "SUPPORT",
        "Final conclusion",
    });
    defer mock.deinit();

    const config = GraphOfThoughtConfig{ .aggregator = .path_based };
    var agent = try GraphOfThoughtAgent.init(allocator, mock.agent(), config);
    defer agent.allocator.destroy(agent);

    const msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const got_agent = agent.agent();
    const result = try got_agent.process(msg);
    defer result.ok.deinit();

    try testing.expect(result.ok.content.string.len > 0);
}

test "GraphOfThought node_based aggregation" {
    const testing = std.testing;
    const MockAgent = @import("../../test_utils.zig").MockAgent;

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Premise A",
        "1. Thought 1",
        "",
        "SUPPORT",
        "Final conclusion",
    });
    defer mock.deinit();

    const config = GraphOfThoughtConfig{ .aggregator = .node_based };
    var agent = try GraphOfThoughtAgent.init(allocator, mock.agent(), config);
    defer agent.allocator.destroy(agent);

    const msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const got_agent = agent.agent();
    const result = try got_agent.process(msg);
    defer result.ok.deinit();

    try testing.expect(result.ok.content.string.len > 0);
}

test "GraphOfThought metadata completeness" {
    const testing = std.testing;
    const MockAgent = @import("../../test_utils.zig").MockAgent;

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Premise A",
        "1. Thought 1",
        "",
        "SUPPORT",
        "Final conclusion",
    });
    defer mock.deinit();

    const config = GraphOfThoughtConfig{};
    var agent = try GraphOfThoughtAgent.init(allocator, mock.agent(), config);
    defer agent.allocator.destroy(agent);

    const msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const got_agent = agent.agent();
    const result = try got_agent.process(msg);
    defer result.ok.deinit();

    // Check all required metadata fields
    try testing.expect(result.ok.metadata.contains("technique"));
    try testing.expect(result.ok.metadata.contains("num_nodes"));
    try testing.expect(result.ok.metadata.contains("num_edges"));
    try testing.expect(result.ok.metadata.contains("num_paths"));
}

test "AggregatorType enum values" {
    const testing = std.testing;

    try testing.expectEqual(AggregatorType.path_based, AggregatorType.path_based);
    try testing.expectEqual(AggregatorType.node_based, AggregatorType.node_based);
    try testing.expect(AggregatorType.path_based != AggregatorType.node_based);
}

test "GraphOfThought response role" {
    const testing = std.testing;
    const MockAgent = @import("../../test_utils.zig").MockAgent;

    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. Premise A",
        "1. Thought 1",
        "",
        "SUPPORT",
        "Final conclusion",
    });
    defer mock.deinit();

    const config = GraphOfThoughtConfig{};
    var agent = try GraphOfThoughtAgent.init(allocator, mock.agent(), config);
    defer agent.allocator.destroy(agent);

    const msg = try Message.withText(allocator, .user, "Test");
    defer msg.deinit();

    const got_agent = agent.agent();
    const result = try got_agent.process(msg);
    defer result.ok.deinit();

    try testing.expectEqual(Message.Role.assistant, result.ok.role);
}


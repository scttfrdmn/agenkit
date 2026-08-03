/// Tree-of-Thought Reasoning Technique
///
/// Tree-of-Thought explores multiple reasoning paths simultaneously through
/// tree search with branching, evaluation, pruning, and backtracking.
///
/// Reference: "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
/// Yao et al., 2023 - https://arxiv.org/abs/2305.10601
const std = @import("std");
const Agent = @import("../../agent.zig").Agent;
const AgentError = @import("../../agent.zig").AgentError;
const Result = @import("../../agent.zig").Result;
const Message = @import("../../message.zig").Message;
const CallOptions = @import("../../call_options.zig").CallOptions;
const ReasoningTree = @import("reasoning_tree.zig").ReasoningTree;
const NodeState = @import("reasoning_tree.zig").NodeState;
const Allocator = std.mem.Allocator;

/// Search strategy for tree exploration
pub const SearchStrategy = enum {
    bfs, // Breadth-first search (level by level)
    dfs, // Depth-first search (explore deeply first)
    best_first, // Best-first search (greedy, highest score first)
};

/// Function type for evaluating reasoning quality
pub const EvaluatorFunc = *const fn (text: []const u8) f64;

/// Bullet markers recognised at the start of a reasoning step.
///
/// Stored as strings, not bytes: "•" is U+2022, three bytes in UTF-8, so
/// `line[0] == '•'` compares a u8 against 8226 and is always false. That made
/// defaultEvaluator score every "•"-bulleted answer as unstructured.
const bullet_markers = [_][]const u8{ "-", "*", "•" };

/// Whether `text` starts with a bullet marker.
fn startsWithBullet(text: []const u8) bool {
    for (bullet_markers) |marker| {
        if (std.mem.startsWith(u8, text, marker)) return true;
    }
    return false;
}

/// Default evaluator based on text length and structure
pub fn defaultEvaluator(text: []const u8) f64 {
    if (text.len == 0) {
        return 0.0;
    }

    // Base score on length (normalized)
    const length_score = @min(@as(f64, @floatFromInt(text.len)) / 500.0, 1.0);

    // Bonus for structured content (numbered steps, bullet points)
    var structure_bonus: f64 = 0.0;

    // Count numbered steps
    var numbered_count: usize = 0;
    var lines = std.mem.splitScalar(u8, text, '\n');
    while (lines.next()) |line| {
        const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
        if (trimmed.len >= 2 and std.ascii.isDigit(trimmed[0])) {
            if (trimmed[1] == '.' or trimmed[1] == ')') {
                numbered_count += 1;
            }
        }
    }

    // Count bullet points
    var bullet_count: usize = 0;
    lines = std.mem.splitScalar(u8, text, '\n');
    while (lines.next()) |line| {
        const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
        if (startsWithBullet(trimmed)) {
            bullet_count += 1;
        }
    }

    if (numbered_count >= 2) {
        structure_bonus = 0.2;
    } else if (bullet_count >= 2) {
        structure_bonus = 0.15;
    }

    // Final score (capped at 1.0)
    return @min(length_score + structure_bonus, 1.0);
}

/// Configuration for Tree-of-Thought
pub const TreeOfThoughtConfig = struct {
    branching_factor: usize = 3,
    max_depth: usize = 5,
    evaluator: EvaluatorFunc = defaultEvaluator,
    strategy: SearchStrategy = .best_first,
    prune_threshold: f64 = 0.3,
};

/// Scored node for priority queue (used in best-first search)
const ScoredNode = struct {
    node_id: usize,
    score: f64,

    /// Order for the best-first frontier: highest score first.
    ///
    /// std.PriorityQueue expects a math.Order and pops the "least" element, so
    /// the comparison is inverted to make it a max-heap. The previous version
    /// returned `a.score < b.score`, which popped the *lowest*-scoring node —
    /// the opposite of best-first — while its comment claimed a max-heap was
    /// intended. Never caught because this file did not compile.
    pub fn compare(_: void, a: ScoredNode, b: ScoredNode) std.math.Order {
        return std.math.order(b.score, a.score);
    }
};

/// Tree-of-Thought agent
pub const TreeOfThoughtAgent = struct {
    allocator: Allocator,
    base_agent: Agent,
    config: TreeOfThoughtConfig,
    agent_name: []const u8,

    pub fn init(
        allocator: Allocator,
        base_agent: Agent,
        config: TreeOfThoughtConfig,
    ) !*TreeOfThoughtAgent {
        const self = try allocator.create(TreeOfThoughtAgent);
        self.* = TreeOfThoughtAgent{
            .allocator = allocator,
            .base_agent = base_agent,
            .config = config,
            .agent_name = "tree_of_thought",
        };
        return self;
    }

    pub fn agent(self: *TreeOfThoughtAgent) Agent {
        return Agent{
            .ptr = self,
            .vtable = &.{
                .name = nameImpl,
                .capabilities = capabilitiesImpl,
                .process = processImpl,
                .process_stream = processStreamImpl,
                .introspect = introspectImpl,
                .deinit = deinitImpl,
                .process_with = processWithImpl,
            },
        };
    }

    fn nameImpl(ptr: *anyopaque) []const u8 {
        const self: *TreeOfThoughtAgent = @ptrCast(@alignCast(ptr));
        return self.agent_name;
    }

    fn capabilitiesImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error![]const []const u8 {
        _ = ptr;
        const caps = try allocator.alloc([]const u8, 6);
        caps[0] = "reasoning";
        caps[1] = "tree_search";
        caps[2] = "multi_path_exploration";
        caps[3] = "backtracking";
        caps[4] = "tree_of_thought";
        caps[5] = "planning";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: Message) AgentError!Result {
        const self: *TreeOfThoughtAgent = @ptrCast(@alignCast(ptr));

        var empty = CallOptions.init(self.allocator);
        defer empty.deinit();
        return self.run(message, &empty);
    }

    /// Implements the optional `processWith` capability (#801).
    ///
    /// The options follow the search down every branch: all three strategies
    /// expand nodes recursively, and each expansion is a fresh set of LLM calls.
    /// Threading them into only the root expansion would leave the whole tree
    /// below depth 1 running at settings the caller never chose.
    fn processWithImpl(ptr: *anyopaque, message: Message, options: *const CallOptions) AgentError!Result {
        const self: *TreeOfThoughtAgent = @ptrCast(@alignCast(ptr));
        return self.run(message, options);
    }

    /// Shared body for both entry points.
    fn run(self: *TreeOfThoughtAgent, message: Message, options: *const CallOptions) AgentError!Result {
        const query = message.contentAsText() catch {
            return Result{ .err = AgentError.InvalidInput };
        };

        // Create reasoning tree
        var tree = ReasoningTree.init(self.allocator);
        defer tree.deinit();

        const root_id = tree.createRoot(query) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        // Perform search based on strategy
        switch (self.config.strategy) {
            .bfs => self.searchBFS(&tree, root_id, options) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            },
            .dfs => self.searchDFS(&tree, root_id, options) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            },
            .best_first => self.searchBestFirst(&tree, root_id, options) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            },
        }

        // Get best leaf node
        const best_leaf = tree.getBestLeaf() orelse {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        // Build response with best path
        const path = tree.getPath(best_leaf.id, self.allocator) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        defer self.allocator.free(path);

        const best_path_text = tree.getPathText(best_leaf.id, "\n", self.allocator) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };
        defer self.allocator.free(best_path_text);

        // Get statistics
        const stats = tree.getStatistics();

        // Create response message
        var response = Message.withText(self.allocator, .assistant, best_path_text) catch {
            return Result{ .err = AgentError.ProcessingFailed };
        };

        // Add metadata
        response.setMetadata("technique", .{ .string = "tree_of_thought" }) catch {};

        const strategy_str = switch (self.config.strategy) {
            .bfs => "bfs",
            .dfs => "dfs",
            .best_first => "best-first",
        };
        response.setMetadata("search_strategy", .{ .string = strategy_str }) catch {};
        response.setMetadata("num_steps", .{ .integer = @as(i64, @intCast(path.len)) }) catch {};
        response.setMetadata("best_score", .{ .float = best_leaf.score }) catch {};

        // Add tree stats
        response.setMetadata("total_nodes", .{ .integer = @as(i64, @intCast(stats.total_nodes)) }) catch {};
        response.setMetadata("max_depth", .{ .integer = @as(i64, @intCast(stats.max_depth)) }) catch {};
        response.setMetadata("num_leaves", .{ .integer = @as(i64, @intCast(stats.num_leaves)) }) catch {};
        response.setMetadata("num_pruned", .{ .integer = @as(i64, @intCast(stats.num_pruned)) }) catch {};

        return Result{ .ok = response };
    }

    fn processStreamImpl(ptr: *anyopaque, message: Message, callbacks: @import("../../agent.zig").StreamCallbacks) AgentError!void {
        _ = ptr;
        _ = message;
        _ = callbacks;
        return AgentError.NotImplemented;
    }

    fn introspectImpl(ptr: *anyopaque, allocator: Allocator) Allocator.Error!@import("../../introspection.zig").IntrospectionResult {
        const self: *TreeOfThoughtAgent = @ptrCast(@alignCast(ptr));
        const caps = try self.agent().capabilities(allocator);
        defer allocator.free(caps);
        return @import("../../introspection.zig").createDefaultIntrospectionResult(allocator, self.agent_name, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *TreeOfThoughtAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }

    /// Generate N varied reasoning branches for a prompt (sequential in Zig)
    fn generateBranches(self: *TreeOfThoughtAgent, prompt: []const u8, n: usize, options: *const CallOptions) ![][]const u8 {
        var branches = std.ArrayListUnmanaged([]const u8).empty;
        errdefer {
            for (branches.items) |branch| {
                self.allocator.free(branch);
            }
            branches.deinit(self.allocator);
        }

        var i: usize = 0;
        while (i < n) : (i += 1) {
            const varied_prompt = try std.fmt.allocPrint(
                self.allocator,
                "{s}\n\nAlternative approach #{d}:",
                .{ prompt, i + 1 },
            );
            defer self.allocator.free(varied_prompt);

            // Both messages must be freed on every path, including the
            // `continue`s. The previous version dropped the request message and
            // the response on the floor, leaking two Messages per branch.
            var msg = try Message.withText(self.allocator, .user, varied_prompt);
            defer msg.deinit();

            const result = self.base_agent.processWithOptions(msg, options) catch continue;
            var response_msg = result.unwrap() catch continue;
            defer response_msg.deinit();

            const branch_text = response_msg.contentAsText() catch continue;

            try branches.append(self.allocator, try self.allocator.dupe(u8, branch_text));
        }

        return try branches.toOwnedSlice(self.allocator);
    }

    /// Expand a tree node by generating and adding children
    fn expandNode(self: *TreeOfThoughtAgent, tree: *ReasoningTree, node_id: usize, options: *const CallOptions) ![]usize {
        const node = tree.getNode(node_id) orelse return error.NodeNotFound;

        // Don't expand pruned nodes
        if (node.state == .pruned) {
            return try self.allocator.alloc(usize, 0);
        }

        // Mark as active
        node.state = .active;

        // Generate branches
        const prompt = try tree.getPathText(node_id, "\n", self.allocator);
        defer self.allocator.free(prompt);

        const branches = try self.generateBranches(prompt, self.config.branching_factor, options);
        defer {
            for (branches) |branch| {
                self.allocator.free(branch);
            }
            self.allocator.free(branches);
        }

        var child_ids = std.ArrayListUnmanaged(usize).empty;
        errdefer child_ids.deinit(self.allocator);

        for (branches) |branch| {
            // Score the branch
            const score = self.config.evaluator(branch);

            // Prune if below threshold
            if (score < self.config.prune_threshold) {
                continue;
            }

            // Add child to tree
            const child_id = try tree.addChild(node_id, branch, score);
            try child_ids.append(self.allocator, child_id);

            if (tree.getNode(child_id)) |child| {
                child.state = .evaluated;
            }
        }

        // Mark node as evaluated.
        //
        // Re-fetch rather than reusing the `node` pointer taken at the top of
        // this function: `addChild` inserts into the tree's AutoHashMap, and a
        // rehash moves every entry, so that pointer may be dangling by now
        // (#817). `addChild` re-fetches its own parent pointer after its `put`
        // for the same reason.
        if (tree.getNode(node_id)) |evaluated| {
            evaluated.state = .evaluated;
        }

        return try child_ids.toOwnedSlice(self.allocator);
    }

    /// Perform breadth-first search on the tree
    fn searchBFS(self: *TreeOfThoughtAgent, tree: *ReasoningTree, root_id: usize, options: *const CallOptions) !void {
        var queue = std.ArrayListUnmanaged(usize).empty;
        defer queue.deinit(self.allocator);

        try queue.append(self.allocator, root_id);

        while (queue.items.len > 0) {
            const node_id = queue.orderedRemove(0);
            const node = tree.getNode(node_id) orelse continue;

            // Stop at max depth
            if (node.depth >= self.config.max_depth) {
                node.state = .terminal;
                continue;
            }

            // Expand node
            const children = try self.expandNode(tree, node_id, options);
            defer self.allocator.free(children);

            // Add children to queue
            for (children) |child_id| {
                try queue.append(self.allocator, child_id);
            }
        }
    }

    /// Perform depth-first search on the tree
    fn searchDFS(self: *TreeOfThoughtAgent, tree: *ReasoningTree, root_id: usize, options: *const CallOptions) !void {
        var stack = std.ArrayListUnmanaged(usize).empty;
        defer stack.deinit(self.allocator);

        try stack.append(self.allocator, root_id);

        // pop() returns ?usize, so it doubles as the loop condition.
        while (stack.pop()) |node_id| {
            const node = tree.getNode(node_id) orelse continue;

            // Stop at max depth
            if (node.depth >= self.config.max_depth) {
                node.state = .terminal;
                continue;
            }

            // Expand node
            const children = try self.expandNode(tree, node_id, options);
            defer self.allocator.free(children);

            // Add children to stack (reverse order for left-to-right DFS)
            var i = children.len;
            while (i > 0) {
                i -= 1;
                try stack.append(self.allocator, children[i]);
            }
        }
    }

    /// Perform best-first search on the tree
    fn searchBestFirst(self: *TreeOfThoughtAgent, tree: *ReasoningTree, root_id: usize, options: *const CallOptions) !void {
        var pq = std.PriorityQueue(ScoredNode, void, ScoredNode.compare).initContext({});
        defer pq.deinit(self.allocator);

        try pq.push(self.allocator, ScoredNode{ .node_id = root_id, .score = 0.0 });

        // pop() returns ?ScoredNode, so it doubles as the loop condition.
        while (pq.pop()) |scored| {
            const node = tree.getNode(scored.node_id) orelse continue;

            // Stop at max depth
            if (node.depth >= self.config.max_depth) {
                node.state = .terminal;
                continue;
            }

            // Expand node
            const children = try self.expandNode(tree, scored.node_id, options);
            defer self.allocator.free(children);

            // Add children to priority queue
            for (children) |child_id| {
                if (tree.getNode(child_id)) |child| {
                    try pq.push(self.allocator, ScoredNode{ .node_id = child_id, .score = child.score });
                }
            }
        }
    }
};

// ============================================================================
// Tests
// ============================================================================
//
// This file previously had no test blocks at all, which in Zig means it was
// never type-checked: `_ = @import(...)` only forces analysis of a file's test
// declarations, and a file with none is analysed not at all — which is how
// agent() shipped without compiling, and how the best-first frontier shipped
// as a min-heap (#811). The end-to-end tests below must go through the Agent
// vtable, not merely reference `agent()`, or the rot recurs.

const MockAgent = @import("../../test_utils.zig").MockAgent;
const Role = @import("../../message.zig").Role;
const StreamCallbacks = @import("../../agent.zig").StreamCallbacks;

/// Config that stops after one level so the tests stay small.
///
/// The default max_depth of 5 with a branching factor of 3 would expand into
/// hundreds of mock calls.
const shallow = TreeOfThoughtConfig{ .branching_factor = 2, .max_depth = 1, .prune_threshold = 0.0 };

test "TreeOfThought name and capabilities" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"branch"});
    defer mock.deinit();

    var tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), shallow);
    const tot_agent = tot.agent();
    defer tot_agent.deinit();

    try testing.expectEqualStrings("tree_of_thought", tot_agent.name());

    const caps = try tot_agent.capabilities(allocator);
    defer allocator.free(caps);
    try testing.expectEqual(@as(usize, 6), caps.len);
    try testing.expectEqualStrings("reasoning", caps[0]);
    try testing.expectEqualStrings("tree_search", caps[1]);
    try testing.expectEqualStrings("multi_path_exploration", caps[2]);
    try testing.expectEqualStrings("backtracking", caps[3]);
    try testing.expectEqualStrings("tree_of_thought", caps[4]);
    try testing.expectEqualStrings("planning", caps[5]);
}

test "TreeOfThought default config" {
    const testing = std.testing;

    const config = TreeOfThoughtConfig{};
    try testing.expectEqual(@as(usize, 3), config.branching_factor);
    try testing.expectEqual(@as(usize, 5), config.max_depth);
    try testing.expectEqual(SearchStrategy.best_first, config.strategy);
    try testing.expectEqual(@as(f64, 0.3), config.prune_threshold);
}

test "TreeOfThought end-to-end through the vtable" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{
        "1. step one\n2. step two\n3. step three",
    });
    defer mock.deinit();

    var tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), shallow);
    const tot_agent = tot.agent();
    defer tot_agent.deinit();

    var msg = try Message.withText(allocator, .user, "Solve this");
    defer msg.deinit();

    var response = try (try tot_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expectEqual(Role.assistant, response.role);
    try testing.expectEqualStrings("tree_of_thought", response.getMetadata("technique").?.string);
    try testing.expectEqualStrings("best-first", response.getMetadata("search_strategy").?.string);
    // Root plus the branch that won: the response is a root-to-leaf path.
    try testing.expectEqual(@as(i64, 2), response.getMetadata("num_steps").?.integer);
    try testing.expect(response.getMetadata("total_nodes").?.integer >= 2);
    try testing.expectEqual(@as(i64, 1), response.getMetadata("max_depth").?.integer);
    // The query is the root, so it heads the returned path.
    try testing.expect(std.mem.startsWith(u8, try response.contentAsText(), "Solve this\n"));
    try testing.expectEqual(@as(usize, shallow.branching_factor), mock.call_count);
}

test "TreeOfThought reports each search strategy" {
    const testing = std.testing;

    for ([_]struct { strategy: SearchStrategy, name: []const u8 }{
        .{ .strategy = .bfs, .name = "bfs" },
        .{ .strategy = .dfs, .name = "dfs" },
        .{ .strategy = .best_first, .name = "best-first" },
    }) |case| {
        var gpa = std.heap.DebugAllocator(.{}){};
        defer _ = gpa.deinit();
        const allocator = gpa.allocator();

        var mock = try MockAgent.init(allocator, &[_][]const u8{"1. a\n2. b"});
        defer mock.deinit();

        var config = shallow;
        config.strategy = case.strategy;
        var tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), config);
        const tot_agent = tot.agent();
        defer tot_agent.deinit();

        var msg = try Message.withText(allocator, .user, "q");
        defer msg.deinit();

        var response = try (try tot_agent.process(msg)).unwrap();
        defer response.deinit();

        try testing.expectEqualStrings(case.name, response.getMetadata("search_strategy").?.string);
    }
}

test "TreeOfThought prune_threshold drops low-scoring branches" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // defaultEvaluator scores by length, so a one-character branch scores far
    // below the threshold and every child is pruned.
    var mock = try MockAgent.init(allocator, &[_][]const u8{"x"});
    defer mock.deinit();

    var tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), .{
        .branching_factor = 2,
        .max_depth = 1,
        .prune_threshold = 0.9,
    });
    const tot_agent = tot.agent();
    defer tot_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var response = try (try tot_agent.process(msg)).unwrap();
    defer response.deinit();

    // Only the root survives, so it is both the best leaf and the whole path.
    try testing.expectEqual(@as(i64, 1), response.getMetadata("total_nodes").?.integer);
    try testing.expectEqual(@as(i64, 1), response.getMetadata("num_steps").?.integer);
    try testing.expectEqualStrings("q", try response.contentAsText());
}

test "TreeOfThought expands past the root under every strategy (#817)" {
    const testing = std.testing;

    // Regression test for #817: `expandNode` used to hold the `*ReasoningNode`
    // it fetched at entry across the `addChild` calls that insert into the
    // tree's AutoHashMap, then write `state = .evaluated` through it. A rehash
    // moves every entry, so that write segfaulted.
    //
    // Reaching it needs BOTH a depth past 1 and a threshold low enough to keep
    // a child alive — every other test in this file pins `max_depth = 1` (see
    // `shallow`) or leans on the default 0.3 threshold, which prunes the short
    // mock replies. So the assertion here is not "process returned" but "the
    // tree actually grew": a root-only tree cannot exercise the bug.
    for ([_]SearchStrategy{ .bfs, .dfs, .best_first }) |strategy| {
        const allocator = testing.allocator;

        var mock = try MockAgent.init(allocator, &[_][]const u8{"1. first\n2. second"});
        defer mock.deinit();

        const tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), .{
            .strategy = strategy,
            .branching_factor = 2,
            .max_depth = 3,
            .prune_threshold = 0.0,
        });
        const tot_agent = tot.agent();
        defer tot_agent.deinit();

        var msg = try Message.withText(allocator, .user, "Solve this");
        defer msg.deinit();

        var response = try (try tot_agent.process(msg)).unwrap();
        defer response.deinit();

        try testing.expect(response.getMetadata("max_depth").?.integer > 1);
        try testing.expect(response.getMetadata("total_nodes").?.integer > 3);
    }
}

test "defaultEvaluator scores empty text as zero" {
    const testing = std.testing;
    try testing.expectEqual(@as(f64, 0.0), defaultEvaluator(""));
}

test "defaultEvaluator rewards numbered structure" {
    const testing = std.testing;

    const plain = defaultEvaluator("aaaa");
    const numbered = defaultEvaluator("1. aa\n2. aa");
    // Same character budget, but the numbered form earns the structure bonus.
    try testing.expect(numbered > plain);
    try testing.expectApproxEqAbs(@as(f64, 0.2), numbered - defaultEvaluator("xx aa\nxx aa"), 1e-9);
}

test "defaultEvaluator rewards bullet structure including the multi-byte bullet" {
    const testing = std.testing;

    // "•" is U+2022, three bytes in UTF-8. A byte-wise `line[0] == '•'` compares
    // against 8226 and never fires, so these scored as unstructured. The
    // unbulleted control uses a three-byte prefix so the length score — which
    // counts bytes, not codepoints — cancels and only the bonus remains.
    const bulleted = defaultEvaluator("• first item\n• second item");
    const unbulleted = defaultEvaluator("xxx first item\nxxx second item");
    try testing.expectApproxEqAbs(@as(f64, 0.15), bulleted - unbulleted, 1e-9);

    // ASCII bullets must keep working too, against a one-byte control.
    const ascii_control = defaultEvaluator("x first item\nx second item");
    try testing.expectApproxEqAbs(
        @as(f64, 0.15),
        defaultEvaluator("- first item\n- second item") - ascii_control,
        1e-9,
    );
    try testing.expectApproxEqAbs(
        @as(f64, 0.15),
        defaultEvaluator("* first item\n* second item") - ascii_control,
        1e-9,
    );
}

test "defaultEvaluator prefers numbered over bulleted" {
    const testing = std.testing;

    // The numbered bonus is 0.2, the bullet bonus 0.15.
    const numbered = defaultEvaluator("1. aa\n2. bb");
    const bulleted = defaultEvaluator("-. aa\n-. bb");
    try testing.expect(numbered > bulleted);
}

test "defaultEvaluator caps at 1.0" {
    const testing = std.testing;

    var buf: [600]u8 = undefined;
    @memset(&buf, 'a');
    // 600 chars already saturates the length score before the bonus applies.
    try testing.expectEqual(@as(f64, 1.0), defaultEvaluator(&buf));
}

test "ScoredNode compare orders highest score first" {
    const testing = std.testing;

    const high = ScoredNode{ .node_id = 1, .score = 0.9 };
    const low = ScoredNode{ .node_id = 2, .score = 0.1 };

    // std.PriorityQueue pops the "least" element, so the higher score must
    // compare as .lt for the frontier to be best-first. The original returned
    // `a.score < b.score`, making it a min-heap.
    try testing.expectEqual(std.math.Order.lt, ScoredNode.compare({}, high, low));
    try testing.expectEqual(std.math.Order.gt, ScoredNode.compare({}, low, high));
    try testing.expectEqual(std.math.Order.eq, ScoredNode.compare({}, high, high));
}

test "ScoredNode compare drives a max-heap frontier" {
    const testing = std.testing;

    var pq = std.PriorityQueue(ScoredNode, void, ScoredNode.compare).initContext({});
    defer pq.deinit(testing.allocator);

    try pq.push(testing.allocator, .{ .node_id = 1, .score = 0.2 });
    try pq.push(testing.allocator, .{ .node_id = 2, .score = 0.9 });
    try pq.push(testing.allocator, .{ .node_id = 3, .score = 0.5 });

    // Best-first: descending score.
    try testing.expectEqual(@as(usize, 2), pq.pop().?.node_id);
    try testing.expectEqual(@as(usize, 3), pq.pop().?.node_id);
    try testing.expectEqual(@as(usize, 1), pq.pop().?.node_id);
    try testing.expectEqual(@as(?ScoredNode, null), pq.pop());
}

test "TreeOfThought custom evaluator is used" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const Fixed = struct {
        fn score(text: []const u8) f64 {
            _ = text;
            return 0.42;
        }
    };

    var mock = try MockAgent.init(allocator, &[_][]const u8{"branch text"});
    defer mock.deinit();

    var tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), .{
        .branching_factor = 1,
        .max_depth = 1,
        .evaluator = Fixed.score,
        .prune_threshold = 0.0,
    });
    const tot_agent = tot.agent();
    defer tot_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var response = try (try tot_agent.process(msg)).unwrap();
    defer response.deinit();

    // The custom score reaches the metadata, so the config field is honoured
    // rather than silently ignored in favour of defaultEvaluator.
    try testing.expectApproxEqAbs(@as(f64, 0.42), response.getMetadata("best_score").?.float, 1e-9);
}

test "TreeOfThought process_stream is not implemented" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), shallow);
    const tot_agent = tot.agent();
    defer tot_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var sink = TestSink{};
    try testing.expectError(
        AgentError.NotImplemented,
        tot_agent.processStream(msg, sink.callbacks()),
    );
    try testing.expectEqual(@as(usize, 0), sink.calls);
}

test "TreeOfThought introspection reports name and capabilities" {
    const testing = std.testing;

    var gpa = std.heap.DebugAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var mock = try MockAgent.init(allocator, &[_][]const u8{"unused"});
    defer mock.deinit();

    var tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), shallow);
    const tot_agent = tot.agent();
    defer tot_agent.deinit();

    var info = try tot_agent.introspect(allocator);
    defer info.deinit();

    try testing.expectEqualStrings("tree_of_thought", info.agent_name);
    try testing.expectEqual(@as(usize, 6), info.capabilities.len);
}

/// Callback sink that records that it was never invoked.
const TestSink = struct {
    calls: usize = 0,

    fn onMessage(ptr: *anyopaque, message: Message) void {
        _ = message;
        const self: *TestSink = @ptrCast(@alignCast(ptr));
        self.calls += 1;
    }

    fn onError(ptr: *anyopaque, err: AgentError) void {
        const self: *TestSink = @ptrCast(@alignCast(ptr));
        self.calls += 1;
        std.debug.assert(err != AgentError.Cancelled);
    }

    fn onComplete(ptr: *anyopaque) void {
        const self: *TestSink = @ptrCast(@alignCast(ptr));
        self.calls += 1;
    }

    fn callbacks(self: *TestSink) StreamCallbacks {
        return StreamCallbacks{
            .ptr = self,
            .on_message_fn = onMessage,
            .on_error_fn = onError,
            .on_complete_fn = onComplete,
        };
    }
};

// ============================================================================
// Per-call options forwarding (#801)
// ============================================================================

const OptionsAwareMockAgent = @import("../../test_utils.zig").OptionsAwareMockAgent;

test "TreeOfThought forwards call options under every search strategy" {
    const testing = std.testing;

    // All three strategies expand nodes recursively, and each expansion is a
    // fresh batch of LLM calls. Threading the options into only the root
    // expansion would leave the whole tree below depth 1 running at settings the
    // caller never chose — so each strategy is checked, not just the default.
    for ([_]SearchStrategy{ .bfs, .dfs, .best_first }) |strategy| {
        const allocator = testing.allocator;

        var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{
            "A promising thought",
            "Another thought",
        });
        defer mock.deinit();

        // prune_threshold 0.0 keeps the short mock replies alive: the default
        // evaluator scores mainly on length, so with the default threshold every
        // branch is pruned and the tree never leaves the root. That is what made
        // the first draft of this test vacuous — a root-only forward passed it.
        const tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), .{
            .strategy = strategy,
            .branching_factor = 2,
            .max_depth = 3,
            .prune_threshold = 0.0,
        });
        const tot_agent = tot.agent();
        defer tot_agent.deinit();

        var msg = try Message.withText(allocator, .user, "A problem");
        defer msg.deinit();

        var options = CallOptions.init(allocator);
        defer options.deinit();
        try options.withTemperature(0.75);

        var response = try (try tot_agent.processWith(msg, &options)).unwrap();
        defer response.deinit();

        // "Every call forwarded" is trivially true for a tree that only ever
        // expanded its root, so assert the recursion actually happened: a depth
        // past 1 means at least one non-root expansion issued LLM calls.
        try testing.expect(response.getMetadata("max_depth").?.integer > 1);
        try testing.expect(mock.getCallCount() > 2);
        try testing.expect(mock.allTemperaturesEqual(0.75));
    }
}

test "TreeOfThought sends no options when called through process" {
    const testing = std.testing;
    const allocator = testing.allocator;

    var mock = try OptionsAwareMockAgent.init(allocator, &[_][]const u8{"A thought"});
    defer mock.deinit();

    const tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), .{
        .branching_factor = 2,
        .max_depth = 2,
    });
    const tot_agent = tot.agent();
    defer tot_agent.deinit();

    var msg = try Message.withText(allocator, .user, "q");
    defer msg.deinit();

    var response = try (try tot_agent.process(msg)).unwrap();
    defer response.deinit();

    try testing.expect(mock.allTemperaturesEqual(null));
}

test "TreeOfThought advertises the options capability" {
    const testing = std.testing;
    const allocator = testing.allocator;

    var mock = try MockAgent.init(allocator, &[_][]const u8{"A thought"});
    defer mock.deinit();

    const tot = try TreeOfThoughtAgent.init(allocator, mock.agent(), .{});
    const tot_agent = tot.agent();
    defer tot_agent.deinit();

    try testing.expect(tot_agent.supportsOptions());
}

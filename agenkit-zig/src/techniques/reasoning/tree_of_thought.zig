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
    var lines = std.mem.split(u8, text, "\n");
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
    lines = std.mem.split(u8, text, "\n");
    while (lines.next()) |line| {
        const trimmed = std.mem.trim(u8, line, &std.ascii.whitespace);
        if (trimmed.len > 0) {
            if (trimmed[0] == '-' or trimmed[0] == '*' or trimmed[0] == '•') {
                bullet_count += 1;
            }
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

    pub fn lessThan(_: void, a: ScoredNode, b: ScoredNode) bool {
        return a.score < b.score; // Min-heap (we want max, so reverse comparison)
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
                .deinit = deinitImpl,
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
            .bfs => self.searchBFS(&tree, root_id) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            },
            .dfs => self.searchDFS(&tree, root_id) catch {
                return Result{ .err = AgentError.ProcessingFailed };
            },
            .best_first => self.searchBestFirst(&tree, root_id) catch {
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

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *TreeOfThoughtAgent = @ptrCast(@alignCast(ptr));
        self.allocator.destroy(self);
    }

    /// Generate N varied reasoning branches for a prompt (sequential in Zig)
    fn generateBranches(self: *TreeOfThoughtAgent, prompt: []const u8, n: usize) ![][]const u8 {
        var branches = std.ArrayList([]const u8).empty;
        errdefer {
            for (branches.items) |branch| {
                self.allocator.free(branch);
            }
            branches.deinit();
        }

        var i: usize = 0;
        while (i < n) : (i += 1) {
            const varied_prompt = try std.fmt.allocPrint(
                self.allocator,
                "{s}\n\nAlternative approach #{d}:",
                .{ prompt, i + 1 },
            );
            defer self.allocator.free(varied_prompt);

            const msg = try Message.withText(self.allocator, .user, varied_prompt);
            const result = self.base_agent.process(msg) catch continue;
            const response_msg = result.unwrap() catch continue;
            const branch_text = response_msg.contentAsText() catch continue;

            try branches.append(try self.allocator.dupe(u8, branch_text));
        }

        return try branches.toOwnedSlice();
    }

    /// Expand a tree node by generating and adding children
    fn expandNode(self: *TreeOfThoughtAgent, tree: *ReasoningTree, node_id: usize) ![]usize {
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

        const branches = try self.generateBranches(prompt, self.config.branching_factor);
        defer {
            for (branches) |branch| {
                self.allocator.free(branch);
            }
            self.allocator.free(branches);
        }

        var child_ids = std.ArrayList(usize).empty;
        errdefer child_ids.deinit();

        for (branches) |branch| {
            // Score the branch
            const score = self.config.evaluator(branch);

            // Prune if below threshold
            if (score < self.config.prune_threshold) {
                continue;
            }

            // Add child to tree
            const child_id = try tree.addChild(node_id, branch, score);
            try child_ids.append(child_id);

            if (tree.getNode(child_id)) |child| {
                child.state = .evaluated;
            }
        }

        // Mark node as evaluated
        node.state = .evaluated;

        return try child_ids.toOwnedSlice();
    }

    /// Perform breadth-first search on the tree
    fn searchBFS(self: *TreeOfThoughtAgent, tree: *ReasoningTree, root_id: usize) !void {
        var queue = std.ArrayList(usize).empty;
        defer queue.deinit();

        try queue.append(root_id);

        while (queue.items.len > 0) {
            const node_id = queue.orderedRemove(0);
            const node = tree.getNode(node_id) orelse continue;

            // Stop at max depth
            if (node.depth >= self.config.max_depth) {
                node.state = .terminal;
                continue;
            }

            // Expand node
            const children = try self.expandNode(tree, node_id);
            defer self.allocator.free(children);

            // Add children to queue
            for (children) |child_id| {
                try queue.append(child_id);
            }
        }
    }

    /// Perform depth-first search on the tree
    fn searchDFS(self: *TreeOfThoughtAgent, tree: *ReasoningTree, root_id: usize) !void {
        var stack = std.ArrayList(usize).empty;
        defer stack.deinit();

        try stack.append(root_id);

        while (stack.items.len > 0) {
            const node_id = stack.pop();
            const node = tree.getNode(node_id) orelse continue;

            // Stop at max depth
            if (node.depth >= self.config.max_depth) {
                node.state = .terminal;
                continue;
            }

            // Expand node
            const children = try self.expandNode(tree, node_id);
            defer self.allocator.free(children);

            // Add children to stack (reverse order for left-to-right DFS)
            var i = children.len;
            while (i > 0) {
                i -= 1;
                try stack.append(children[i]);
            }
        }
    }

    /// Perform best-first search on the tree
    fn searchBestFirst(self: *TreeOfThoughtAgent, tree: *ReasoningTree, root_id: usize) !void {
        var pq = std.PriorityQueue(ScoredNode, void, ScoredNode.lessThan).init(self.allocator, {});
        defer pq.deinit();

        try pq.add(ScoredNode{ .node_id = root_id, .score = 0.0 });

        while (pq.removeOrNull()) |scored| {
            const node = tree.getNode(scored.node_id) orelse continue;

            // Stop at max depth
            if (node.depth >= self.config.max_depth) {
                node.state = .terminal;
                continue;
            }

            // Expand node
            const children = try self.expandNode(tree, scored.node_id);
            defer self.allocator.free(children);

            // Add children to priority queue
            for (children) |child_id| {
                if (tree.getNode(child_id)) |child| {
                    try pq.add(ScoredNode{ .node_id = child_id, .score = child.score });
                }
            }
        }
    }
};

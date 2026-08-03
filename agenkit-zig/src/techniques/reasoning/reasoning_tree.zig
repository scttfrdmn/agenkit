/// Reasoning Tree Data Structure for Tree-of-Thought
///
/// Provides a tree structure for exploring multiple reasoning paths with
/// branching, evaluation, pruning, and backtracking capabilities.
const std = @import("std");
const Allocator = std.mem.Allocator;

/// State of a reasoning node in the tree
pub const NodeState = enum {
    open, // Node created but not yet explored
    active, // Node currently being explored
    evaluated, // Node has been scored but not yet pruned/terminated
    pruned, // Node pruned due to low score
    terminal, // Node is a leaf/endpoint
};

/// Individual node in the reasoning tree
pub const ReasoningNode = struct {
    id: usize,
    content: []const u8,
    parent_id: ?usize,
    children_ids: std.ArrayListUnmanaged(usize),
    depth: usize,
    score: f64,
    state: NodeState,

    pub fn isLeaf(self: *const ReasoningNode) bool {
        return self.children_ids.items.len == 0;
    }

    pub fn isRoot(self: *const ReasoningNode) bool {
        return self.parent_id == null;
    }

    pub fn deinit(self: *ReasoningNode, allocator: Allocator) void {
        allocator.free(self.content);
        self.children_ids.deinit(allocator);
    }
};

/// Statistics about the reasoning tree
pub const TreeStatistics = struct {
    total_nodes: usize,
    max_depth: usize,
    num_leaves: usize,
    num_pruned: usize,
    best_score: f64,
    avg_score: f64,
};

/// Tree structure for multi-path reasoning exploration
pub const ReasoningTree = struct {
    allocator: Allocator,
    nodes: std.AutoHashMap(usize, ReasoningNode),
    root_id: ?usize,
    next_id: usize,
    max_depth: usize,

    pub fn init(allocator: Allocator) ReasoningTree {
        return ReasoningTree{
            .allocator = allocator,
            .nodes = std.AutoHashMap(usize, ReasoningNode).init(allocator),
            .root_id = null,
            .next_id = 0,
            .max_depth = 0,
        };
    }

    pub fn deinit(self: *ReasoningTree) void {
        var it = self.nodes.valueIterator();
        while (it.next()) |node| {
            var mutable_node = node.*;
            mutable_node.deinit(self.allocator);
        }
        self.nodes.deinit();
    }

    /// Create the root node of the tree
    pub fn createRoot(self: *ReasoningTree, content: []const u8) !usize {
        const node_id = self.next_id;
        self.next_id += 1;

        const node = ReasoningNode{
            .id = node_id,
            .content = try self.allocator.dupe(u8, content),
            .parent_id = null,
            .children_ids = std.ArrayListUnmanaged(usize).empty,
            .depth = 0,
            .score = 0.0,
            .state = .open,
        };

        try self.nodes.put(node_id, node);
        self.root_id = node_id;
        self.max_depth = 0;

        return node_id;
    }

    /// Add a child node to a parent
    pub fn addChild(
        self: *ReasoningTree,
        parent_id: usize,
        content: []const u8,
        score: f64,
    ) !usize {
        const parent = self.nodes.getPtr(parent_id) orelse return error.ParentNotFound;
        const parent_depth = parent.depth;

        const child_id = self.next_id;
        self.next_id += 1;

        const child = ReasoningNode{
            .id = child_id,
            .content = try self.allocator.dupe(u8, content),
            .parent_id = parent_id,
            .children_ids = std.ArrayListUnmanaged(usize).empty,
            .depth = parent_depth + 1,
            .score = score,
            .state = .open,
        };

        if (child.depth > self.max_depth) {
            self.max_depth = child.depth;
        }

        try self.nodes.put(child_id, child);

        // Add child to parent's children list
        const parent_ptr = self.nodes.getPtr(parent_id).?;
        try parent_ptr.children_ids.append(self.allocator, child_id);

        return child_id;
    }

    /// Get a node by ID
    pub fn getNode(self: *ReasoningTree, node_id: usize) ?*ReasoningNode {
        return self.nodes.getPtr(node_id);
    }

    /// Get the path from root to a specific node
    pub fn getPath(self: *ReasoningTree, node_id: usize, allocator: Allocator) ![]const *const ReasoningNode {
        var path = std.ArrayListUnmanaged(*const ReasoningNode).empty;
        errdefer path.deinit(allocator);

        var current_id: ?usize = node_id;
        while (current_id) |id| {
            if (self.nodes.getPtr(id)) |node| {
                try path.append(allocator, node);
                current_id = node.parent_id;
            } else {
                break;
            }
        }

        // Reverse to get root-to-leaf order
        std.mem.reverse(*const ReasoningNode, path.items);

        return try path.toOwnedSlice(allocator);
    }

    /// Get path content as concatenated text
    pub fn getPathText(
        self: *ReasoningTree,
        node_id: usize,
        delimiter: []const u8,
        allocator: Allocator,
    ) ![]u8 {
        const path = try self.getPath(node_id, allocator);
        defer allocator.free(path);

        if (path.len == 0) {
            return try allocator.dupe(u8, "");
        }

        // Calculate total size needed
        var total_size: usize = 0;
        for (path) |node| {
            total_size += node.content.len;
        }
        total_size += delimiter.len * (path.len - 1); // Delimiters between nodes

        // Build result string
        var result = try allocator.alloc(u8, total_size);
        var pos: usize = 0;

        for (path, 0..) |node, i| {
            @memcpy(result[pos .. pos + node.content.len], node.content);
            pos += node.content.len;

            if (i < path.len - 1) {
                @memcpy(result[pos .. pos + delimiter.len], delimiter);
                pos += delimiter.len;
            }
        }

        return result;
    }

    /// Find the best leaf node (highest score)
    pub fn getBestLeaf(self: *ReasoningTree) ?*ReasoningNode {
        var best_node: ?*ReasoningNode = null;
        var best_score: f64 = -1.0;

        var it = self.nodes.valueIterator();
        while (it.next()) |node| {
            if (node.isLeaf() and node.state != .pruned) {
                if (best_node == null or node.score > best_score) {
                    best_node = node;
                    best_score = node.score;
                }
            }
        }

        return best_node;
    }

    /// Prune a node and all its descendants
    pub fn pruneNode(self: *ReasoningTree, node_id: usize) void {
        self.pruneRecursive(node_id);
    }

    fn pruneRecursive(self: *ReasoningTree, node_id: usize) void {
        if (self.nodes.getPtr(node_id)) |node| {
            // Make a copy of children IDs before marking as pruned
            var children_copy = node.children_ids.clone(self.allocator) catch return;
            defer children_copy.deinit(self.allocator);

            // Mark this node as pruned
            node.state = .pruned;

            // Recursively prune all children
            for (children_copy.items) |child_id| {
                self.pruneRecursive(child_id);
            }
        }
    }

    /// Get statistics about the tree
    pub fn getStatistics(self: *ReasoningTree) TreeStatistics {
        var num_leaves: usize = 0;
        var num_pruned: usize = 0;
        var best_score: f64 = 0.0;
        var sum_scores: f64 = 0.0;
        var scored_nodes: usize = 0;

        var it = self.nodes.valueIterator();
        while (it.next()) |node| {
            if (node.isLeaf()) {
                num_leaves += 1;
            }

            if (node.state == .pruned) {
                num_pruned += 1;
            }

            // Track scores (exclude root which has score 0.0)
            if (!node.isRoot()) {
                sum_scores += node.score;
                scored_nodes += 1;
                if (node.score > best_score) {
                    best_score = node.score;
                }
            }
        }

        const avg_score = if (scored_nodes > 0)
            sum_scores / @as(f64, @floatFromInt(scored_nodes))
        else
            0.0;

        return TreeStatistics{
            .total_nodes = self.nodes.count(),
            .max_depth = self.max_depth,
            .num_leaves = num_leaves,
            .num_pruned = num_pruned,
            .best_score = best_score,
            .avg_score = avg_score,
        };
    }
};

// ============================================================================
// Tests
// ============================================================================
//
// This file previously had no test blocks at all, which in Zig means it was
// never type-checked: `_ = @import(...)` only forces analysis of a file's test
// declarations, and a file with none is analysed not at all (#811).

test "ReasoningTree createRoot" {
    const testing = std.testing;

    var tree = ReasoningTree.init(testing.allocator);
    defer tree.deinit();

    const root_id = try tree.createRoot("the question");

    try testing.expectEqual(@as(?usize, root_id), tree.root_id);
    const root = tree.getNode(root_id).?;
    try testing.expectEqualStrings("the question", root.content);
    try testing.expectEqual(@as(usize, 0), root.depth);
    try testing.expect(root.isRoot());
    try testing.expect(root.isLeaf());
    try testing.expectEqual(NodeState.open, root.state);
}

test "ReasoningTree addChild tracks depth and parentage" {
    const testing = std.testing;

    var tree = ReasoningTree.init(testing.allocator);
    defer tree.deinit();

    const root_id = try tree.createRoot("root");
    const child_id = try tree.addChild(root_id, "child", 0.5);
    const grandchild_id = try tree.addChild(child_id, "grandchild", 0.7);

    const child = tree.getNode(child_id).?;
    try testing.expectEqual(@as(?usize, root_id), child.parent_id);
    try testing.expectEqual(@as(usize, 1), child.depth);
    try testing.expect(!child.isLeaf());

    const grandchild = tree.getNode(grandchild_id).?;
    try testing.expectEqual(@as(usize, 2), grandchild.depth);
    try testing.expectEqual(@as(f64, 0.7), grandchild.score);

    // The parent's children list is updated, not just the child's parent_id.
    const root = tree.getNode(root_id).?;
    try testing.expectEqual(@as(usize, 1), root.children_ids.items.len);
    try testing.expectEqual(child_id, root.children_ids.items[0]);

    try testing.expectEqual(@as(usize, 2), tree.max_depth);
}

test "ReasoningTree addChild rejects a missing parent" {
    const testing = std.testing;

    var tree = ReasoningTree.init(testing.allocator);
    defer tree.deinit();

    try testing.expectError(error.ParentNotFound, tree.addChild(99, "orphan", 0.5));
}

test "ReasoningTree getPath is root-to-leaf" {
    const testing = std.testing;

    var tree = ReasoningTree.init(testing.allocator);
    defer tree.deinit();

    const root_id = try tree.createRoot("a");
    const child_id = try tree.addChild(root_id, "b", 0.5);
    const leaf_id = try tree.addChild(child_id, "c", 0.9);

    const path = try tree.getPath(leaf_id, testing.allocator);
    defer testing.allocator.free(path);

    // Walked parent-ward then reversed, so the order must be root-first.
    try testing.expectEqual(@as(usize, 3), path.len);
    try testing.expectEqualStrings("a", path[0].content);
    try testing.expectEqualStrings("b", path[1].content);
    try testing.expectEqualStrings("c", path[2].content);
}

test "ReasoningTree getPathText joins with the delimiter" {
    const testing = std.testing;

    var tree = ReasoningTree.init(testing.allocator);
    defer tree.deinit();

    const root_id = try tree.createRoot("first");
    const child_id = try tree.addChild(root_id, "second", 0.5);

    const text = try tree.getPathText(child_id, " -> ", testing.allocator);
    defer testing.allocator.free(text);
    try testing.expectEqualStrings("first -> second", text);

    // A single node gets no trailing delimiter.
    const root_text = try tree.getPathText(root_id, " -> ", testing.allocator);
    defer testing.allocator.free(root_text);
    try testing.expectEqualStrings("first", root_text);
}

test "ReasoningTree getBestLeaf skips pruned and non-leaf nodes" {
    const testing = std.testing;

    var tree = ReasoningTree.init(testing.allocator);
    defer tree.deinit();

    const root_id = try tree.createRoot("root");
    const mid_id = try tree.addChild(root_id, "middle", 0.99);
    _ = try tree.addChild(mid_id, "weak leaf", 0.2);
    const strong_id = try tree.addChild(root_id, "strong leaf", 0.8);
    const pruned_id = try tree.addChild(root_id, "pruned leaf", 0.95);
    tree.pruneNode(pruned_id);

    // "middle" scores highest but is not a leaf; "pruned leaf" scores higher
    // still but is pruned.
    const best = tree.getBestLeaf().?;
    try testing.expectEqual(strong_id, best.id);
    try testing.expectEqualStrings("strong leaf", best.content);
}

test "ReasoningTree getBestLeaf returns null on an empty tree" {
    const testing = std.testing;

    var tree = ReasoningTree.init(testing.allocator);
    defer tree.deinit();

    try testing.expectEqual(@as(?*ReasoningNode, null), tree.getBestLeaf());
}

test "ReasoningTree pruneNode prunes descendants too" {
    const testing = std.testing;

    var tree = ReasoningTree.init(testing.allocator);
    defer tree.deinit();

    const root_id = try tree.createRoot("root");
    const branch_id = try tree.addChild(root_id, "branch", 0.5);
    const leaf_a = try tree.addChild(branch_id, "leaf a", 0.6);
    const leaf_b = try tree.addChild(branch_id, "leaf b", 0.7);
    const sibling_id = try tree.addChild(root_id, "sibling", 0.4);

    tree.pruneNode(branch_id);

    try testing.expectEqual(NodeState.pruned, tree.getNode(branch_id).?.state);
    try testing.expectEqual(NodeState.pruned, tree.getNode(leaf_a).?.state);
    try testing.expectEqual(NodeState.pruned, tree.getNode(leaf_b).?.state);
    // The unrelated subtree is untouched.
    try testing.expectEqual(NodeState.open, tree.getNode(sibling_id).?.state);
}

test "ReasoningTree getStatistics excludes the root from scores" {
    const testing = std.testing;

    var tree = ReasoningTree.init(testing.allocator);
    defer tree.deinit();

    const root_id = try tree.createRoot("root");
    _ = try tree.addChild(root_id, "a", 0.4);
    const b_id = try tree.addChild(root_id, "b", 0.8);
    const pruned_id = try tree.addChild(b_id, "c", 0.6);
    tree.pruneNode(pruned_id);

    const stats = tree.getStatistics();
    try testing.expectEqual(@as(usize, 4), stats.total_nodes);
    try testing.expectEqual(@as(usize, 2), stats.max_depth);
    // Leaves: "a" and "c". "b" has a child, root has two.
    try testing.expectEqual(@as(usize, 2), stats.num_leaves);
    try testing.expectEqual(@as(usize, 1), stats.num_pruned);
    try testing.expectEqual(@as(f64, 0.8), stats.best_score);
    // (0.4 + 0.8 + 0.6) / 3 — the root's 0.0 must not drag the mean down.
    try testing.expectApproxEqAbs(@as(f64, 0.6), stats.avg_score, 1e-9);
}

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
    children_ids: std.ArrayList(usize),
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
        self.children_ids.deinit();
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
            .children_ids = std.ArrayList(usize).empty,
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
            .children_ids = std.ArrayList(usize).empty,
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
        try parent_ptr.children_ids.append(child_id);

        return child_id;
    }

    /// Get a node by ID
    pub fn getNode(self: *ReasoningTree, node_id: usize) ?*ReasoningNode {
        return self.nodes.getPtr(node_id);
    }

    /// Get the path from root to a specific node
    pub fn getPath(self: *ReasoningTree, node_id: usize, allocator: Allocator) ![]const *const ReasoningNode {
        var path = std.ArrayList(*const ReasoningNode).empty;
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
            const children_copy = node.children_ids.clone() catch return;
            defer children_copy.deinit();

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

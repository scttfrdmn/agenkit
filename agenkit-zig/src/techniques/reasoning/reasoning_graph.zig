/// Reasoning Graph Data Structure for Graph-of-Thought
///
/// Provides a directed graph structure for representing reasoning as nodes
/// (thoughts/conclusions) connected by edges (logical relationships).
///
/// This is more flexible than tree-based approaches, allowing for:
/// - Multiple reasoning paths
/// - Complex dependencies
/// - Cycle detection for circular reasoning
/// - Path aggregation
///
/// Reference: Graph-of-Thought paper: https://arxiv.org/abs/2308.09687
const std = @import("std");
const Allocator = std.mem.Allocator;

/// Type of thought node in the graph
pub const NodeType = enum {
    premise,
    intermediate,
    conclusion,
};

/// Type of logical connection between nodes
pub const EdgeType = enum {
    supports,
    depends_on,
    contradicts,
    refines,
};

/// A single thought or conclusion in the reasoning graph
pub const ThoughtNode = struct {
    id: usize,
    content: []const u8,
    node_type: NodeType,
    confidence: f64,

    pub fn deinit(self: *ThoughtNode, allocator: Allocator) void {
        allocator.free(self.content);
    }
};

/// A logical connection between two thoughts
pub const LogicalEdge = struct {
    from_node: usize,
    to_node: usize,
    edge_type: EdgeType,
    strength: f64,
};

/// Graph statistics for analysis
pub const GraphStatistics = struct {
    num_nodes: usize,
    num_edges: usize,
    has_cycles: bool,
    premise_count: usize,
    intermediate_count: usize,
    conclusion_count: usize,
};

/// Directed graph for representing reasoning structures
pub const ReasoningGraph = struct {
    allocator: Allocator,
    nodes: std.AutoHashMap(usize, ThoughtNode),
    edges: std.ArrayListUnmanaged(LogicalEdge),
    next_id: usize,
    outgoing: std.AutoHashMap(usize, std.ArrayListUnmanaged(usize)),
    incoming: std.AutoHashMap(usize, std.ArrayListUnmanaged(usize)),

    pub fn init(allocator: Allocator) ReasoningGraph {
        return ReasoningGraph{
            .allocator = allocator,
            .nodes = std.AutoHashMap(usize, ThoughtNode).init(allocator),
            .edges = std.ArrayListUnmanaged(LogicalEdge).empty,
            .next_id = 0,
            .outgoing = std.AutoHashMap(usize, std.ArrayListUnmanaged(usize)).init(allocator),
            .incoming = std.AutoHashMap(usize, std.ArrayListUnmanaged(usize)).init(allocator),
        };
    }

    pub fn deinit(self: *ReasoningGraph) void {
        var node_iter = self.nodes.valueIterator();
        while (node_iter.next()) |node| {
            var mutable_node = node.*;
            mutable_node.deinit(self.allocator);
        }
        self.nodes.deinit();
        self.edges.deinit(self.allocator);

        var out_iter = self.outgoing.valueIterator();
        while (out_iter.next()) |list| {
            list.deinit(self.allocator);
        }
        self.outgoing.deinit();

        var in_iter = self.incoming.valueIterator();
        while (in_iter.next()) |list| {
            list.deinit(self.allocator);
        }
        self.incoming.deinit();
    }

    /// Add a thought node to the graph
    pub fn addNode(self: *ReasoningGraph, content: []const u8, node_type: NodeType, confidence: f64) !usize {
        // Every fallible step happens before the first mutation, so a failure
        // leaves the graph exactly as it was. Previously the content dupe came
        // first and `nodes.put` could fail after it, leaking the copy — and
        // next_id advanced even then, so a failed add burned an id.
        try self.nodes.ensureUnusedCapacity(1);
        try self.outgoing.ensureUnusedCapacity(1);
        try self.incoming.ensureUnusedCapacity(1);

        const content_copy = try self.allocator.dupe(u8, content);

        const node_id = self.next_id;
        const node = ThoughtNode{
            .id = node_id,
            .content = content_copy,
            .node_type = node_type,
            .confidence = confidence,
        };

        self.nodes.putAssumeCapacity(node_id, node);
        self.outgoing.putAssumeCapacity(node_id, std.ArrayListUnmanaged(usize).empty);
        self.incoming.putAssumeCapacity(node_id, std.ArrayListUnmanaged(usize).empty);
        self.next_id += 1;

        return node_id;
    }

    /// Add a logical edge between two nodes
    pub fn addEdge(self: *ReasoningGraph, from_node: usize, to_node: usize, edge_type: EdgeType, strength: f64) !void {
        if (!self.nodes.contains(from_node) or !self.nodes.contains(to_node)) {
            return error.NodeNotFound;
        }

        const out_list = self.outgoing.getPtr(from_node).?;
        const in_list = self.incoming.getPtr(to_node).?;

        // Reserve all three slots up front. The previous version appended to
        // `edges` first, so a failure in either adjacency list left the edge
        // recorded in `edges` but invisible to traversal — statistics and
        // findPaths would then disagree about the graph's shape.
        try self.edges.ensureUnusedCapacity(self.allocator, 1);
        try out_list.ensureUnusedCapacity(self.allocator, 1);
        try in_list.ensureUnusedCapacity(self.allocator, 1);

        self.edges.appendAssumeCapacity(LogicalEdge{
            .from_node = from_node,
            .to_node = to_node,
            .edge_type = edge_type,
            .strength = strength,
        });
        out_list.appendAssumeCapacity(to_node);
        in_list.appendAssumeCapacity(from_node);
    }

    /// Get node by ID
    pub fn getNode(self: *const ReasoningGraph, node_id: usize) ?*const ThoughtNode {
        return self.nodes.getPtr(node_id);
    }

    /// Get all premise nodes
    pub fn getPremises(self: *const ReasoningGraph, allocator: Allocator) ![]const *const ThoughtNode {
        var premises = std.ArrayListUnmanaged(*const ThoughtNode).empty;
        defer premises.deinit(allocator);

        var iter = self.nodes.valueIterator();
        while (iter.next()) |node| {
            if (node.node_type == .premise) {
                try premises.append(allocator, node);
            }
        }

        return try premises.toOwnedSlice(allocator);
    }

    /// Get all conclusion nodes
    pub fn getConclusions(self: *const ReasoningGraph, allocator: Allocator) ![]const *const ThoughtNode {
        var conclusions = std.ArrayListUnmanaged(*const ThoughtNode).empty;
        defer conclusions.deinit(allocator);

        var iter = self.nodes.valueIterator();
        while (iter.next()) |node| {
            if (node.node_type == .conclusion) {
                try conclusions.append(allocator, node);
            }
        }

        return try conclusions.toOwnedSlice(allocator);
    }

    /// Find all paths from start to end node
    pub fn findPaths(self: *const ReasoningGraph, allocator: Allocator, start: usize, end: usize, max_length: usize) ![][]usize {
        // toOwnedSlice() empties the list on success, so this defer only frees
        // the accumulated paths on the error return.
        var paths = std.ArrayListUnmanaged([]usize).empty;
        defer {
            for (paths.items) |path| {
                allocator.free(path);
            }
            paths.deinit(allocator);
        }

        var visited = std.AutoHashMap(usize, void).init(allocator);
        defer visited.deinit();

        var current_path = std.ArrayListUnmanaged(usize).empty;
        defer current_path.deinit(allocator);

        try self.dfsPath(allocator, start, end, max_length, &visited, &current_path, &paths);

        return try paths.toOwnedSlice(allocator);
    }

    fn dfsPath(
        self: *const ReasoningGraph,
        allocator: Allocator,
        current: usize,
        end: usize,
        max_length: usize,
        visited: *std.AutoHashMap(usize, void),
        path: *std.ArrayListUnmanaged(usize),
        paths: *std.ArrayListUnmanaged([]usize),
    ) !void {
        if (path.items.len > max_length) {
            return;
        }

        if (current == end) {
            const complete_path = try allocator.alloc(usize, path.items.len + 1);
            errdefer allocator.free(complete_path);
            @memcpy(complete_path[0..path.items.len], path.items);
            complete_path[path.items.len] = current;
            try paths.append(allocator, complete_path);
            return;
        }

        if (visited.contains(current)) {
            return;
        }

        try visited.put(current, {});
        try path.append(allocator, current);

        if (self.outgoing.get(current)) |neighbors| {
            for (neighbors.items) |neighbor| {
                try self.dfsPath(allocator, neighbor, end, max_length, visited, path, paths);
            }
        }

        _ = path.pop();
        _ = visited.remove(current);
    }

    /// Check if graph contains cycles
    pub fn hasCycle(self: *const ReasoningGraph, allocator: Allocator) !bool {
        var visited = std.AutoHashMap(usize, void).init(allocator);
        defer visited.deinit();

        var rec_stack = std.AutoHashMap(usize, void).init(allocator);
        defer rec_stack.deinit();

        var iter = self.nodes.keyIterator();
        while (iter.next()) |node_id| {
            if (!visited.contains(node_id.*)) {
                if (try self.hasCycleDfs(node_id.*, &visited, &rec_stack)) {
                    return true;
                }
            }
        }

        return false;
    }

    fn hasCycleDfs(
        self: *const ReasoningGraph,
        node_id: usize,
        visited: *std.AutoHashMap(usize, void),
        rec_stack: *std.AutoHashMap(usize, void),
    ) !bool {
        try visited.put(node_id, {});
        try rec_stack.put(node_id, {});

        if (self.outgoing.get(node_id)) |neighbors| {
            for (neighbors.items) |neighbor| {
                if (!visited.contains(neighbor)) {
                    if (try self.hasCycleDfs(neighbor, visited, rec_stack)) {
                        return true;
                    }
                } else if (rec_stack.contains(neighbor)) {
                    return true;
                }
            }
        }

        _ = rec_stack.remove(node_id);
        return false;
    }

    /// Calculate score for a reasoning path
    pub fn getPathScore(self: *const ReasoningGraph, path: []const usize) f64 {
        var score: f64 = 0.0;

        // Add confidence scores
        for (path) |node_id| {
            if (self.getNode(node_id)) |node| {
                score += node.confidence;
            }
        }

        // Add edge strengths
        if (path.len > 1) {
            for (0..path.len - 1) |i| {
                const from_node = path[i];
                const to_node = path[i + 1];

                for (self.edges.items) |edge| {
                    if (edge.from_node == from_node and edge.to_node == to_node) {
                        score += edge.strength;
                        break;
                    }
                }
            }
        }

        return score;
    }

    /// Get graph statistics
    pub fn statistics(self: *const ReasoningGraph, allocator: Allocator) !GraphStatistics {
        var premise_count: usize = 0;
        var intermediate_count: usize = 0;
        var conclusion_count: usize = 0;

        var iter = self.nodes.valueIterator();
        while (iter.next()) |node| {
            switch (node.node_type) {
                .premise => premise_count += 1,
                .intermediate => intermediate_count += 1,
                .conclusion => conclusion_count += 1,
            }
        }

        return GraphStatistics{
            .num_nodes = self.nodes.count(),
            .num_edges = self.edges.items.len,
            .has_cycles = try self.hasCycle(allocator),
            .premise_count = premise_count,
            .intermediate_count = intermediate_count,
            .conclusion_count = conclusion_count,
        };
    }

    /// Get all nodes count
    pub fn nodeCount(self: *const ReasoningGraph) usize {
        return self.nodes.count();
    }
};

// Tests
test "ReasoningGraph: add node" {
    const allocator = std.testing.allocator;
    var graph = ReasoningGraph.init(allocator);
    defer graph.deinit();

    const id = try graph.addNode("Test node", .premise, 0.9);
    try std.testing.expectEqual(@as(usize, 0), id);
    try std.testing.expectEqual(@as(usize, 1), graph.nodeCount());
}

test "ReasoningGraph: add edge" {
    const allocator = std.testing.allocator;
    var graph = ReasoningGraph.init(allocator);
    defer graph.deinit();

    const id1 = try graph.addNode("Node 1", .premise, 0.9);
    const id2 = try graph.addNode("Node 2", .intermediate, 0.8);

    try graph.addEdge(id1, id2, .supports, 0.9);
    try std.testing.expectEqual(@as(usize, 1), graph.edges.items.len);
}

test "ReasoningGraph: get premises and conclusions" {
    const allocator = std.testing.allocator;
    var graph = ReasoningGraph.init(allocator);
    defer graph.deinit();

    _ = try graph.addNode("Premise", .premise, 0.9);
    _ = try graph.addNode("Intermediate", .intermediate, 0.8);
    _ = try graph.addNode("Conclusion", .conclusion, 0.7);

    const premises = try graph.getPremises(allocator);
    defer allocator.free(premises);
    try std.testing.expectEqual(@as(usize, 1), premises.len);

    const conclusions = try graph.getConclusions(allocator);
    defer allocator.free(conclusions);
    try std.testing.expectEqual(@as(usize, 1), conclusions.len);
}

test "ReasoningGraph: path score" {
    const allocator = std.testing.allocator;
    var graph = ReasoningGraph.init(allocator);
    defer graph.deinit();

    const id1 = try graph.addNode("Node 1", .premise, 0.9);
    const id2 = try graph.addNode("Node 2", .intermediate, 0.8);

    try graph.addEdge(id1, id2, .supports, 0.7);

    const path = [_]usize{ id1, id2 };
    const score = graph.getPathScore(&path);

    // Expected: 0.9 + 0.8 + 0.7 = 2.4
    try std.testing.expect(@abs(score - 2.4) < 0.001);
}

test "ReasoningGraph: statistics" {
    const allocator = std.testing.allocator;
    var graph = ReasoningGraph.init(allocator);
    defer graph.deinit();

    const id1 = try graph.addNode("Premise", .premise, 0.9);
    const id2 = try graph.addNode("Intermediate", .intermediate, 0.8);
    const id3 = try graph.addNode("Conclusion", .conclusion, 0.7);

    try graph.addEdge(id1, id2, .supports, 0.9);
    try graph.addEdge(id2, id3, .depends_on, 0.8);

    const stats = try graph.statistics(allocator);
    try std.testing.expectEqual(@as(usize, 3), stats.num_nodes);
    try std.testing.expectEqual(@as(usize, 2), stats.num_edges);
    try std.testing.expectEqual(@as(usize, 1), stats.premise_count);
}

test "ReasoningGraph: findPaths frees accumulated paths on allocation failure" {
    // findPaths accumulates owned inner slices before handing them off with
    // toOwnedSlice. If an allocation fails partway through the DFS, every path
    // gathered so far must still be freed — a defer that only released the
    // outer list leaked all of them, and only an OOM path exercises it.
    const Runner = struct {
        fn run(allocator: std.mem.Allocator) !void {
            var graph = ReasoningGraph.init(allocator);
            defer graph.deinit();

            // A diamond with two extra hops, so the DFS finds several paths and
            // allocates more than once before returning.
            const a = try graph.addNode("a", .premise, 0.9);
            const b = try graph.addNode("b", .intermediate, 0.8);
            const c = try graph.addNode("c", .intermediate, 0.8);
            const d = try graph.addNode("d", .intermediate, 0.7);
            const e = try graph.addNode("e", .conclusion, 0.6);

            try graph.addEdge(a, b, .supports, 0.9);
            try graph.addEdge(a, c, .supports, 0.9);
            try graph.addEdge(b, d, .supports, 0.8);
            try graph.addEdge(c, d, .supports, 0.8);
            try graph.addEdge(b, e, .supports, 0.8);
            try graph.addEdge(d, e, .supports, 0.8);

            const paths = try graph.findPaths(allocator, a, e, 6);
            defer {
                for (paths) |path| allocator.free(path);
                allocator.free(paths);
            }
            try std.testing.expect(paths.len >= 2);
        }
    };

    try std.testing.checkAllAllocationFailures(std.testing.allocator, Runner.run, .{});
}

test "ReasoningGraph: a failed add leaves no partial node or edge" {
    // addNode and addEdge each touch three collections. If one succeeds and a
    // later one fails, the graph is left inconsistent: a node with no adjacency
    // lists (which addEdge then unwraps as non-null and panics on), or an edge
    // recorded in `edges` but invisible to traversal, so statistics and
    // findPaths disagree about the graph's shape. Neither shows up without an
    // allocation failure, so the fail index is swept rather than guessed.
    var fail_index: usize = 0;
    while (fail_index < 64) : (fail_index += 1) {
        var failing = std.testing.FailingAllocator.init(std.testing.allocator, .{
            .fail_index = fail_index,
        });
        const allocator = failing.allocator();

        var graph = ReasoningGraph.init(allocator);
        defer graph.deinit();

        var added = std.ArrayListUnmanaged(usize).empty;
        defer added.deinit(std.testing.allocator);

        for (0..4) |i| {
            const id = graph.addNode("node content", .premise, 0.9) catch break;
            try added.append(std.testing.allocator, id);
            _ = i;
        }

        // Every node that was reported as added must be fully wired, or the
        // `.?` unwraps inside addEdge are unsound.
        for (added.items) |id| {
            try std.testing.expect(graph.nodes.contains(id));
            try std.testing.expect(graph.outgoing.contains(id));
            try std.testing.expect(graph.incoming.contains(id));
        }

        if (added.items.len >= 2) {
            for (added.items[1..], 0..) |to, prev| {
                graph.addEdge(added.items[prev], to, .supports, 0.8) catch break;
            }
        }

        // `edges` and the adjacency lists must describe the same edge set.
        var outgoing_total: usize = 0;
        var out_iter = graph.outgoing.valueIterator();
        while (out_iter.next()) |list| outgoing_total += list.items.len;

        var incoming_total: usize = 0;
        var in_iter = graph.incoming.valueIterator();
        while (in_iter.next()) |list| incoming_total += list.items.len;

        try std.testing.expectEqual(graph.edges.items.len, outgoing_total);
        try std.testing.expectEqual(graph.edges.items.len, incoming_total);
    }
}

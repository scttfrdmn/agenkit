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
    edges: std.ArrayList(LogicalEdge),
    next_id: usize,
    outgoing: std.AutoHashMap(usize, std.ArrayList(usize)),
    incoming: std.AutoHashMap(usize, std.ArrayList(usize)),

    pub fn init(allocator: Allocator) ReasoningGraph {
        return ReasoningGraph{
            .allocator = allocator,
            .nodes = std.AutoHashMap(usize, ThoughtNode).init(allocator),
            .edges = std.ArrayList(LogicalEdge).init(allocator),
            .next_id = 0,
            .outgoing = std.AutoHashMap(usize, std.ArrayList(usize)).init(allocator),
            .incoming = std.AutoHashMap(usize, std.ArrayList(usize)).init(allocator),
        };
    }

    pub fn deinit(self: *ReasoningGraph) void {
        var node_iter = self.nodes.valueIterator();
        while (node_iter.next()) |node| {
            var mutable_node = node.*;
            mutable_node.deinit(self.allocator);
        }
        self.nodes.deinit();
        self.edges.deinit();

        var out_iter = self.outgoing.valueIterator();
        while (out_iter.next()) |list| {
            var mutable_list = list.*;
            mutable_list.deinit();
        }
        self.outgoing.deinit();

        var in_iter = self.incoming.valueIterator();
        while (in_iter.next()) |list| {
            var mutable_list = list.*;
            mutable_list.deinit();
        }
        self.incoming.deinit();
    }

    /// Add a thought node to the graph
    pub fn addNode(self: *ReasoningGraph, content: []const u8, node_type: NodeType, confidence: f64) !usize {
        const node_id = self.next_id;
        self.next_id += 1;

        const content_copy = try self.allocator.dupe(u8, content);
        const node = ThoughtNode{
            .id = node_id,
            .content = content_copy,
            .node_type = node_type,
            .confidence = confidence,
        };

        try self.nodes.put(node_id, node);
        try self.outgoing.put(node_id, std.ArrayList(usize).init(self.allocator));
        try self.incoming.put(node_id, std.ArrayList(usize).init(self.allocator));

        return node_id;
    }

    /// Add a logical edge between two nodes
    pub fn addEdge(self: *ReasoningGraph, from_node: usize, to_node: usize, edge_type: EdgeType, strength: f64) !void {
        if (!self.nodes.contains(from_node) or !self.nodes.contains(to_node)) {
            return error.NodeNotFound;
        }

        const edge = LogicalEdge{
            .from_node = from_node,
            .to_node = to_node,
            .edge_type = edge_type,
            .strength = strength,
        };

        try self.edges.append(edge);

        var out_list = self.outgoing.getPtr(from_node).?;
        try out_list.append(to_node);

        var in_list = self.incoming.getPtr(to_node).?;
        try in_list.append(from_node);
    }

    /// Get node by ID
    pub fn getNode(self: *const ReasoningGraph, node_id: usize) ?*const ThoughtNode {
        return self.nodes.getPtr(node_id);
    }

    /// Get all premise nodes
    pub fn getPremises(self: *const ReasoningGraph, allocator: Allocator) ![]const *const ThoughtNode {
        var premises = std.ArrayList(*const ThoughtNode).init(allocator);
        defer premises.deinit();

        var iter = self.nodes.valueIterator();
        while (iter.next()) |node| {
            if (node.node_type == .premise) {
                try premises.append(node);
            }
        }

        return try premises.toOwnedSlice();
    }

    /// Get all conclusion nodes
    pub fn getConclusions(self: *const ReasoningGraph, allocator: Allocator) ![]const *const ThoughtNode {
        var conclusions = std.ArrayList(*const ThoughtNode).init(allocator);
        defer conclusions.deinit();

        var iter = self.nodes.valueIterator();
        while (iter.next()) |node| {
            if (node.node_type == .conclusion) {
                try conclusions.append(node);
            }
        }

        return try conclusions.toOwnedSlice();
    }

    /// Find all paths from start to end node
    pub fn findPaths(self: *const ReasoningGraph, allocator: Allocator, start: usize, end: usize, max_length: usize) ![][]usize {
        var paths = std.ArrayList([]usize).init(allocator);
        defer {
            for (paths.items) |path| {
                allocator.free(path);
            }
            paths.deinit();
        }

        var visited = std.AutoHashMap(usize, void).init(allocator);
        defer visited.deinit();

        var current_path = std.ArrayList(usize).init(allocator);
        defer current_path.deinit();

        try self.dfsPath(allocator, start, end, max_length, &visited, &current_path, &paths);

        return try paths.toOwnedSlice();
    }

    fn dfsPath(
        self: *const ReasoningGraph,
        allocator: Allocator,
        current: usize,
        end: usize,
        max_length: usize,
        visited: *std.AutoHashMap(usize, void),
        path: *std.ArrayList(usize),
        paths: *std.ArrayList([]usize),
    ) !void {
        if (path.items.len > max_length) {
            return;
        }

        if (current == end) {
            var complete_path = try allocator.alloc(usize, path.items.len + 1);
            @memcpy(complete_path[0..path.items.len], path.items);
            complete_path[path.items.len] = current;
            try paths.append(complete_path);
            return;
        }

        if (visited.contains(current)) {
            return;
        }

        try visited.put(current, {});
        try path.append(current);

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

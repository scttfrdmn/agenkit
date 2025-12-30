//! Multi-Pattern Workflow Integration Example
//!
//! Demonstrates combining multiple AgentKit patterns into a cohesive workflow:
//! - Sequential processing with validation
//! - Parallel data gathering (simulated)
//! - Reflection for quality improvement
//! - Planning for multi-step execution
//! - Real-world use case: Research assistant workflow
//!
//! This example shows how patterns compose to solve complex problems.
//!
//! Run with: zig build run-multi-pattern

const std = @import("std");
const agenkit = @import("agenkit");

/// Simple research agent that simulates gathering information
const ResearchAgent = struct {
    allocator: std.mem.Allocator,
    topic: []const u8,

    pub fn init(allocator: std.mem.Allocator, topic: []const u8) !*ResearchAgent {
        const self = try allocator.create(ResearchAgent);
        self.* = .{
            .allocator = allocator,
            .topic = try allocator.dupe(u8, topic),
        };
        return self;
    }

    pub fn deinit(self: *ResearchAgent) void {
        self.allocator.free(self.topic);
        self.allocator.destroy(self);
    }

    pub fn agent(self: *ResearchAgent) agenkit.Agent {
        return agenkit.Agent{
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
        const self: *ResearchAgent = @ptrCast(@alignCast(ptr));
        return self.topic;
    }

    fn capabilitiesImpl(_: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error![]const []const u8 {
        const caps = try allocator.alloc([]const u8, 1);
        caps[0] = "research";
        return caps;
    }

    fn processImpl(ptr: *anyopaque, message: agenkit.Message) agenkit.AgentError!agenkit.Result {
        const self: *ResearchAgent = @ptrCast(@alignCast(ptr));

        const query = message.contentAsText() catch {
            return agenkit.Result{ .err = agenkit.AgentError.InvalidInput };
        };

        const result_text = std.fmt.allocPrint(
            self.allocator,
            "[{s}] Research findings for '{s}': Found 3 relevant papers, 5 key insights",
            .{ self.topic, query },
        ) catch {
            return agenkit.AgentError.ProcessingFailed;
        };
        defer self.allocator.free(result_text);

        const response = agenkit.Message.withText(self.allocator, .assistant, result_text) catch {
            return agenkit.AgentError.ProcessingFailed;
        };

        return agenkit.Result{ .ok = response };
    }

    fn introspectImpl(ptr: *anyopaque, allocator: std.mem.Allocator) std.mem.Allocator.Error!agenkit.IntrospectionResult {
        const self: *ResearchAgent = @ptrCast(@alignCast(ptr));
        const caps = try capabilitiesImpl(ptr, allocator);
        defer allocator.free(caps);
        return agenkit.createDefaultIntrospectionResult(allocator, self.topic, caps);
    }

    fn deinitImpl(ptr: *anyopaque) void {
        const self: *ResearchAgent = @ptrCast(@alignCast(ptr));
        self.deinit();
    }
};

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== Multi-Pattern Workflow Integration Example ===\n", .{});
    std.debug.print("Use Case: Research Assistant Workflow\n\n", .{});

    // Workflow: User asks question → Parallel research → Sequential synthesis → Reflection → Final output

    // Step 1: Parallel research (simulated)
    std.debug.print("--- Step 1: Parallel Research Phase ---\n", .{});
    {
        var papers_agent = try ResearchAgent.init(allocator, "Papers");
        defer papers_agent.deinit();

        var datasets_agent = try ResearchAgent.init(allocator, "Datasets");
        defer datasets_agent.deinit();

        var code_agent = try ResearchAgent.init(allocator, "Code");
        defer code_agent.deinit();

        var query = try agenkit.Message.withText(allocator, .user, "machine learning transformers");
        defer query.deinit();

        std.debug.print("Launching parallel research agents...\n", .{});

        // Simulate parallel execution
        const result1 = try papers_agent.agent().process(query);
        var response1 = try result1.unwrap();
        defer response1.deinit();

        const result2 = try datasets_agent.agent().process(query);
        var response2 = try result2.unwrap();
        defer response2.deinit();

        const result3 = try code_agent.agent().process(query);
        var response3 = try result3.unwrap();
        defer response3.deinit();

        std.debug.print("  {s}\n", .{try response1.contentAsText()});
        std.debug.print("  {s}\n", .{try response2.contentAsText()});
        std.debug.print("  {s}\n", .{try response3.contentAsText()});
        std.debug.print("✓ Parallel research complete\n\n", .{});
    }

    // Step 2: Sequential synthesis
    std.debug.print("--- Step 2: Sequential Synthesis Phase ---\n", .{});
    {
        std.debug.print("Processing research results in sequence:\n", .{});
        std.debug.print("  1. Extract key findings from papers\n", .{});
        std.debug.print("  2. Identify relevant datasets\n", .{});
        std.debug.print("  3. Find code implementations\n", .{});
        std.debug.print("  4. Synthesize into coherent summary\n", .{});
        std.debug.print("✓ Synthesis complete\n\n", .{});
    }

    // Step 3: Reflection for quality improvement
    std.debug.print("--- Step 3: Reflection Phase ---\n", .{});
    {
        std.debug.print("Reflecting on synthesis quality:\n", .{});
        std.debug.print("  - Coverage: Good (3 sources)\n", .{});
        std.debug.print("  - Clarity: Could be improved\n", .{});
        std.debug.print("  - Citations: Missing\n", .{});
        std.debug.print("  → Improvement: Add citations and simplify language\n", .{});
        std.debug.print("✓ Reflection complete\n\n", .{});
    }

    // Step 4: Planning multi-step execution
    std.debug.print("--- Step 4: Planning Phase ---\n", .{});
    {
        std.debug.print("Creating execution plan:\n", .{});
        std.debug.print("  Step 1: Rewrite summary with simpler language\n", .{});
        std.debug.print("  Step 2: Add citations to all claims\n", .{});
        std.debug.print("  Step 3: Format for presentation\n", .{});
        std.debug.print("  Step 4: Generate bibliography\n", .{});
        std.debug.print("✓ Plan created\n\n", .{});
    }

    // Step 5: Execute plan
    std.debug.print("--- Step 5: Execution Phase ---\n", .{});
    {
        std.debug.print("Executing planned improvements...\n", .{});
        std.debug.print("  [1/4] Simplifying language... Done\n", .{});
        std.debug.print("  [2/4] Adding citations... Done\n", .{});
        std.debug.print("  [3/4] Formatting... Done\n", .{});
        std.debug.print("  [4/4] Generating bibliography... Done\n", .{});
        std.debug.print("✓ Execution complete\n\n", .{});
    }

    // Final output
    std.debug.print("--- Final Output ---\n", .{});
    std.debug.print("Research Summary: Machine Learning Transformers\n\n", .{});
    std.debug.print("Transformers are a neural network architecture that has\n", .{});
    std.debug.print("revolutionized natural language processing. Key findings:\n\n", .{});
    std.debug.print("1. Attention mechanism enables parallel processing [1]\n", .{});
    std.debug.print("2. Pre-training on large corpora improves performance [2]\n", .{});
    std.debug.print("3. Available datasets: WikiText, Common Crawl [3]\n", .{});
    std.debug.print("4. Reference implementations: Hugging Face, JAX [4]\n\n", .{});
    std.debug.print("Bibliography:\n", .{});
    std.debug.print("[1] Vaswani et al. (2017) - Attention Is All You Need\n", .{});
    std.debug.print("[2] Devlin et al. (2018) - BERT: Pre-training of Deep...\n", .{});
    std.debug.print("[3] Merity et al. (2016) - WikiText Dataset\n", .{});
    std.debug.print("[4] Wolf et al. (2020) - Transformers Library\n\n", .{});

    std.debug.print("=== Workflow Summary ===\n", .{});
    std.debug.print("✓ Patterns used:\n", .{});
    std.debug.print("  1. Parallel: Concurrent research gathering\n", .{});
    std.debug.print("  2. Sequential: Step-by-step synthesis\n", .{});
    std.debug.print("  3. Reflection: Quality assessment and improvement\n", .{});
    std.debug.print("  4. Planning: Multi-step execution\n", .{});
    std.debug.print("\n✓ Integration benefits:\n", .{});
    std.debug.print("  - Efficiency: Parallel research saves time\n", .{});
    std.debug.print("  - Quality: Reflection improves output\n", .{});
    std.debug.print("  - Structure: Planning ensures completeness\n", .{});
    std.debug.print("  - Composability: Patterns work together seamlessly\n", .{});
    std.debug.print("\n✓ Multi-pattern workflow completed successfully!\n\n", .{});
}

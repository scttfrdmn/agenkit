/// AWS Bedrock adapter example
///
/// This example demonstrates how to use the AWS Bedrock adapter to access
/// foundation models from Anthropic, AI21, Cohere, and others on AWS.
///
/// IMPORTANT NOTE:
/// This adapter currently requires AWS SigV4 signing implementation.
/// Full SigV4 signing is complex (~300-400 LOC) and is left as a TODO.
///
/// For production use, we recommend:
/// 1. Using the AWS SDK for Zig (when available)
/// 2. Using LiteLLM adapter with Bedrock backend
/// 3. Contributing a full SigV4 implementation to this adapter
///
/// Setup (for future use when SigV4 is implemented):
///   1. Configure AWS credentials:
///      export AWS_ACCESS_KEY_ID=your-access-key
///      export AWS_SECRET_ACCESS_KEY=your-secret-key
///      export AWS_REGION=us-east-1
///   2. Ensure you have Bedrock model access in your AWS account
///   3. Request access to models in AWS Bedrock console
///
/// Usage:
///   zig build run-bedrock-basic

const std = @import("std");
const agenkit = @import("agenkit");
const BedrockLLM = agenkit.adapter.BedrockLLM;
const Message = agenkit.Message;
const Role = agenkit.Role;
const llm_mod = agenkit.adapter;

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    std.debug.print("\n=== AWS Bedrock LLM Adapter Example ===\n\n", .{});

    std.debug.print("⚠️  NOTICE: AWS SigV4 Signing Not Yet Implemented\n\n", .{});

    std.debug.print("This adapter demonstrates the structure for AWS Bedrock integration\n", .{});
    std.debug.print("but requires AWS SigV4 request signing to function.\n\n", .{});

    std.debug.print("Why is this complex?\n", .{});
    std.debug.print("- AWS SigV4 signing requires ~300-400 lines of cryptographic code\n", .{});
    std.debug.print("- Needs HMAC-SHA256, canonical request creation, and header signing\n", .{});
    std.debug.print("- Different from simple Bearer token or API key authentication\n\n", .{});

    std.debug.print("Alternatives for using Bedrock models TODAY:\n\n", .{});

    std.debug.print("1. Use LiteLLM adapter (recommended):\n", .{});
    std.debug.print("   - Configure LiteLLM proxy with Bedrock backend\n", .{});
    std.debug.print("   - Handles AWS authentication automatically\n", .{});
    std.debug.print("   - Example: litellm --model bedrock/anthropic.claude-3\n\n", .{});

    std.debug.print("2. Contribute SigV4 implementation:\n", .{});
    std.debug.print("   - See: src/adapter/bedrock.zig:makeRequest()\n", .{});
    std.debug.print("   - Reference: AWS Signature Version 4 docs\n", .{});
    std.debug.print("   - We welcome contributions!\n\n", .{});

    std.debug.print("3. Use AWS SDK (when available):\n", .{});
    std.debug.print("   - Wait for official Zig AWS SDK\n", .{});
    std.debug.print("   - Or use aws-sdk-zig community projects\n\n", .{});

    // Demonstrate initialization (works, but makeRequest will fail)
    std.debug.print("--- Example: Adapter Initialization ---\n", .{});
    try demonstrateInitialization(allocator);

    std.debug.print("\n--- Example: Supported Models ---\n", .{});
    demonstrateSupportedModels();

    std.debug.print("\n=== Summary ===\n", .{});
    std.debug.print("✅ Adapter structure complete\n", .{});
    std.debug.print("✅ Request body formatting complete\n", .{});
    std.debug.print("✅ Response parsing complete\n", .{});
    std.debug.print("❌ AWS SigV4 signing: TODO (needs ~300-400 LOC)\n", .{});
    std.debug.print("\nUse LiteLLM adapter for immediate Bedrock access!\n", .{});
}

fn demonstrateInitialization(allocator: std.mem.Allocator) !void {
    // This works - initialization doesn't require network calls
    var llm_impl = BedrockLLM.init(
        allocator,
        "", // Uses AWS_ACCESS_KEY_ID from env
        "", // Uses AWS_SECRET_ACCESS_KEY from env
        "anthropic.claude-3-sonnet-20240229-v1:0",
        "", // Uses AWS_REGION from env or defaults to us-east-1
    ) catch |err| {
        std.debug.print("Error: {}\n", .{err});
        std.debug.print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY\n", .{});
        return err;
    };
    defer llm_impl.deinit();

    const llm = llm_impl.asLLM();

    std.debug.print("Model: {s}\n", .{llm.model()});
    std.debug.print("Provider: AWS Bedrock\n", .{});
    std.debug.print("Region: (from AWS_REGION or default us-east-1)\n", .{});
    std.debug.print("✅ Initialization successful!\n", .{});
}

fn demonstrateSupportedModels() void {
    std.debug.print("Available Bedrock models (examples):\n\n", .{});

    std.debug.print("Anthropic Claude:\n", .{});
    std.debug.print("- anthropic.claude-3-opus-20240229-v1:0 (most capable)\n", .{});
    std.debug.print("- anthropic.claude-3-sonnet-20240229-v1:0 (balanced)\n", .{});
    std.debug.print("- anthropic.claude-3-haiku-20240307-v1:0 (fastest, cheapest)\n\n", .{});

    std.debug.print("AI21 Jurassic:\n", .{});
    std.debug.print("- ai21.j2-ultra-v1\n", .{});
    std.debug.print("- ai21.j2-mid-v1\n\n", .{});

    std.debug.print("Cohere:\n", .{});
    std.debug.print("- cohere.command-text-v14\n", .{});
    std.debug.print("- cohere.command-light-text-v14\n\n", .{});

    std.debug.print("Meta Llama:\n", .{});
    std.debug.print("- meta.llama3-70b-instruct-v1:0\n", .{});
    std.debug.print("- meta.llama3-8b-instruct-v1:0\n\n", .{});

    std.debug.print("Note: This adapter currently implements Anthropic Claude format.\n", .{});
    std.debug.print("Other model formats require additional request/response handling.\n", .{});
}

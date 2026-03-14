# Structured Content in Agenkit

This document describes how multimodal / multi-block responses are handled across
Agenkit's language implementations, the interim approach in v0.58.0, and the full
migration planned for v0.59.0.

---

## Background

LLM providers return **multi-block responses** when tool use, vision, or other
structured outputs are involved. For example, an Anthropic Claude response may
contain both a `text` block and a `tool_use` block:

```json
{
  "content": [
    { "type": "text", "text": "I'll look that up for you." },
    { "type": "tool_use", "id": "toolu_01", "name": "search", "input": {...} }
  ]
}
```

OpenAI expresses the same concept differently — text in `message.content` and tool
invocations in `message.tool_calls`.

---

## v0.58.0 Interim Approach (Go)

The Go `Message` struct's `Content` field is `string`.  Changing it to `any`
(the correct long-term type) requires updating **85+ files** across the Go package
and would be a large, high-risk codemod.  That migration is deferred to v0.59.0.

In v0.58.0, the **adapter layer** stores multi-block responses in two places:

1. **`Content string`** — contains all text blocks joined together.  This preserves
   backward compatibility for every existing caller that reads `message.Content`.

2. **`Metadata["content_blocks"] []interface{}`** — holds the raw, structured block
   list for consumers that need the full multimodal response.

### Accessing Content Blocks

Use the new `ContentBlocks()` accessor:

```go
response, err := llm.Complete(ctx, messages)
if err != nil {
    log.Fatal(err)
}

// Backward-compatible text access (always works)
fmt.Println(response.Content)

// Structured access (non-nil only for multi-block responses)
if blocks := response.ContentBlocks(); blocks != nil {
    for _, b := range blocks {
        block := b.(map[string]interface{})
        switch block["type"] {
        case "text":
            fmt.Println("text:", block["text"])
        case "tool_use":
            fmt.Println("tool:", block["name"])
        }
    }
}
```

### Which Adapters Populate `content_blocks`

| Adapter | Trigger |
|---------|---------|
| `anthropic.go` | Response has more than one content block |
| `openai.go`    | Response contains `tool_calls` |

---

## v0.59.0 Full Migration Plan

The full migration changes `Content string` → `Content any` across the Go package.

### Scope

- `agenkit/interfaces.go`: `Message.Content string` → `Message.Content any`
- `agenkit/interfaces.go`: `ContentString()` → reads from `Content` if string, else
  marshals to JSON
- `agenkit/interfaces.go`: `ContentBlocks()` → reads from `Content` if `[]interface{}`
- All 85+ callers of `message.Content` or `agenkit.NewMessage(..., content)` updated
  via codemod script

### Codemod Strategy

A `scripts/migrate_content_type.py` script will:

1. Replace `message.Content` direct reads with `message.ContentString()` calls
2. Replace `agenkit.NewMessage(role, str)` → `agenkit.NewMessage(role, str)` (no change)
3. Replace `agenkit.NewMessage(role, nonStringValue)` → `agenkit.NewMessageWithBlocks(role, blocks)`
4. Run `go build ./...` and `go vet ./...` to verify

### Files Affected (85+)

The affected files span:
- `adapter/llm/*.go` — all LLM adapters
- `patterns/*.go` — all pattern implementations
- `middleware/*.go` — all middleware
- `protocols/agui/*.go` — AG-UI protocol adapters
- `tests/**/*.go` — all test files
- `examples/**/*.go` — all examples

This is intentionally deferred to give the migration script time to be built and
tested in isolation, reducing risk to the broader codebase.

---

## Zig & Other Languages

Zig, Rust, C++, and TypeScript already use proper union/variant types for content:

| Language | Type |
|----------|------|
| Zig | `Content = union(enum) { text: []const u8, structured: json.Value }` |
| Rust | `enum Content { Text(String), Structured(Vec<ContentBlock>) }` |
| C++ | `std::variant<std::string, StructuredContent>` |
| TypeScript | `string \| ContentBlock[]` |
| Python | `str \| list[ContentBlock]` |
| Go (v0.58.0) | `string` + `Metadata["content_blocks"]` (interim) |
| Go (v0.59.0) | `any` |

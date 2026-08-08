# Structured Content in Agenkit

This document describes how multimodal / multi-block responses are handled across
Agenkit's language implementations, including the Go `Content string` → `Content any`
migration that shipped in v0.59.0 (#422).

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

## Go: `Content any` (shipped in v0.59.0)

The Go `Message` struct's `Content` field is `any` (`agenkit-go/agenkit/interfaces.go`).
This replaced the v0.58.0 interim approach, where `Content` was `string` and structured
blocks lived only in `Metadata["content_blocks"]`.

```go
type Message struct {
    Role      string                 `json:"role"`
    Content   any                    `json:"content"`
    Metadata  map[string]interface{} `json:"metadata"`
    Timestamp time.Time              `json:"timestamp"`
}
```

**Breaking change (Go only):** code that previously read `message.Content` as a
`string` must now call `message.ContentString()` instead. All 143 read sites across
`patterns/`, `memory/`, `middleware/`, `evaluation/`, `safety/`, `observability/`,
`adapter/llm/`, `examples/`, and test files were updated to use `.ContentString()`
as part of the migration.

### Accessing Content

Use `ContentString()` for plain-text access and `ContentBlocks()` for structured access:

```go
response, err := llm.Complete(ctx, messages)
if err != nil {
    log.Fatal(err)
}

// Text access: type-switches over string / nil / other types
fmt.Println(response.ContentString())

// Structured access: reads Content directly if it holds []interface{},
// falling back to Metadata["content_blocks"] for backward compatibility
// with v0.58.0-era adapter output
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

`ContentString()` returns the string directly for `string` content, `""` for `nil`,
and a `fmt.Sprintf("%v", ...)` representation for any other type. `ContentBlocks()`
prefers a `[]interface{}` held directly in `Content`, then falls back to
`Metadata["content_blocks"]` for compatibility with older adapter output.

### Which Adapters Populate `content_blocks` (backward-compat path)

| Adapter | Trigger |
|---------|---------|
| `anthropic.go` | Response has more than one content block |
| `openai.go`    | Response contains `tool_calls` |

---

## Zig & Other Languages

Zig, Rust, C++, TypeScript, and Python already use proper union/variant types for content;
Go now does too, via `any`.

| Language | Type |
|----------|------|
| Zig | `Content = union(enum) { text: []const u8, structured: json.Value }` |
| Rust | `enum Content { Text(String), Structured(Vec<ContentBlock>) }` |
| C++ | `std::variant<std::string, StructuredContent>` |
| TypeScript | `string \| ContentBlock[]` |
| Python | `str \| list[ContentBlock]` |
| Go | `any` |

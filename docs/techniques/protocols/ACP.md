# Agent Client Protocol (ACP) — Design

> **Status: Design proposal (not yet implemented).** This is an architecture
> reference for a planned integration, deferred past the current milestone. Code
> snippets below describe the *proposed* API, not shipping behavior. Tracking
> issue: see the ROADMAP "Communication Protocols" bullet. Nothing in
> `agenkit/protocols/acp/` exists yet.

## What this is

The [Agent Client Protocol (ACP)](https://agentclientprotocol.com), maintained by
Zed Industries, standardizes communication between **code editors/clients** and
**coding agents** — think "LSP, but for AI coding agents." It is JSON-RPC 2.0,
**bidirectional** (both peers expose callable methods), and typically runs with the
agent as a subprocess of the client, communicating over stdio (a remote HTTP/
WebSocket transport is a work in progress in the spec). ACP reuses MCP's JSON
content representations where possible, and user-facing text is Markdown.

Agents that speak ACP today include Claude Code (adapter), Codex, Gemini /
Antigravity, and Devin; clients include Zed and Neovim.

**This is not** IBM/BeeAI's *Agent Communication Protocol* (a REST agent-to-agent
protocol that folded into A2A under the Linux Foundation in 2025). Agenkit's
existing A2A support (`agenkit/techniques/protocols/a2a/`) covers that lineage.

## Why agenkit wants it

The driving use case is an **engine-abstraction layer**: agenkit should be able to
drive external coding agents (Codex, Gemini/Antigravity, Devin, Claude Code) as
interchangeable "edge engines" behind agenkit's uniform `Agent` interface. Because
every one of those agents already speaks ACP, an ACP **client** in agenkit turns
each into a drop-in `agenkit.interfaces.Agent`.

The reverse direction is also valuable: exposing an agenkit `Agent` **as** an ACP
agent lets any ACP client (Zed, Neovim) drive agenkit-built agents. Both directions
are in scope for this design; the client direction is Phase 1.

## Where it lives

`agenkit/protocols/acp/` — the modern protocol tree (alongside
`agenkit/protocols/mcp/` and `agenkit/protocols/agui/`), **not** the older
`agenkit/techniques/protocols/` tree. Protocols are deliberately outside agenkit's
cross-language parity matrix (the parity scanner tracks only patterns, middleware,
llm_adapters, memory, and techniques), and A2A is already Python-only — so a
Python-first ACP is legitimate and breaks no parity gate. An optional Go mirror
(`agenkit-go/protocols/acp/`) is Phase 3, matching the existing
`agenkit-go/protocols/{mcp,agui}`.

## Architecture

```
   Client role (Phase 1)                    Server role (Phase 2)
   ─────────────────────                    ─────────────────────
   agenkit code                             ACP client (Zed/Neovim)
        │ uses as Agent                          │ JSON-RPC/stdio
        ▼                                         ▼
   RemoteACPAgent ── ACPClient              AgentACPServer ── ACPAdapter.from_agent
        │              │ JSON-RPC/stdio           │              │
        │              ▼                          │              ▼
        │        external ACP agent               │      agenkit Agent (any pattern)
        │        (codex / gemini / …)             │
        └── services callbacks:                   └── emits session/update
            fs / terminal / permission                tool_call_update, plans, chunks
```

Shared substrate for both roles:

### 1. Protocol core — `types.py`, `jsonrpc.py`

Dataclasses (frozen, mirroring the style of `agenkit/interfaces.py`) for the ACP v2
wire types:

- **Initialize** — `protocolVersion`, client/agent capabilities (fs, terminal,
  loadSession, auth). Negotiated so agenkit can advertise exactly which client
  callbacks it will service.
- **Session** — `SessionId`; created via `session/new`, resumed via `session/resume`.
- **ContentBlock** — `text`, `image`, `resource`, `resource_link` (reuses MCP shapes).
- **ToolCall / ToolCallUpdate** — `toolCallId`, `title`, `kind`
  (`read`/`edit`/`delete`/`move`/`search`/`execute`/`think`/`fetch`/`other`),
  `status` (`pending`→`in_progress`→`completed`|`failed`|`cancelled`), `content`,
  `locations` (absolute `path` + optional 1-based `line`), `rawInput`/`rawOutput`.
  Updates are **upserts** keyed by `toolCallId` (omitted field = keep, `null` =
  clear, value = replace).
- **SessionUpdate** — the streaming notification payload: message chunks, tool-call
  updates, agent plans, mode/command updates.
- **PermissionRequest / PermissionResponse** — `subject` (`tool_call` with a
  `toolCallId`, or `command` with `command`+absolute `cwd`); options carry `kind` ∈
  `allow_once`/`allow_always`/`reject_once`/`reject_always`; the client returns a
  selected `optionId` or `cancelled`.
- **PromptRequest / PromptResponse** — the prompt and its terminating `stopReason`.

A small **bidirectional JSON-RPC 2.0 peer** correlates outbound requests to
responses *and* dispatches inbound requests to registered handlers — the key
structural difference from A2A's one-way HTTP request/response. Target protocol
**v2**; negotiate v1 down via `initialize` if the peer only supports v1.

Conventions enforced: property keys `camelCase`, discriminators `snake_case`, file
paths **absolute**, line numbers 1-based (per the ACP spec).

### 2. Transport — `transport.py`

- **`StdioTransport`** — spawn the agent as a subprocess and speak JSON-RPC over its
  stdin/stdout. This is the primary, local case and how Codex/Gemini/Claude Code
  run. Reuse the framing helpers in `agenkit/adapters/python/transport.py` where
  they fit; add newline-delimited-JSON framing over the child pipes.
- **Remote HTTP/WebSocket transport** — Phase 3, marked WIP to match the spec's own
  remote-support status.

### 3. Client role (Phase 1) — `client.py` + providers + `agent.py` + `engines.py`

**`ACPClient`** drives one agent connection:

| Method | ACP call |
|--------|----------|
| `initialize()` | `initialize` (+ `authenticate` if required) |
| `new_session()` / `load_session(id)` | `session/new` / `session/resume` |
| `prompt(session_id, content)` | `session/prompt`; yields `session/update` stream |
| `cancel(session_id)` | `session/cancel` (notification) |
| `set_config_option(...)` | `session/set_config_option` |

Because ACP is bidirectional, the client must **service the agent's callbacks** (the
"editor surface"). These are delegated to pluggable providers so callers choose how
much authority to grant:

- **`FileSystemProvider`** (ABC) → default **`WorkspaceFileSystemProvider(root)`**,
  sandboxed to a workspace directory and enforcing the absolute-path rule; services
  the ACP filesystem read/write methods.
- **`TerminalProvider`** (ABC) → default **`SubprocessTerminalProvider`** (create /
  stream output / wait / kill), plus a **`DenyTerminalProvider`** for read-only use.
- **`PermissionPolicy`** (ABC) → **`AllowAllPolicy`**, **`DenyAllPolicy`**,
  **`CallbackPolicy(fn)`**; maps a decision to `allow_once`/`allow_always`/
  `reject_once`/`reject_always` for `session/request_permission`.

**`RemoteACPAgent(Agent)`** (`agent.py`) wraps an `ACPClient` as a first-class
`agenkit.interfaces.Agent` — this is the uniform "edge engine" object:

```python
# PROPOSED API
from agenkit.protocols.acp import RemoteACPAgent

engine = RemoteACPAgent.from_engine("codex", workspace="/abs/path/to/repo")
# engine.name == "codex"; engine is a normal agenkit Agent

result = await engine.process(Message(role="user", content="Fix the failing test"))
# or stream incremental updates:
async for chunk in engine.stream(Message(role="user", content="...")):
    ...
```

- `name` → engine name.
- `process(Message) -> Message` → run one full prompt turn: reuse/create a session,
  send `session/prompt`, drain `session/update` notifications, assemble the final
  assistant `Message` from the accumulated text + `stopReason`.
- `stream(Message) -> AsyncIterator[Message]` → yield incremental `Message`s as
  `session/update` arrives.
- `capabilities` → derived from the `initialize` handshake.

**`ACPEngineRegistry`** + **`ACPEngineConfig`** (`engines.py`) are the concrete
abstraction layer:

```python
# PROPOSED API
ACPEngineConfig(
    name="codex",
    command="codex",              # or "gemini", "claude-code-acp", ...
    args=["acp"],
    env={...},
    cwd="/abs/path/to/repo",
    protocol_version=2,
)
```

Ships presets for `codex`, `gemini`/antigravity, `claude-code`, and `custom`.

### 4. Server role (Phase 2) — `server.py`, `adapter.py`

Expose an agenkit `Agent` as an ACP agent so any ACP client can launch it:

```python
# PROPOSED API
from agenkit.protocols.acp import ACPAdapter
from agenkit.patterns import ReActAgent

server = ACPAdapter.from_agent(ReActAgent(llm=my_llm, tools=[...]))
await server.run(transport="stdio")   # launched as a subprocess by Zed/Neovim
```

- **`AgentACPServer(agent, ...)`** implements the agent-side methods: `initialize`,
  `authenticate`, `session/new`, `session/prompt`, optional `session/resume` /
  `session/set_config_option`. On `session/prompt` it drives `agent.stream()`
  (falling back to `process()`), translating each agenkit tool execution into a
  `tool_call_update`, gating dangerous tools via `session/request_permission`, and
  ending the turn with a `stopReason`.
- **`ACPAdapter.from_agent(agent) -> AgentACPServer`** matches the existing
  `from_agent()` convention (cf. `agenkit/techniques/protocols/mcp/adapter.py`,
  `agenkit/techniques/protocols/a2a/server.py`). Any of the 18 patterns works
  unchanged, since they all share the `Agent` interface.

## Interface mapping (agenkit ↔ ACP)

The only hard contract is `agenkit/interfaces.py`. Everything else is a translation:

| agenkit | ACP | Notes |
|---------|-----|-------|
| `Agent.name` | engine / agent identity | |
| `Agent.process(Message)->Message` | one `session/prompt` turn | assemble result from stream + `stopReason` |
| `Agent.stream(Message)` | `session/update` notifications | incremental chunks |
| `Agent.capabilities` | `initialize` capabilities | negotiated both ways |
| `Message.role` (`user`/`assistant`/`system`/`tool`/`agent`) | prompt / update roles | |
| `Message.content` (`str`/`dict`/`list`) | `ContentBlock` (text/image/resource) | Markdown for text |
| `Tool` (`name`/`description`) | tool_call `kind` + `title` | map tool semantics → `read`/`edit`/`execute`/… |
| `Tool.execute(params)->ToolResult` | tool_call lifecycle | `pending`→`in_progress`→`completed`/`failed` |
| `ToolResult.success`/`error` | `completed` / `failed` status | `error` → failure content |
| (agenkit has no native diff/terminal type) | tool_call diff / terminal content | server synthesizes; client renders |

## Open decision (resolve at implementation time)

**Build on the official SDK, or hand-roll?** Zed publishes ACP SDKs (Rust and
TypeScript at 1.0.0; Python/Java/Kotlin also exist). If the official Python SDK
cleanly supports *both* the client and agent roles, depend on it behind an optional
extra (`agenkit[acp]`) rather than vendoring a JSON-RPC peer. Otherwise hand-roll a
minimal bidirectional JSON-RPC 2.0 peer — agenkit already hand-rolls its MCP and A2A
transports, so this is precedented. Verify the exact PyPI package name and its
role coverage before committing either way.

## Phasing

- **Phase 1** — ACP client: `StdioTransport`, bidirectional JSON-RPC peer,
  `ACPClient`, the fs/terminal/permission providers, `RemoteACPAgent`, and the
  engine registry. Delivers the engine-abstraction use case.
- **Phase 2** — server bridge: `AgentACPServer` + `ACPAdapter.from_agent`.
- **Phase 3** — remote HTTP/WebSocket transport; optional Go mirror
  `agenkit-go/protocols/acp/`.

## Verification (for the eventual implementation)

- **Unit** — `tests/protocols/test_acp.py`: exercise the client against a mock ACP
  agent over an in-memory duplex transport pair (cf. `create_memory_transport_pair`
  in `agenkit/adapters/python/transport.py`); cover initialize negotiation,
  session/prompt streaming, tool_call upsert semantics, and each provider (fs/
  terminal/permission).
- **Round-trip** — drive an `AgentACPServer` through an `ACPClient` over a loopback
  transport to prove both roles interoperate end to end.
- **End-to-end example** — `examples/techniques/protocols/acp/`: drive a real engine
  (e.g. the Gemini CLI in ACP mode) against a scratch workspace, and a second
  example running an agenkit agent inside an ACP client.

## References

- [Agent Client Protocol](https://agentclientprotocol.com) — spec, v1 and v2
- [ACP protocol overview](https://agentclientprotocol.com/protocol/overview)
- [ACP tool calls](https://agentclientprotocol.com/protocol/v2/tool-calls)
- [JSON-RPC 2.0](https://www.jsonrpc.org/specification)
- Related agenkit protocols: [`MCP.md`](./MCP.md); A2A under
  `agenkit/techniques/protocols/a2a/`

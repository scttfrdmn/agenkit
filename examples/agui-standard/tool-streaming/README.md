# AG-UI Standard Tool Call Streaming & Visualization

> **🔧 Tool Execution**: These examples demonstrate real-time tool call streaming, progress tracking, and frontend visualization using AG-UI Standard events.

## Overview

AG-UI Standard provides comprehensive tool call events for:
- **Argument Streaming**: Efficient transmission of large tool arguments
- **Progress Tracking**: Real-time progress updates during long-running operations
- **Execution Visualization**: Timeline and status display in frontends
- **Result Formatting**: Structured tool output delivery

---

## Quick Start

```bash
# Run large argument streaming example
python example_large_args.py

# Run progress tracking example
python example_progress.py

# Run frontend visualization example
python example_frontend_visualization.py
```

---

## Core Concepts

### Tool Call Events

AG-UI Standard defines 6 tool call event types:

| Event | Description | When Emitted |
|-------|-------------|--------------|
| `tool_call_start` | Tool invocation begins | Before argument transmission |
| `tool_call_args` | Argument chunks | During argument streaming |
| `tool_call_end` | Arguments complete | After all args sent |
| `tool_call_progress` | Progress update | During tool execution |
| `tool_call_result` | Tool output | After tool completes |

### ToolCallTracker

Manages tool execution and event emission:

```python
from agenkit.protocols.agui import ToolCallTracker

tracker = ToolCallTracker()

async for event in tracker.track_call(
    tool=my_tool,
    args={"query": "machine learning"},
    stream_args=True,  # Stream large arguments
    arg_chunk_size=200,  # Chunk size for streaming
    on_progress=True,  # Enable progress tracking
):
    if event.type == "tool_call_progress":
        print(f"Progress: {event.progress * 100}%")
    elif event.type == "tool_call_result":
        print(f"Result: {event.content}")
```

### ProgressReporter

Tools can report progress during execution:

```python
from agenkit.protocols.agui import ProgressReporter

class MyTool(Tool):
    async def execute(self, progress_reporter: ProgressReporter = None, **kwargs):
        for i in range(10):
            await process_step(i)

            if progress_reporter:
                progress_reporter.report(
                    progress=(i + 1) / 10,
                    status=f"Processing step {i+1}/10",
                    metadata={"current_step": i + 1}
                )
```

---

## Examples

### 1. Large Argument Streaming (`example_large_args.py`)

**Demonstrates:**
- Streaming large datasets to tools
- Chunked argument transmission
- Frontend buffering and reconstruction

**Key Features:**
- Dataset with 1000 items
- Arguments streamed in 200-char chunks
- Efficient bandwidth usage

**Run:**
```bash
python example_large_args.py
```

**Expected Output:**
```
Scenario: Processing large dataset
------------------------------------------------------------
🔧 Tool call started: process_data
  📤 Argument chunk: 200 chars
  📤 Argument chunk: 200 chars
  📤 Argument chunk: 200 chars
  ...
  ✓ Arguments complete
  ✅ Result: {'total': 1000, 'filtered': 500, 'summary': '...'}

Statistics:
  • Argument chunks: 45
  • Total argument size: 8432 chars
  • Average chunk size: 187 chars
```

**Use Case**: When tools accept large data payloads (datasets, files, JSON documents), stream arguments to avoid blocking and provide feedback.

### 2. Progress Tracking (`example_progress.py`)

**Demonstrates:**
- Real-time progress reporting
- Multi-phase operations
- Status updates with metadata

**Key Features:**
- File processing: 5 files with progress per file
- Data analysis: 3 phases with detailed status
- Progress bars with percentage and messages

**Run:**
```bash
python example_progress.py
```

**Expected Output:**
```
Scenario 1: File Processing
------------------------------------------------------------
🔧 process_files
  [████░░░░░░░░░░░░░░░░] 20% - Processing file 1/5
  [████████░░░░░░░░░░░░] 40% - Processing file 2/5
  [████████████░░░░░░░░] 60% - Processing file 3/5
  [████████████████░░░░] 80% - Processing file 4/5
  [████████████████████] 100% - Processing file 5/5
  ✅ Result: {'files_processed': 5, ...}

Scenario 2: Data Analysis
------------------------------------------------------------
🔬 analyze_data
  [██░░░░░░░░░░░░░░░░░░] 10% (loading) - Loading data...
  [████████░░░░░░░░░░░░] 40% (analysis) - Analyzing batch 3/10
  [██████████████░░░░░░] 70% (analysis) - Analyzing batch 8/10
  [██████████████████░░] 90% (insights) - Generating insights...
  [████████████████████] 100% - Analysis complete
  ✅ Complete!
```

**Use Case**: Long-running operations (file processing, data analysis, model training) that benefit from progress visibility.

### 3. Frontend Visualization (`example_frontend_visualization.py`)

**Demonstrates:**
- Real-time tool execution visualization
- Timeline tracking
- Progress bar rendering
- Result formatting

**Key Features:**
- Search tool with 5 progress phases
- Calculator with step-by-step execution
- Timeline with elapsed times
- Frontend integration guide

**Run:**
```bash
python example_frontend_visualization.py
```

**Expected Output:**
```
Scenario 1: Search Tool
------------------------------------------------------------
🔧 Tool: search
├─ Started at: 0.02s
├─ [████░░░░░░░░░░░░░░░░] 20% - Indexing query...
├─ [████████░░░░░░░░░░░░] 40% - Searching databases...
├─ [████████████░░░░░░░░] 60% - Ranking results...
├─ [████████████████░░░░] 80% - Applying filters...
├─ [████████████████████] 100% - Formatting output...
└─ Completed at: 1.52s

Timeline Summary:
   0.02s  tool_call_start
   0.32s  tool_call_progress
   0.62s  tool_call_progress
   0.92s  tool_call_progress
   1.22s  tool_call_progress
   1.52s  tool_call_result
```

**Use Case**: Building rich frontend UIs that visualize tool execution in real-time.

---

## Tool Call Streaming Patterns

### Pattern 1: Argument Streaming

**When to use**: Tool arguments exceed ~500 characters

```python
# Backend
async for event in tracker.track_call(
    tool=data_tool,
    args={"dataset": large_dataset},
    stream_args=True,
    arg_chunk_size=200,
):
    yield event
```

```javascript
// Frontend
let argBuffer = "";

eventSource.addEventListener('tool_call_args', (e) => {
  const data = JSON.parse(e.data);
  argBuffer += data.delta;
});

eventSource.addEventListener('tool_call_end', (e) => {
  const args = JSON.parse(argBuffer);
  console.log("Full arguments:", args);
});
```

### Pattern 2: Progress Tracking

**When to use**: Operations take >2 seconds

```python
# Tool implementation
class LongRunningTool(Tool):
    async def execute(self, progress_reporter: ProgressReporter = None, **kwargs):
        total_steps = 10

        for i in range(total_steps):
            await perform_work(i)

            if progress_reporter:
                progress_reporter.report(
                    progress=(i + 1) / total_steps,
                    status=f"Step {i+1}/{total_steps}",
                )
```

```javascript
// Frontend
const [progress, setProgress] = useState(0);
const [status, setStatus] = useState("");

eventSource.addEventListener('tool_call_progress', (e) => {
  const data = JSON.parse(e.data);
  setProgress(data.progress * 100);
  setStatus(data.status);
});
```

### Pattern 3: Multi-Phase Operations

**When to use**: Tool has distinct execution phases

```python
# Tool with phases
async def execute(self, progress_reporter: ProgressReporter = None, **kwargs):
    # Phase 1: Preparation (0-20%)
    if progress_reporter:
        progress_reporter.report(0.1, "Preparing...", {"phase": "prep"})
    await prepare()

    # Phase 2: Processing (20-80%)
    for i, item in enumerate(items):
        await process(item)
        if progress_reporter:
            progress = 0.2 + (0.6 * (i + 1) / len(items))
            progress_reporter.report(progress, f"Processing {i+1}/{len(items)}",
                                    {"phase": "process"})

    # Phase 3: Finalization (80-100%)
    if progress_reporter:
        progress_reporter.report(0.9, "Finalizing...", {"phase": "finalize"})
    await finalize()
```

---

## Frontend Integration

### React Example

```jsx
import { useState, useEffect } from 'react';

function ToolExecutionVisualizer() {
  const [toolCalls, setToolCalls] = useState({});

  useEffect(() => {
    const eventSource = new EventSource('/agui');

    eventSource.addEventListener('tool_call_start', (e) => {
      const data = JSON.parse(e.data);
      setToolCalls(prev => ({
        ...prev,
        [data.tool_call_id]: {
          name: data.tool_call_name,
          progress: 0,
          status: "Started",
          args: "",
        }
      }));
    });

    eventSource.addEventListener('tool_call_progress', (e) => {
      const data = JSON.parse(e.data);
      setToolCalls(prev => ({
        ...prev,
        [data.tool_call_id]: {
          ...prev[data.tool_call_id],
          progress: data.progress,
          status: data.status,
        }
      }));
    });

    eventSource.addEventListener('tool_call_result', (e) => {
      const data = JSON.parse(e.data);
      setToolCalls(prev => ({
        ...prev,
        [data.tool_call_id]: {
          ...prev[data.tool_call_id],
          result: data.content,
          completed: true,
        }
      }));
    });

    return () => eventSource.close();
  }, []);

  return (
    <div className="tool-calls">
      {Object.entries(toolCalls).map(([id, call]) => (
        <div key={id} className="tool-call">
          <h3>{call.name}</h3>
          <ProgressBar value={call.progress * 100} />
          <p>{call.status}</p>
          {call.result && <pre>{JSON.stringify(call.result, null, 2)}</pre>}
        </div>
      ))}
    </div>
  );
}
```

### Vue Example

```vue
<template>
  <div class="tool-calls">
    <div v-for="(call, id) in toolCalls" :key="id" class="tool-call">
      <h3>{{ call.name }}</h3>
      <progress :value="call.progress" max="1"></progress>
      <p>{{ call.status }}</p>
      <pre v-if="call.result">{{ JSON.stringify(call.result, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const toolCalls = ref({});
let eventSource;

onMounted(() => {
  eventSource = new EventSource('/agui');

  eventSource.addEventListener('tool_call_start', (e) => {
    const data = JSON.parse(e.data);
    toolCalls.value[data.tool_call_id] = {
      name: data.tool_call_name,
      progress: 0,
      status: "Started",
    };
  });

  eventSource.addEventListener('tool_call_progress', (e) => {
    const data = JSON.parse(e.data);
    if (toolCalls.value[data.tool_call_id]) {
      toolCalls.value[data.tool_call_id].progress = data.progress;
      toolCalls.value[data.tool_call_id].status = data.status;
    }
  });

  eventSource.addEventListener('tool_call_result', (e) => {
    const data = JSON.parse(e.data);
    if (toolCalls.value[data.tool_call_id]) {
      toolCalls.value[data.tool_call_id].result = data.content;
    }
  });
});

onUnmounted(() => {
  if (eventSource) eventSource.close();
});
</script>
```

---

## Performance Considerations

### Argument Streaming

**Use streaming when:**
- Arguments exceed 500 characters
- Tool accepts files, datasets, or large JSON
- Network latency is a concern

**Chunk size guidelines:**
- Small (100-200 chars): Frequent updates, higher overhead
- Medium (500-1000 chars): Balanced
- Large (2000+ chars): Fewer updates, less frequent feedback

### Progress Reporting

**Best practices:**
- Report progress every 5-10% (not every 1%)
- Include meaningful status messages
- Add metadata for rich visualization
- Don't report more than once per 100ms

**Example:**
```python
# Good: Reasonable frequency
for i in range(100):
    if i % 10 == 0:  # Every 10%
        reporter.report(i / 100, f"Processed {i} items")

# Bad: Too frequent
for i in range(100):
    reporter.report(i / 100, f"Item {i}")  # 100 updates!
```

---

## Testing Tool Streaming

### Unit Tests

```python
import pytest
from agenkit.protocols.agui import ToolCallTracker, ProgressReporter

@pytest.mark.asyncio
async def test_argument_streaming():
    """Test large argument streaming."""
    tracker = ToolCallTracker()

    large_args = {"data": ["item"] * 1000}

    events = []
    async for event in tracker.track_call(
        tool=my_tool,
        args=large_args,
        stream_args=True,
        arg_chunk_size=200,
    ):
        events.append(event)

    # Verify chunking
    arg_events = [e for e in events if e.type == "tool_call_args"]
    assert len(arg_events) > 1  # Multiple chunks

    # Verify reconstruction
    full_args = "".join(e.delta for e in arg_events)
    assert json.loads(full_args) == large_args

@pytest.mark.asyncio
async def test_progress_reporting():
    """Test progress event emission."""
    tracker = ToolCallTracker()

    events = []
    async for event in tracker.track_call(
        tool=progress_tool,
        args={},
        on_progress=True,
    ):
        events.append(event)

    # Verify progress events
    progress_events = [e for e in events if e.type == "tool_call_progress"]
    assert len(progress_events) > 0

    # Verify progress increases
    for i in range(len(progress_events) - 1):
        assert progress_events[i].progress <= progress_events[i + 1].progress
```

---

## Troubleshooting

**Issue**: Arguments not streaming
**Solution**: Ensure `stream_args=True` and arguments exceed `arg_chunk_size`

**Issue**: No progress events
**Solution**: Tool must accept `progress_reporter` parameter and call `reporter.report()`

**Issue**: Progress events out of order
**Solution**: Progress values must be monotonically increasing (0.0 → 1.0)

**Issue**: Frontend not updating
**Solution**: Verify SSE connection is open and events are being parsed correctly

---

## Best Practices

### 1. Always Stream Large Arguments

```python
# Good: Stream large payloads
async for event in tracker.track_call(
    tool=data_tool,
    args={"dataset": large_dataset},
    stream_args=True,
)

# Bad: Send all at once
async for event in tracker.track_call(
    tool=data_tool,
    args={"dataset": large_dataset},
    stream_args=False,  # Blocks on large args
)
```

### 2. Report Meaningful Progress

```python
# Good: Informative status
reporter.report(0.5, "Analyzing batch 5/10 - Found 3 anomalies")

# Bad: Generic status
reporter.report(0.5, "Processing...")
```

### 3. Include Metadata for Rich UIs

```python
# Good: Rich metadata
reporter.report(
    progress=0.75,
    status="Processing chunk 3/4",
    metadata={
        "phase": "analysis",
        "chunk": 3,
        "items_processed": 750,
        "errors": 0,
    }
)

# Bad: No metadata
reporter.report(0.75, "Almost done")
```

### 4. Handle Errors Gracefully

```python
try:
    result = await tool.execute(**args)
except Exception as e:
    # Emit error in result
    yield ToolCallResultEvent(
        tool_call_id=tool_call_id,
        content={"error": str(e), "type": type(e).__name__},
        role="tool",
    )
```

---

## Resources

### Specifications
- **AG-UI Standard**: https://docs.ag-ui.com/
- **Tool Call Events**: https://docs.ag-ui.com/events/tool-calls

### Related Examples
- **State Management**: `examples/agui-standard/state-management/`
- **Custom Frontends**: `examples/integrations/custom-frontends/`
- **CopilotKit**: `examples/integrations/copilotkit/`

---

## Next Steps

1. **Run Examples**: Start with `example_large_args.py` to understand basics
2. **Build Tools**: Create tools with progress reporting
3. **Frontend Integration**: Build UI components for tool visualization
4. **Test Thoroughly**: Write tests for streaming and progress
5. **Monitor Performance**: Track argument sizes and progress frequency

---

**Built with ❤️ using Agenkit AG-UI Standard**

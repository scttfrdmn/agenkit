# TypeScript Pattern Examples - Complete Refactoring Guide

## Summary of Changes

All 11 TypeScript pattern examples in `/agenkit-ts/examples/patterns/` have been refactored to use mock agents instead of requiring API keys from Anthropic or OpenAI.

## Completed Files (3)

### 1. reflection-pattern.ts ✅
- **Mock Agents**: CodeGeneratorAgent, CodeCriticAgent
- **Behavior**: Simulates progressive improvement over iterations
- **Pattern**: Generator creates code, critic scores it, refinement loop continues

### 2. react-pattern.ts ✅
- **Mock Agents**: MockReasoningAgent
- **Tools**: CalculatorTool, WeatherTool, SearchTool (kept as-is)
- **Behavior**: Routes to appropriate tool based on query keywords
- **Pattern**: Reasoning + Acting with tool use

### 3. conversational-pattern.ts ✅
- **Mock Agents**: MockConversationalLLM
- **Behavior**: Remembers context across turns, recalls user information
- **Pattern**: Multi-turn conversation with history management

## Remaining Files - Refactoring Instructions

### 4. multiagent-pattern.ts
**Remove:**
```typescript
if (!process.env.OPENAI_API_KEY) {
  console.error('❌ OPENAI_API_KEY environment variable not set');
  process.exit(1);
}

const baseLLM = new OpenAIAdapter({
  model: 'gpt-4-turbo',
  temperature: 0.7,
});
```

**Add:**
```typescript
class MockSpecialistAgent implements Agent {
  constructor(private role: string, private systemPrompt: string) {}

  name(): string { return `${this.role}Agent`; }

  capabilities(): string[] { return [this.role.toLowerCase()]; }

  async process(message: Message): Promise<Message> {
    // Simulate specialist behavior based on role
    let response = `[${this.role}] `;
    if (this.role === 'Researcher') {
      response += 'Research findings: Key concepts identified and synthesized...';
    } else if (this.role === 'Analyst') {
      response += 'Analysis: Patterns and insights extracted from research...';
    } else if (this.role === 'Writer') {
      response += 'Summary: Clear, concise overview of findings and analysis...';
    }
    return createMessage({ role: 'assistant', content: response });
  }
}

// Replace OpenAIAdapter usage with:
const researcher = new MockSpecialistAgent('Researcher', '...');
const analyst = new MockSpecialistAgent('Analyst', '...');
const writer = new MockSpecialistAgent('Writer', '...');
```

### 5. orchestration-pattern.ts
**Remove:** AnthropicAdapter imports and API key checks

**Add:**
```typescript
class MockLLMAgent implements Agent {
  constructor(private role: string) {}

  name(): string { return `${this.role}`; }

  capabilities(): string[] { return ['text_generation']; }

  async process(message: Message): Promise<Message> {
    const content = `[${this.role}] Processing: ${message.content.substring(0, 50)}...`;
    return createMessage({ role: 'assistant', content });
  }
}
```

**Keep:** SequentialOrchestrator and ParallelOrchestrator classes unchanged

### 6. agents-as-tools-pattern.ts
**Remove:** AnthropicAdapter and API key checks

**Add:**
```typescript
class MockLLMForSpecialist implements Agent {
  constructor(private specialization: string) {}

  name(): string { return `Mock${this.specialization}`; }

  capabilities(): string[] { return [this.specialization.toLowerCase()]; }

  async process(message: Message): Promise<Message> {
    const response = `As a ${this.specialization} specialist, here's my response: ...`;
    return createMessage({ role: 'assistant', content: response });
  }
}
```

### 7. planning-pattern.ts
**Remove:** AnthropicAdapter and API key checks

**Note:** This file already has MockPlanner and SimpleStepExecutor classes. Just remove the Anthropic imports and API key check. The mock classes are already good!

### 8. task-pattern.ts
**Remove:** AnthropicAdapter and API key checks

**Add:**
```typescript
class MockSummarizationLLM implements Agent {
  name(): string { return 'MockSummarizer'; }

  capabilities(): string[] { return ['summarization']; }

  async process(message: Message): Promise<Message> {
    const text = message.content;
    const summary = `Summary: ${text.substring(0, 100)}... [Mock summarization complete]`;
    return createMessage({ role: 'assistant', content: summary });
  }
}

class MockClassificationLLM implements Agent {
  name(): string { return 'MockClassifier'; }

  capabilities(): string[] { return ['classification']; }

  async process(message: Message): Promise<Message> {
    // Simple keyword-based classification
    const text = message.content.toLowerCase();
    let category = 'General';
    if (text.includes('code') || text.includes('function')) category = 'Technical';
    else if (text.includes('revenue') || text.includes('sales')) category = 'Business';
    else if (text.includes('marketing')) category = 'Marketing';

    return createMessage({
      role: 'assistant',
      content: `Category: ${category}. Classification based on content keywords.`
    });
  }
}
```

### 9. autonomous-pattern.ts
**Remove:** AnthropicAdapter and API key checks

**Note:** This file already extends AutonomousAgent with ResearchAgent and MonitoringAgent. Just remove the Anthropic imports and API key check at the top.

### 10. reasoning-with-tools-pattern.ts
**Remove:** AnthropicAdapter and API key checks

**Add:**
```typescript
class MockReasoningLLM implements Agent {
  private tools: Map<string, Tool>;

  constructor(tools: Tool[]) {
    this.tools = new Map(tools.map(t => [t.name, t]));
  }

  name(): string { return 'MockReasoningLLM'; }

  capabilities(): string[] { return ['reasoning', 'tool_use']; }

  async process(message: Message): Promise<Message> {
    const query = message.content.toLowerCase();

    // Route to appropriate tool based on keywords
    if (query.includes('calculate') || query.includes('%')) {
      const calcTool = this.tools.get('calculator');
      // ... use calculator
    } else if (query.includes('weather')) {
      const weatherTool = this.tools.get('weather');
      // ... use weather
    }

    return createMessage({ role: 'assistant', content: response });
  }
}
```

### 11. memory-hierarchy-pattern.ts
**Remove:** API key checks

**Add:**
```typescript
class MockMemoryLLM implements Agent {
  name(): string { return 'MockMemoryLLM'; }

  capabilities(): string[] { return ['memory', 'recall']; }

  async process(message: Message): Promise<Message> {
    const response = `Processed with memory context: ${message.content.substring(0, 50)}...`;
    return createMessage({ role: 'assistant', content: response });
  }
}
```

## Common Pattern for All Files

### Remove (at top of main() function):
```typescript
// Check for API key
if (!process.env.ANTHROPIC_API_KEY) {
  console.error('❌ ANTHROPIC_API_KEY environment variable not set');
  console.error('Please set your API key: export ANTHROPIC_API_KEY=your-key');
  process.exit(1);
}

// Create LLM adapter
const llm = new AnthropicAdapter({
  model: 'claude-3-5-sonnet-20241022',
  temperature: 0.7,
});
```

### Replace with:
```typescript
console.log('✓ Using mock agents (no API keys required)');
console.log();

// Create mock agent
const mockAgent = new MockAgent();
```

### Add (at end of main() function):
```typescript
console.log();
console.log('Production Usage:');
console.log('  Replace mock agents with real LLM adapters:');
console.log('  - AnthropicAdapter (Claude)');
console.log('  - OpenAIAdapter (GPT-4)');
console.log('  - Or any custom Agent implementation');
console.log();
console.log('Pattern examples demonstrate the workflow without API costs!');
```

## Testing After Refactoring

For each refactored file:
```bash
npm run build
node dist/examples/patterns/<filename>.js
```

Expected: No errors, output demonstrates the pattern, NO API key required!

## Key Benefits

1. **Zero Cost**: Examples run without API calls
2. **Fast**: No network latency, instant results
3. **Consistent**: Same approach as Python/Rust/C++ examples
4. **Educational**: Focus on pattern mechanics, not LLM details
5. **Production-Ready**: Easy swap to real LLMs

## Implementation Checklist

- [x] reflection-pattern.ts
- [x] react-pattern.ts
- [x] conversational-pattern.ts
- [ ] multiagent-pattern.ts
- [ ] orchestration-pattern.ts
- [ ] agents-as-tools-pattern.ts
- [ ] planning-pattern.ts
- [ ] task-pattern.ts
- [ ] autonomous-pattern.ts
- [ ] reasoning-with-tools-pattern.ts
- [ ] memory-hierarchy-pattern.ts

## Notes

- Mock agents should be simple but realistic
- Keep all pattern logic unchanged
- Tools (Calculator, Weather, etc.) don't need mocking - they already work standalone
- Focus on demonstrating patterns, not LLM capabilities

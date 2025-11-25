/**
 * Tests for Agents-as-Tools pattern.
 */

import {
  AgentTool,
  OutputFormat,
  createAgentTool,
  createAgentToolSimple,
} from '../patterns/agents-as-tools';
import { Agent, Message, createMessage } from '../core/interfaces';

/**
 * Mock agent for testing.
 */
class MockAgent implements Agent {
  readonly name: string;
  readonly capabilities?: string[];
  private response: string;

  constructor(name: string, response: string, capabilities?: string[]) {
    this.name = name;
    this.response = response;
    this.capabilities = capabilities;
  }

  async process(message: Message): Promise<Message> {
    return createMessage('assistant', this.response);
  }
}

describe('AgentTool', () => {
  describe('Configuration Validation', () => {
    it('should require agent', () => {
      expect(() => {
        new AgentTool({
          agent: null as any,
          name: 'test_tool',
          description: 'Test tool',
        });
      }).toThrow('agent is required');
    });

    it('should require non-empty name', () => {
      expect(() => {
        new AgentTool({
          agent: new MockAgent('test', 'response'),
          name: '',
          description: 'Test tool',
        });
      }).toThrow('tool name cannot be empty');
    });

    it('should require non-empty description', () => {
      expect(() => {
        new AgentTool({
          agent: new MockAgent('test', 'response'),
          name: 'test_tool',
          description: '',
        });
      }).toThrow('tool description cannot be empty');
    });

    it('should use default values', () => {
      const tool = new AgentTool({
        agent: new MockAgent('test', 'response'),
        name: 'test_tool',
        description: 'Test description',
      });

      expect(tool.name).toBe('test_tool');
      expect(tool.description).toBe('Test description');
      expect(tool.getInputKey()).toBe('query');
      expect(tool.getOutputFormat()).toBe(OutputFormat.STRING);
    });

    it('should use custom values', () => {
      const tool = new AgentTool({
        agent: new MockAgent('test', 'response'),
        name: 'custom_tool',
        description: 'Custom description',
        inputKey: 'task',
        outputFormat: OutputFormat.DICT,
        includeMetadata: true,
      });

      expect(tool.getInputKey()).toBe('task');
      expect(tool.getOutputFormat()).toBe(OutputFormat.DICT);
    });
  });

  describe('Basic Execution', () => {
    it('should execute agent and return string output', async () => {
      const agent = new MockAgent('test_agent', 'Hello from agent');
      const tool = new AgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
      });

      const result = await tool.execute({ query: 'Test input' });

      expect(result.success).toBe(true);
      expect(result.output).toBe('Hello from agent');
      expect(result.metadata?.agentName).toBe('test_agent');
      expect(result.metadata?.toolName).toBe('test_tool');
    });

    it('should handle missing parameter', async () => {
      const agent = new MockAgent('test_agent', 'response');
      const tool = new AgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
        inputKey: 'required_param',
      });

      const result = await tool.execute({ wrong_param: 'value' });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Missing required parameter 'required_param'");
    });

    it('should handle agent errors', async () => {
      class ErrorAgent implements Agent {
        readonly name = 'error_agent';
        async process(): Promise<Message> {
          throw new Error('Agent processing failed');
        }
      }

      const tool = new AgentTool({
        agent: new ErrorAgent(),
        name: 'test_tool',
        description: 'Test tool',
      });

      const result = await tool.execute({ query: 'test' });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Agent 'error_agent' failed");
      expect(result.error).toContain('Agent processing failed');
    });
  });

  describe('Output Formats', () => {
    it('should return string output', async () => {
      const agent = new MockAgent('test_agent', 'test response');
      const tool = new AgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
        outputFormat: OutputFormat.STRING,
      });

      const result = await tool.execute({ query: 'test' });

      expect(typeof result.output).toBe('string');
      expect(result.output).toBe('test response');
    });

    it('should return dict output without metadata', async () => {
      const agent = new MockAgent('test_agent', 'test response');
      const tool = new AgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
        outputFormat: OutputFormat.DICT,
        includeMetadata: false,
      });

      const result = await tool.execute({ query: 'test' });

      expect(typeof result.output).toBe('object');
      const output = result.output as Record<string, unknown>;
      expect(output.content).toBe('test response');
      expect(output.metadata).toBeUndefined();
    });

    it('should return dict output with metadata', async () => {
      const agent = new MockAgent('test_agent', 'test response');
      const tool = new AgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
        outputFormat: OutputFormat.DICT,
        includeMetadata: true,
      });

      const result = await tool.execute({ query: 'test' });

      const output = result.output as Record<string, unknown>;
      expect(output.content).toBe('test response');
      expect(output.metadata).toBeDefined();
    });

    it('should return message output', async () => {
      const agent = new MockAgent('test_agent', 'test response');
      const tool = new AgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
        outputFormat: OutputFormat.MESSAGE,
      });

      const result = await tool.execute({ query: 'test' });

      const message = result.output as Message;
      expect(message.role).toBe('assistant');
      expect(message.content).toBe('test response');
      expect(message.timestamp).toBeDefined();
    });
  });

  describe('Custom Input Key', () => {
    it('should use custom input key', async () => {
      const agent = new MockAgent('test_agent', 'response');
      const tool = new AgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
        inputKey: 'custom_input',
      });

      const result = await tool.execute({ custom_input: 'test value' });

      expect(result.success).toBe(true);
      expect(result.output).toBe('response');
    });

    it('should fail with wrong input key', async () => {
      const agent = new MockAgent('test_agent', 'response');
      const tool = new AgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
        inputKey: 'expected_key',
      });

      const result = await tool.execute({ wrong_key: 'value' });

      expect(result.success).toBe(false);
      expect(result.error).toContain('expected_key');
    });
  });

  describe('Accessors', () => {
    it('should provide agent accessor', () => {
      const agent = new MockAgent('test_agent', 'response');
      const tool = new AgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
      });

      expect(tool.getAgent()).toBe(agent);
    });

    it('should provide toString method', () => {
      const agent = new MockAgent('test_agent', 'response');
      const tool = new AgentTool({
        agent,
        name: 'my_tool',
        description: 'Test tool',
      });

      const str = tool.toString();
      expect(str).toBe("AgentTool(name='my_tool', agent=test_agent)");
    });

    it('should have parameters schema', () => {
      const agent = new MockAgent('test_agent', 'response');
      const tool = new AgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
        inputKey: 'task',
      });

      expect(tool.parametersSchema).toBeDefined();
      expect(tool.parametersSchema?.properties).toHaveProperty('task');
      expect(tool.parametersSchema?.required).toContain('task');
    });
  });

  describe('Convenience Functions', () => {
    it('should create tool with createAgentTool', () => {
      const agent = new MockAgent('test_agent', 'response');
      const tool = createAgentTool({
        agent,
        name: 'test_tool',
        description: 'Test tool',
        inputKey: 'query',
        outputFormat: OutputFormat.STRING,
      });

      expect(tool.name).toBe('test_tool');
      expect(tool.getInputKey()).toBe('query');
    });

    it('should create tool with createAgentToolSimple', () => {
      const agent = new MockAgent('test_agent', 'response');
      const tool = createAgentToolSimple(agent, 'test_tool', 'Test tool');

      expect(tool.name).toBe('test_tool');
      expect(tool.getInputKey()).toBe('query');
      expect(tool.getOutputFormat()).toBe(OutputFormat.STRING);
    });
  });

  describe('Integration Scenarios', () => {
    it('should enable hierarchical agent delegation', async () => {
      // Create specialist agents
      const codeAgent = new MockAgent('code_specialist', 'def hello(): print("hello")', [
        'programming',
        'code-review',
      ]);
      const mathAgent = new MockAgent('math_specialist', '42', [
        'mathematics',
        'calculations',
      ]);

      // Wrap as tools
      const codeTool = createAgentToolSimple(
        codeAgent,
        'code_expert',
        'Expert in programming'
      );
      const mathTool = createAgentToolSimple(
        mathAgent,
        'math_expert',
        'Expert in mathematics'
      );

      // Use code tool
      const codeResult = await codeTool.execute({
        query: 'Write a hello function',
      });
      expect(codeResult.success).toBe(true);
      expect(codeResult.output).toContain('def hello()');

      // Use math tool
      const mathResult = await mathTool.execute({
        query: 'What is the answer?',
      });
      expect(mathResult.success).toBe(true);
      expect(mathResult.output).toBe('42');
    });

    it('should handle different output formats in same system', async () => {
      const agent = new MockAgent('test_agent', 'response');

      const stringTool = createAgentTool({
        agent,
        name: 'string_tool',
        description: 'Returns string',
        outputFormat: OutputFormat.STRING,
      });

      const dictTool = createAgentTool({
        agent,
        name: 'dict_tool',
        description: 'Returns dict',
        outputFormat: OutputFormat.DICT,
      });

      const stringResult = await stringTool.execute({ query: 'test' });
      expect(typeof stringResult.output).toBe('string');

      const dictResult = await dictTool.execute({ query: 'test' });
      expect(typeof dictResult.output).toBe('object');
    });
  });
});

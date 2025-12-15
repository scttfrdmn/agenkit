import { useState, useEffect } from 'react';
import type { ZigAgent } from '@agenkit/wasm';

// Import from local package during development
// In production: import { createZigAgent } from '@agenkit/wasm';
declare const createZigAgent: (moduleName: string, agentName: string, capabilities?: string[], debug?: boolean) => Promise<ZigAgent>;

function App() {
  const [agent, setAgent] = useState<ZigAgent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [processing, setProcessing] = useState(false);
  const [selectedModule, setSelectedModule] = useState('echo_example');

  // Available WASM modules
  const modules = [
    { id: 'echo_example', name: 'Echo', description: 'Simple echo agent' },
    { id: 'reflection_example', name: 'Reflection', description: 'Self-reflection pattern' },
    { id: 'sequential_example', name: 'Sequential', description: 'Sequential processing' },
    { id: 'parallel_example', name: 'Parallel', description: 'Parallel processing' },
    { id: 'react_example', name: 'ReAct', description: 'Reasoning + acting' },
  ];

  // Load agent on mount or when module changes
  useEffect(() => {
    let mounted = true;

    async function loadAgent() {
      try {
        setLoading(true);
        setError(null);
        setResponse('');

        // Load the selected WASM module
        const newAgent = await createZigAgent(
          selectedModule,
          `react-${selectedModule}`,
          ['browser', 'demo'],
          true // debug mode
        );

        if (mounted) {
          setAgent(newAgent);
          setLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load agent');
          setLoading(false);
        }
      }
    }

    loadAgent();

    return () => {
      mounted = false;
    };
  }, [selectedModule]);

  const handleSend = async () => {
    if (!agent || !message.trim() || processing) return;

    try {
      setProcessing(true);
      setError(null);

      const result = await agent.process({
        role: 'user',
        content: message,
        metadata: {
          timestamp: new Date().toISOString(),
          source: 'react-app',
        },
      });

      if (result.ok && result.message) {
        setResponse(result.message.content);
      } else if (result.error) {
        setError(`${result.error.type}: ${result.error.message}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
    } finally {
      setProcessing(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '2rem', fontFamily: 'system-ui, sans-serif' }}>
      <h1>🚀 Agenkit WASM + React</h1>
      <p style={{ color: '#666' }}>
        Run AI agents in the browser using WebAssembly
      </p>

      {/* Module Selector */}
      <div style={{ marginBottom: '1.5rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
          Select Agent Pattern:
        </label>
        <select
          value={selectedModule}
          onChange={(e) => setSelectedModule(e.target.value)}
          disabled={loading || processing}
          style={{
            width: '100%',
            padding: '0.75rem',
            fontSize: '1rem',
            border: '2px solid #ddd',
            borderRadius: '8px',
          }}
        >
          {modules.map((mod) => (
            <option key={mod.id} value={mod.id}>
              {mod.name} - {mod.description}
            </option>
          ))}
        </select>
      </div>

      {/* Status */}
      {loading && (
        <div style={{
          padding: '1rem',
          backgroundColor: '#e3f2fd',
          borderRadius: '8px',
          marginBottom: '1rem',
        }}>
          <strong>⏳ Loading agent...</strong>
          <p style={{ margin: '0.5rem 0 0', color: '#666' }}>
            Initializing {selectedModule} WASM module
          </p>
        </div>
      )}

      {error && (
        <div style={{
          padding: '1rem',
          backgroundColor: '#ffebee',
          borderRadius: '8px',
          marginBottom: '1rem',
          color: '#c62828',
        }}>
          <strong>❌ Error:</strong>
          <p style={{ margin: '0.5rem 0 0' }}>{error}</p>
        </div>
      )}

      {agent && !loading && (
        <>
          {/* Agent Info */}
          <div style={{
            padding: '1rem',
            backgroundColor: '#f5f5f5',
            borderRadius: '8px',
            marginBottom: '1rem',
          }}>
            <strong>✅ Agent Loaded</strong>
            <p style={{ margin: '0.5rem 0 0', color: '#666' }}>
              Name: {agent.name} | Capabilities: {agent.capabilities.join(', ')}
            </p>
          </div>

          {/* Input Area */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
              Your Message:
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              disabled={processing}
              rows={4}
              style={{
                width: '100%',
                padding: '0.75rem',
                fontSize: '1rem',
                border: '2px solid #ddd',
                borderRadius: '8px',
                fontFamily: 'inherit',
                resize: 'vertical',
              }}
            />
          </div>

          <button
            onClick={handleSend}
            disabled={!message.trim() || processing}
            style={{
              width: '100%',
              padding: '1rem',
              fontSize: '1rem',
              fontWeight: 'bold',
              color: 'white',
              backgroundColor: processing ? '#999' : '#1976d2',
              border: 'none',
              borderRadius: '8px',
              cursor: processing ? 'not-allowed' : 'pointer',
            }}
          >
            {processing ? '⏳ Processing...' : '🚀 Send to Agent'}
          </button>

          {/* Response Area */}
          {response && (
            <div style={{
              marginTop: '1.5rem',
              padding: '1rem',
              backgroundColor: '#e8f5e9',
              borderRadius: '8px',
              border: '2px solid #4caf50',
            }}>
              <strong style={{ color: '#2e7d32' }}>🤖 Agent Response:</strong>
              <p style={{ margin: '0.75rem 0 0', whiteSpace: 'pre-wrap' }}>
                {response}
              </p>
            </div>
          )}
        </>
      )}

      {/* Footer */}
      <div style={{
        marginTop: '3rem',
        paddingTop: '1.5rem',
        borderTop: '1px solid #ddd',
        color: '#666',
        fontSize: '0.875rem',
      }}>
        <p>
          <strong>How it works:</strong> This app loads a WebAssembly module compiled from Zig,
          instantiates it with WASI support, and provides a JavaScript interface for processing messages.
        </p>
        <p>
          <strong>Module size:</strong> 4.5KB-66KB per agent | <strong>Load time:</strong> &lt;10ms
        </p>
        <p>
          Learn more: <a href="https://github.com/agenkit/agenkit" target="_blank" rel="noopener">
            github.com/agenkit/agenkit
          </a>
        </p>
      </div>
    </div>
  );
}

export default App;

'use client';

import { useState } from 'react';

export default function Home() {
  const [agentType, setAgentType] = useState<'react' | 'conversational' | 'router'>('react');
  const [message, setMessage] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!message.trim()) return;

    // Add user message to UI
    setMessages((prev) => [...prev, { role: 'user', content: message }]);
    setLoading(true);

    try {
      const response = await fetch('/api/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_type: agentType,
          message: { role: 'user', content: message },
          session_id: sessionId || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      // Update session ID if new
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }

      // Add assistant response to UI
      setMessages((prev) => [...prev, { role: 'assistant', content: data.content }]);
      setMessage('');
    } catch (error) {
      console.error('Error:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'error',
          content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clearSession = () => {
    setMessages([]);
    setSessionId('');
    setMessage('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Agenkit on Vercel Edge Functions
          </h1>
          <p className="text-gray-600">
            Edge-native AI agents with global distribution and sub-50ms cold starts
          </p>
        </div>

        {/* Configuration */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Configuration</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Agent Type
              </label>
              <select
                value={agentType}
                onChange={(e) =>
                  setAgentType(e.target.value as 'react' | 'conversational' | 'router')
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="react">ReAct (Reasoning + Tools)</option>
                <option value="conversational">Conversational</option>
                <option value="router">Router (Auto-select)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Session ID
              </label>
              <input
                type="text"
                value={sessionId}
                readOnly
                placeholder="Auto-generated"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50"
              />
            </div>
          </div>

          <button
            onClick={clearSession}
            className="mt-4 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
          >
            Clear Session
          </button>
        </div>

        {/* Chat Interface */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Chat</h2>

          {/* Messages */}
          <div className="h-96 overflow-y-auto mb-4 space-y-3 border border-gray-200 rounded-lg p-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-400 py-20">
                <p className="text-lg mb-2">No messages yet</p>
                <p className="text-sm">
                  Try: &quot;Calculate 15 × 3&quot; or &quot;Hello, how are you?&quot;
                </p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-blue-100 ml-auto max-w-[80%]'
                      : msg.role === 'error'
                      ? 'bg-red-100 max-w-[80%]'
                      : 'bg-gray-100 mr-auto max-w-[80%]'
                  }`}
                >
                  <div className="text-xs font-semibold text-gray-600 mb-1">
                    {msg.role === 'user' ? 'You' : msg.role === 'error' ? 'Error' : 'Agent'}
                  </div>
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>
              ))
            )}
          </div>

          {/* Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !loading && sendMessage()}
              placeholder="Type your message..."
              disabled={loading}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
            />
            <button
              onClick={sendMessage}
              disabled={loading || !message.trim()}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {loading ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-2">ReAct Agent</h3>
            <p className="text-sm text-gray-600">
              Combines reasoning with tool use (calculator). Try: &quot;Calculate 100 + 50&quot;
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-2">Conversational</h3>
            <p className="text-sm text-gray-600">
              Multi-turn conversations with context. Try: &quot;Hello, how are you?&quot;
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-2">Router Agent</h3>
            <p className="text-sm text-gray-600">
              Auto-selects best agent. Try: &quot;Calculate 5 + 3 and explain&quot;
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-gray-600 text-sm">
          <p>
            Powered by{' '}
            <a
              href="https://github.com/scttfrdmn/agenkit"
              className="text-blue-500 hover:underline"
            >
              Agenkit
            </a>
            {' '}•{' '}
            Deployed on{' '}
            <a href="https://vercel.com" className="text-blue-500 hover:underline">
              Vercel Edge Functions
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

<script>
  import { onMount, tick } from 'svelte';

  let messages = [];
  let input = '';
  let isStreaming = false;
  let messagesContainer;
  let streamBuffer = '';

  async function scrollToBottom() {
    await tick();
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  $: messages && scrollToBottom();

  async function sendMessage() {
    if (!input.trim() || isStreaming) return;

    messages = [...messages, { role: 'user', content: input }];
    const userInput = input;
    input = '';
    isStreaming = true;
    streamBuffer = '';

    try {
      const response = await fetch('/agui', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: 'svelte-' + Date.now(),
          message: userInput,
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));

              if (event.type === 'text_message_content') {
                streamBuffer += event.delta;

                const lastMsg = messages[messages.length - 1];
                if (lastMsg && lastMsg.role === 'assistant') {
                  messages[messages.length - 1] = { ...lastMsg, content: streamBuffer };
                } else {
                  messages = [...messages, { role: 'assistant', content: streamBuffer }];
                }
              }
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      messages = [...messages, { role: 'assistant', content: '❌ Error occurred' }];
    } finally {
      isStreaming = false;
      streamBuffer = '';
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      sendMessage();
    }
  }
</script>

<div class="chat-container">
  <div class="header">
    <h1>⚡ Svelte + AG-UI</h1>
    <p>Custom SSE Integration (~300 LOC)</p>
  </div>

  <div class="messages" bind:this={messagesContainer}>
    {#if messages.length === 0}
      <div class="welcome">
        <h2>Welcome!</h2>
        <p>This is a custom Svelte frontend consuming AG-UI Standard protocol via SSE.</p>
        <p>Try: "Hello" or "Help"</p>
      </div>
    {/if}

    {#each messages as msg, i (i)}
      <div class="message {msg.role}">
        <div class="role">{msg.role === 'user' ? '👤' : '🤖'}</div>
        <div class="content">{msg.content}</div>
      </div>
    {/each}

    {#if isStreaming && messages[messages.length - 1]?.role === 'user'}
      <div class="message assistant">
        <div class="role">🤖</div>
        <div class="content typing">Thinking...</div>
      </div>
    {/if}
  </div>

  <div class="input-area">
    <input
      type="text"
      bind:value={input}
      on:keydown={handleKeyDown}
      placeholder="Type a message..."
      disabled={isStreaming}
    />
    <button on:click={sendMessage} disabled={!input.trim() || isStreaming}>
      {isStreaming ? '⏳' : '📤'}
    </button>
  </div>

  <div class="footer">
    <span>Powered by Agenkit AG-UI Standard</span>
    <span>•</span>
    <span>Svelte 4</span>
  </div>
</div>

<style>
  .chat-container {
    background: white;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    display: flex;
    flex-direction: column;
    height: 80vh;
    max-height: 700px;
  }

  .header {
    padding: 1.5rem;
    background: linear-gradient(135deg, #ff3e00 0%, #40b3ff 100%);
    color: white;
    text-align: center;
    border-radius: 16px 16px 0 0;
  }

  .header h1 {
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
  }

  .header p {
    font-size: 0.9rem;
    opacity: 0.9;
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
    background: #f8f9fa;
  }

  .welcome {
    text-align: center;
    padding: 2rem;
    color: #64748b;
  }

  .welcome h2 {
    color: #ff3e00;
    margin-bottom: 1rem;
  }

  .message {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    animation: fadeIn 0.3s;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .message .role {
    font-size: 1.5rem;
    flex-shrink: 0;
  }

  .message .content {
    background: white;
    padding: 1rem;
    border-radius: 12px;
    flex: 1;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    white-space: pre-wrap;
  }

  .message.user .content {
    background: linear-gradient(135deg, #ff3e00 0%, #40b3ff 100%);
    color: white;
  }

  .typing {
    color: #ff3e00;
    font-weight: 600;
  }

  .input-area {
    padding: 1.5rem;
    background: white;
    border-top: 1px solid #e2e8f0;
    display: flex;
    gap: 1rem;
    border-radius: 0 0 16px 16px;
  }

  input {
    flex: 1;
    padding: 0.75rem;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    font-size: 0.95rem;
    font-family: inherit;
  }

  input:focus {
    outline: none;
    border-color: #ff3e00;
  }

  button {
    padding: 0.75rem 1.5rem;
    background: linear-gradient(135deg, #ff3e00 0%, #40b3ff 100%);
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    transition: transform 0.2s;
  }

  button:hover:not(:disabled) {
    transform: translateY(-2px);
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .footer {
    padding: 0.75rem;
    background: #f8f9fa;
    text-align: center;
    font-size: 0.85rem;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    display: flex;
    justify-content: center;
    gap: 0.5rem;
  }
</style>

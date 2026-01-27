import { useState, useRef, useEffect } from 'react'
import './App.css'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const messagesEndRef = useRef(null)
  const streamBufferRef = useRef('')

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || isStreaming) return

    const userMsg = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsStreaming(true)
    streamBufferRef.current = ''

    try {
      const response = await fetch('/agui', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: 'react-' + Date.now(),
          message: input,
        }),
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))

              if (event.type === 'text_message_content') {
                streamBufferRef.current += event.delta

                setMessages(prev => {
                  const newMsgs = [...prev]
                  if (newMsgs[newMsgs.length - 1]?.role === 'assistant') {
                    newMsgs[newMsgs.length - 1].content = streamBufferRef.current
                  } else {
                    newMsgs.push({ role: 'assistant', content: streamBufferRef.current })
                  }
                  return newMsgs
                })
              }
            } catch (e) {
              console.error('Parse error:', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, { role: 'assistant', content: '❌ Error occurred' }])
    } finally {
      setIsStreaming(false)
      streamBufferRef.current = ''
    }
  }

  return (
    <div className="chat-container">
      <div className="header">
        <h1>⚛️ React + AG-UI</h1>
        <p>Custom SSE Integration (~300 LOC)</p>
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <div className="welcome">
            <h2>Welcome!</h2>
            <p>This is a custom React frontend consuming AG-UI Standard protocol via SSE.</p>
            <p>Try: "Hello" or "Help"</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="role">{msg.role === 'user' ? '👤' : '🤖'}</div>
            <div className="content">{msg.content}</div>
          </div>
        ))}

        {isStreaming && messages[messages.length - 1]?.role === 'user' && (
          <div className="message assistant">
            <div className="role">🤖</div>
            <div className="content typing">Thinking...</div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Type a message..."
          disabled={isStreaming}
        />
        <button onClick={sendMessage} disabled={!input.trim() || isStreaming}>
          {isStreaming ? '⏳' : '📤'}
        </button>
      </div>

      <div className="footer">
        <span>Powered by Agenkit AG-UI Standard</span>
        <span>•</span>
        <span>React 18</span>
      </div>
    </div>
  )
}

export default App

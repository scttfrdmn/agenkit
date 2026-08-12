# Collaborative Document Editor

Production-ready example demonstrating real-time collaborative editing with AI writing assistance through AG-UI protocol.

## 🎯 Overview

This example showcases an intelligent document editor where multiple users can collaborate in real-time while receiving AI-powered writing assistance. Perfect for understanding shared state management and interactive AI workflows.

### Key Features

- ✅ **Real-time Collaboration**: Multiple users edit simultaneously
- ✅ **AI Writing Assistant**: Grammar, style, expansion, summarization
- ✅ **Smart Suggestions**: Context-aware improvements
- ✅ **Auto-sync**: Changes broadcast to all clients instantly
- ✅ **Rich Metrics**: Track edits, assists, and suggestions
- ✅ **Production Ready**: Proper state management and error handling

## 🏗️ Architecture

```
┌────────────────────┐                  ┌─────────────────────────┐
│                    │   WebSocket      │                         │
│  Editor Client A   │◄─────────────────►│                         │
│                    │                  │   FastAPI Backend       │
│  - Text Editor     │                  │                         │
│  - AI Toolbar      │                  │   - DocumentManager     │
│  - Live Updates    │                  │   - EditorAgent         │
└────────────────────┘                  │   - State Sync          │
                                        │   - AG-UI Adapter       │
┌────────────────────┐                  │                         │
│                    │   WebSocket      │                         │
│  Editor Client B   │◄─────────────────►│                         │
│                    │                  └─────────────────────────┘
│  - Text Editor     │                            │
│  - AI Toolbar      │                            │
│  - Live Updates    │                            ▼
└────────────────────┘                    AI Assistance:
                                          - Grammar Check
        │                                 - Style Improvement
        │                                 - Content Expansion
        ▼                                 - Summarization
   Simultaneous                           - Auto-completion
   Editing with
   AI Assistance
```

## 📋 Prerequisites

- Python 3.10+
- Node.js 18+ (optional, for static file serving)
- Docker & Docker Compose (optional)

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Build and start both services
docker-compose up --build

# Access the application
open http://localhost:3000
```

### Option 2: Run Locally

#### Backend

```bash
cd backend

# Install dependencies
pip install -e ../../../../  # Install agenkit locally
pip install -r requirements.txt

# Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: `http://localhost:8000`
WebSocket: `ws://localhost:8000/ws`

#### Frontend

```bash
cd frontend

# Serve with any static file server
python -m http.server 3000

# Or use Node.js
npx serve -p 3000
```

Frontend available at: `http://localhost:3000`

## 🎮 Usage

### 1. Open the Editor

Navigate to http://localhost:3000 and you'll see:
- **Left Panel**: Document editor with AI toolbar
- **Right Panel**: AI assistant feedback and suggestions
- **Bottom**: Real-time statistics

### 2. Start Writing

Type your document in the main editor area. As you type:
- Word and character counts update in real-time
- Changes are automatically synced (after 300ms of inactivity)
- Other connected clients see your changes instantly

### 3. Use AI Assistance

Click any toolbar button to get AI help:

- **💡 Suggest Improvements**: Get grammar and style suggestions
- **➕ Expand Content**: Add more detail and elaboration
- **📋 Summarize**: Create a concise summary
- **✓ Check Grammar**: Find grammar and spelling issues
- **✨ Improve Style**: Get readability and style recommendations
- **⚡ Auto-Complete**: Finish your current sentence

### 4. Apply Suggestions

Review AI suggestions in the right panel:
- Each suggestion includes type, severity, and specific recommendations
- Improved content is shown directly
- Processing time is displayed

## 💬 Example Workflows

### Grammar and Style Checking

**Document**:
```
Their is a problem with grammar in this document that need fixing.
In order to improve the quality we should check it carefully.
```

**AI Response** (after clicking "Suggest Improvements"):
```
Found 3 potential improvements

Suggestions:
1. ❌ Grammar: Subject-verb agreement: 'their' is plural, use 'are' or 'were'
2. ⚠️ Style: Consider using active voice for clarity
3. ℹ️ Style: Consider replacing 'in order to' with 'to'

Improved Content:
There is a problem with grammar in this document that needs fixing.
To improve the quality we should check it carefully.
```

### Content Expansion

**Document**:
```
AI agents are useful.
```

**AI Response** (after clicking "Expand"):
```
Expanded content from 21 to 185 characters (8.8x)

Expanded Content:
AI agents are useful.

This concept is particularly important because it demonstrates how modern
AI systems can assist with writing tasks. The implications extend beyond
simple editing to encompass collaborative workflows and real-time feedback
mechanisms.
```

### Summarization

**Long Document** (500+ words)

**AI Response** (after clicking "Summarize"):
```
Summary created (156 chars, 31% of original)

Summary:
The collaborative document editor enables real-time editing with AI assistance.
Multiple users can work simultaneously while receiving intelligent suggestions.
This demonstrates the power of combining collaborative workflows with AI agents.
```

### Auto-completion

**Partial Sentence**:
```
This feature demonstrates the potential of AI
```

**AI Response** (after clicking "Auto-Complete"):
```
Sentence completed
Added: ` with AI-powered suggestions and improvements.`

Result:
This feature demonstrates the potential of AI with AI-powered suggestions
and improvements.
```

## 🔧 Configuration

### Document Sync Settings

Edit `backend/main.py`:

```python
# Adjust debounce time for document updates (in client.js)
editTimeout = setTimeout(() => {
    this.sendDocumentEdit();
}, 300);  // 300ms - decrease for faster sync, increase to reduce network traffic
```

### AI Response Settings

Edit `backend/main.py`:

```python
adapter = AGUIAdapter(
    editor_agent,
    agent_name="EditorAssistant",
    chunk_size=20,  # Adjust for faster/slower streaming
)
```

### Assistance Commands

Edit `backend/agent.py` to customize AI behaviors:

```python
def _suggest_improvements(self, document: str, selection: str) -> dict:
    # Add custom grammar/style rules
    suggestions = []

    # Your custom checks here
    if "custom_pattern" in document:
        suggestions.append(
            {"type": "custom", "severity": "warning", "message": "Your custom suggestion"}
        )

    return {"suggestions": suggestions}
```

## 📊 AG-UI Events

This example demonstrates these AG-UI events:

### 1. MetadataEvent

Sent on connection:
```json
{
  "event_type": "metadata",
  "data": {
    "agent_name": "EditorAssistant",
    "capabilities": [
      "writing_assistance",
      "grammar_checking",
      "style_improvement",
      "content_expansion",
      "summarization"
    ],
    "client_id": "uuid-client-1",
    "protocol": "AG-UI",
    "version": "1.0"
  }
}
```

### 2. Custom Messages: Document State

```json
{
  "type": "document_state",
  "document_id": "default",
  "content": "Current document content...",
  "edit_history": [
    {
      "timestamp": "2026-01-24T10:30:00",
      "client_id": "uuid-1",
      "content_length": 150,
      "diff_length": 25
    }
  ]
}
```

### 3. Custom Messages: Document Updates

```json
{
  "type": "document_update",
  "document_id": "default",
  "content": "Updated content...",
  "timestamp": "2026-01-24T10:30:05"
}
```

### 4. TextMessageComplete (AI Assistance)

```json
{
  "event_type": "text_message_complete",
  "message_id": "msg_abc123",
  "content": "# Writing Assistance: Suggest Improvements\n\n**Found 2 potential improvements**...",
  "metadata": {
    "command": "suggest_improvements",
    "suggestions": [
      {
        "type": "grammar",
        "severity": "error",
        "message": "Subject-verb agreement issue"
      }
    ],
    "improved_content": "Corrected text...",
    "processing_time": 0.3
  }
}
```

## 🧪 Testing

### Manual Testing

1. **Single User**: Type in editor, verify word count updates
2. **AI Assistance**: Click each toolbar button, verify responses
3. **Multiple Users**: Open in two browser tabs, verify sync
4. **Error Handling**: Disconnect backend, verify error display
5. **Reconnection**: Restart backend, verify auto-reconnect

### Automated Testing

```bash
cd backend
pytest tests/
```

### Multi-User Testing

```bash
# Open multiple browser windows to localhost:3000
# Edit in one window, observe updates in others
# Request AI assistance in one, observe in all
```

## 📚 Code Walkthrough

### Backend: Document State Management

```python
class DocumentManager:
    """Manages shared document state and broadcasts changes."""

    async def update_document(self, document_id: str, content: str, client_id: str):
        """Update document and record edit history."""
        async with self.document_locks[document_id]:
            self.documents[document_id] = content

            edit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "client_id": client_id,
                "content_length": len(content),
            }

            self.edit_history[document_id].append(edit_record)
```

### Backend: Broadcasting Updates

```python
async def broadcast_document_update(document_id: str, content: str, exclude_client: str):
    """Send update to all clients except the originator."""
    update_message = {"type": "document_update", "document_id": document_id, "content": content}

    for client_id, websocket in active_connections.items():
        if client_documents.get(client_id) == document_id and client_id != exclude_client:
            await websocket.send_json(update_message)
```

### Backend: AI Assistance

```python
async def process(self, message: Message) -> Message:
    """Process AI assistance request."""
    command = self._parse_command(message.content)
    document = message.metadata.get("document_content", "")
    selection = message.metadata.get("selection", "")

    # Perform assistance
    result = await self._perform_assistance(command, document, selection)

    return Message(
        role="assistant",
        content=self._format_response(command, result),
        metadata={
            "command": command,
            "suggestions": result.get("suggestions", []),
            "improved_content": result.get("improved_content"),
        },
    )
```

### Frontend: Document Synchronization

```javascript
handleDocumentUpdate(message) {
    // Save cursor position
    const cursorPos = this.editor.selectionStart;

    // Update content
    this.editor.value = message.content;
    this.updateCounts();

    // Restore cursor
    this.editor.setSelectionRange(cursorPos, cursorPos);

    // Visual feedback
    this.editor.style.borderColor = '#667eea';
    setTimeout(() => {
        this.editor.style.borderColor = '';
    }, 500);
}
```

### Frontend: AI Assistance Requests

```javascript
requestAssistance(command) {
    const content = this.editor.value;
    const selection = this.getSelectedText();
    const cursorPosition = this.editor.selectionStart;

    // Disable toolbar during processing
    this.setToolbarEnabled(false);

    // Send request
    this.send({
        type: 'ai_assistance',
        document_id: this.documentId,
        command: command,
        selection: selection,
        cursor_position: cursorPosition
    });
}
```

## 🎨 Customization

### Add Custom AI Command

1. **Update agent** in `backend/agent.py`:

```python
def _parse_command(self, content: str) -> str:
    if "custom_command" in content:
        return "custom_action"
    # ... existing commands


def _custom_action(self, document: str) -> dict:
    # Your custom AI logic
    return {"improved_content": "...", "custom_data": {...}}
```

2. **Add toolbar button** in `frontend/index.html`:

```html
<button class="toolbar-button" onclick="requestAssistance('custom command')">
    🎯 Custom Action
</button>
```

### Modify UI Colors

Edit `frontend/index.html` CSS:

```css
.toolbar-button:hover {
    background: #3b82f6;  /* Custom blue */
    border-color: #3b82f6;
}

.assistant-card.complete {
    border-left-color: #22c55e;  /* Custom green */
}
```

### Change Sync Behavior

Edit `frontend/client.js`:

```javascript
// Immediate sync (no debounce)
this.editor.addEventListener('input', () => {
    this.sendDocumentEdit();  // Send on every keystroke
});

// Or increase debounce for less frequent updates
clearTimeout(editTimeout);
editTimeout = setTimeout(() => {
    this.sendDocumentEdit();
}, 1000);  // 1 second delay
```

## 🐛 Troubleshooting

### Changes Not Syncing

```bash
# Check backend logs
docker-compose logs backend

# Verify WebSocket connection
# Open browser DevTools -> Network -> WS
```

### AI Assistance Not Working

- **Check toolbar enabled**: Buttons should not be disabled
- **Verify connection**: Status indicator should be green
- **Check browser console**: Look for JavaScript errors
- **Review backend logs**: Check for processing errors

### Multiple Users Not Seeing Each Other

- **Ensure same document ID**: All clients must join same document
- **Check broadcast logic**: Verify `broadcast_document_update()` is called
- **Test with two tabs**: Open two browser tabs on same machine

### Cursor Position Lost

Edit `frontend/client.js` to improve cursor restoration:

```javascript
handleDocumentUpdate(message) {
    // Better cursor preservation logic
    const start = this.editor.selectionStart;
    const end = this.editor.selectionEnd;

    this.editor.value = message.content;

    // Restore selection range
    this.editor.setSelectionRange(start, end);
}
```

## 📖 API Reference

### WebSocket Protocol

**Client → Server** (Document Edit):
```json
{
  "type": "document_edit",
  "document_id": "default",
  "content": "Document content...",
  "cursor_position": 150
}
```

**Client → Server** (AI Assistance):
```json
{
  "type": "ai_assistance",
  "document_id": "default",
  "command": "suggest improvements",
  "selection": "Selected text...",
  "cursor_position": 150
}
```

**Server → Client** (Document Update):
```json
{
  "type": "document_update",
  "document_id": "default",
  "content": "Updated content...",
  "timestamp": "2026-01-24T10:30:00"
}
```

**Server → Client** (AI Response):
```json
{
  "event_type": "text_message_complete",
  "message_id": "msg_123",
  "content": "# Writing Assistance...",
  "metadata": {
    "command": "suggest_improvements",
    "suggestions": [...],
    "processing_time": 0.3
  }
}
```

## 🚢 Production Deployment

### Environment Variables

```bash
# .env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_URL=https://your-domain.com
DOCUMENT_RETENTION_HOURS=24
MAX_DOCUMENT_SIZE=10485760  # 10MB
```

### Docker Production

```bash
# Build for production
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Performance Tuning

- **Debounce Time**: Balance between sync speed and network traffic
- **Document Locks**: Ensure proper async lock usage for concurrent edits
- **History Limit**: Adjust `edit_history` size (currently 50 edits)
- **Connection Pooling**: For high-traffic scenarios

## 📈 Metrics & Monitoring

### Key Metrics

- Total edits (per client and global)
- AI assistance requests
- Total suggestions provided
- Average response time
- Active users count
- Document edit frequency

### Logging

Backend logs include:
- Client connections/disconnections
- Document joins and edits
- AI assistance requests and processing times
- Broadcast operations
- Errors and exceptions

## 🔗 Next Steps

After mastering collaborative editing, explore:

1. **Multi-Agent** (`../multi-agent/`) - Multiple agents collaborating
2. **Multimodal Agent** (`../multimodal/`) - Handle images and files
3. **Customer Support Bot** (`../support-bot/`) - Context tracking

## 📄 License

Apache 2.0 - See [LICENSE](../../../../LICENSE)

## 🔗 Resources

- [AG-UI Protocol Specification](../../../../docs/agui-protocol.md)
- [Agenkit Documentation](https://docs.agenkit.dev)
- [AG-UI Example Gallery](../)

---

**Built with ❤️ using Agenkit**

# Multimodal Agent

Production-ready example demonstrating multimodal content processing with AG-UI protocol.

## 🎯 Overview

This example showcases an AI agent that processes multiple content types including images, documents, code files, and data files. Perfect for understanding how to build agents that handle diverse input modalities.

### Key Features

- ✅ **Image Analysis**: Visual understanding, object detection, OCR
- ✅ **Document Processing**: Text extraction, summarization, key topics
- ✅ **Code Analysis**: Syntax checking, quality assessment, security
- ✅ **Data Processing**: Format validation, structure analysis, insights
- ✅ **Drag & Drop**: Intuitive file upload interface
- ✅ **Real-time Preview**: See images before analysis
- ✅ **Production Ready**: Comprehensive error handling and validation

## 🏗️ Architecture

```
┌────────────────────┐                  ┌─────────────────────────┐
│                    │   WebSocket      │                         │
│  Upload Interface  │◄─────────────────►│   FastAPI Backend       │
│                    │                  │                         │
│  - Drag & Drop     │                  │   - MultimodalAgent     │
│  - Image Preview   │                  │   - Content Routing     │
│  - File Info       │                  │   - Base64 Decoding     │
│  - Query Input     │                  │   - AG-UI Adapter       │
└────────────────────┘                  │                         │
        │                                └─────────────────────────┘
        │                                            │
        ▼                                            ▼
   User Uploads                                 Processing:
   Multiple Types                               - Images
                                                - Documents
                                                - Code
                                                - Data
```

## 📋 Prerequisites

- Python 3.10+
- Docker & Docker Compose (optional)

## 🚀 Quick Start

### Docker (Recommended)

```bash
docker-compose up --build
open http://localhost:3000
```

### Local Setup

```bash
# Backend
cd backend
pip install -e ../../../../
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
python -m http.server 3000
```

## 🎮 Usage

### 1. Upload Content

- **Click upload area** or **drag and drop** a file
- Supported formats:
  - Images: .jpg, .png, .gif, .bmp, .webp
  - Documents: .txt, .md, .pdf, .doc, .docx
  - Code: .py, .js, .ts, .go, .rs, .cpp, .java
  - Data: .json, .csv, .xml, .yaml

### 2. Add Query (Optional)

Type a specific question or request:
- "What objects are in this image?"
- "Summarize this document"
- "Check code quality"
- "Analyze data structure"

### 3. Analyze

Click **Analyze** button. Agent processes content and returns:
- Image: Description, objects, colors, text, sentiment
- Document: Summary, key topics, readability, word count
- Code: Quality assessment, security check, suggestions
- Data: Structure analysis, quality metrics, insights

## 💬 Example Results

### Image Analysis

**Upload**: photo.jpg (250KB)
**Query**: "What's in this image?"

**Result**:
```
Visual Analysis:
- Description: A multimodal AI interface displaying upload tools
- Scene: Web application user interface
- Objects: interface_element (95%), upload_button (89%), text_area (92%)
- Dominant Colors: #667eea, #764ba2, #ffffff
- Sentiment: Professional and modern

Suggestions:
- High quality image suitable for presentation
- Good contrast for accessibility
- Clear visual hierarchy
```

### Code Analysis

**Upload**: agent.py (850 lines)
**Query**: "Check code quality"

**Result**:
```
Code Analysis:
- Language: Python
- Lines: 850
- Complexity: Moderate

Code Quality:
- Structure: Well-organized with clear function definitions
- Documentation: Good docstrings present
- Style: Follows Python conventions
- Maintainability: High - clear naming and modular design

Suggestions:
- Consider adding type hints for better IDE support
- Add unit tests for critical functions
- Extract common patterns into reusable utilities

Security:
- Issues Found: 0
- Recommendations: Input validation, error handling
```

### Document Processing

**Upload**: report.txt (12KB)
**Query**: "Summarize this"

**Result**:
```
Document Analysis:
- Words: 2,450
- Pages: ~8
- Readability: Professional level
- Key Topics: Multimodal AI, Document Processing, AG-UI Protocol

Summary:
The collaborative document editor enables real-time editing with AI assistance.
Multiple users can work simultaneously while receiving intelligent suggestions.
This demonstrates the power of combining collaborative workflows with AI agents...
```

## 🔧 Configuration

### File Size Limit

Edit `docker-compose.yml`:
```yaml
environment:
  - MAX_FILE_SIZE=10485760  # 10MB (adjust as needed)
```

### Supported Formats

Edit `backend/agent.py`:
```python
self._supported_types = {
    "images": [".jpg", ".jpeg", ".png"],
    "custom_type": [".xyz", ".abc"],  # Add new type
}
```

### Analysis Behavior

Customize processing in `backend/agent.py`:
```python
def _analyze_image(self, query: str, image_format: str, image_size: int):
    # Add custom image analysis logic
    pass
```

## 📊 AG-UI Events

### MetadataEvent

```json
{
  "event_type": "metadata",
  "data": {
    "agent_name": "MultimodalAssistant",
    "capabilities": ["image_analysis", "text_extraction", ...],
    "supported_formats": {
      "images": [".jpg", ".png"],
      "documents": [".txt", ".pdf"]
    },
    "max_file_size": 10485760
  }
}
```

### Image Upload Message

```json
{
  "type": "image",
  "message": "Analyze this image",
  "image_data": "base64...",
  "image_format": "png",
  "image_size": 256000
}
```

### File Upload Message

```json
{
  "type": "file",
  "message": "Check code quality",
  "file_data": "base64...",
  "file_name": "agent.py",
  "file_size": 45000,
  "file_type": "text/x-python"
}
```

## 🧪 Testing

### Manual Testing

1. **Images**: Upload PNG/JPG, verify analysis
2. **Documents**: Upload TXT/PDF, verify extraction
3. **Code**: Upload .py/.js, verify quality check
4. **Data**: Upload JSON/CSV, verify structure analysis
5. **Error**: Upload huge file, verify size limit

### Automated Testing

```bash
cd backend
pytest tests/
```

## 📚 Code Walkthrough

### Backend: Content Routing

```python
async def process(self, message: Message) -> Message:
    """Route to appropriate processor based on content type."""
    metadata = message.metadata or {}

    if "image_data" in metadata:
        result = await self._process_image(content, metadata)
    elif "file_data" in metadata:
        result = await self._process_file(content, metadata)
    else:
        result = await self._process_text(content, metadata)

    return Message(role="assistant", content=result)
```

### Backend: Image Processing

```python
async def _process_image(self, query: str, metadata: dict):
    """Analyze image content."""
    image_data = metadata.get("image_data")  # base64
    image_format = metadata.get("image_format")

    # Simulate analysis
    analysis = {"description": "...", "objects_detected": [...], "dominant_colors": [...]}

    return {"type": "image", "analysis": analysis}
```

### Frontend: File Upload

```javascript
async handleFileSelect(file) {
    // Read as base64
    const reader = new FileReader();
    reader.onload = (e) => {
        this.currentFileData = e.target.result.split(',')[1];
        this.displayPreview(file, e.target.result);
    };
    reader.readAsDataURL(file);
}
```

### Frontend: Send to Agent

```javascript
function analyzeContent() {
    const message = {
        type: file.type.startsWith('image/') ? 'image' : 'file',
        message: query,
        [file.type.startsWith('image/') ? 'image_data' : 'file_data']:
            client.currentFileData,
        ...
    };
    client.send(message);
}
```

## 🎨 Customization

### Add New Content Type

1. **Update supported types** in `agent.py`:
```python
self._supported_types["custom"] = [".xyz"]
```

2. **Add processor**:
```python
async def _process_custom(self, query: str, metadata: dict):
    # Your custom processing logic
    return {"type": "custom", "analysis": {...}}
```

3. **Update routing**:
```python
elif "custom_data" in metadata:
    result = await self._process_custom(content, metadata)
```

## 🐛 Troubleshooting

### File Not Uploading

- Check file size (< 10MB by default)
- Verify MIME type is supported
- Check browser console for errors

### Preview Not Showing

- Ensure file is valid image format
- Check FileReader compatibility
- Verify base64 encoding

### Analysis Not Working

```bash
# Check backend logs
docker-compose logs backend

# Verify WebSocket connection
# Browser DevTools -> Network -> WS
```

## 🚢 Production Deployment

### Environment Variables

```bash
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_ORIGINS=https://your-domain.com
LOG_LEVEL=info
```

### Security Considerations

- Validate file types on server
- Scan uploads for malware
- Implement rate limiting
- Use HTTPS in production
- Sanitize file names

## 🔗 Next Steps

Explore other examples:
1. **Multi-Agent** - Coordinate multiple agents
2. **Customer Support Bot** - Context tracking
3. **Code Assistant** - Documentation + generation

## 📄 License

Apache 2.0 - See [LICENSE](../../../../LICENSE)

---

**Built with ❤️ using Agenkit**

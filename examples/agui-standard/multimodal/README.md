# AG-UI Standard Multimodal Support

> **🎨 Multimodal Content**: These examples demonstrate handling images, files, and audio in AG-UI Standard messages using content parts.

## Overview

AG-UI Standard supports rich multimodal content through structured content parts. Messages can contain:
- **Text**: Plain text content
- **Images**: URLs or base64-encoded images
- **Files**: Document attachments (PDFs, code, data)
- **Audio**: Voice messages and recordings

---

## Quick Start

```bash
# Run image & text example
python example_image_text.py

# Run file attachments example
python example_file_attachments.py

# Run audio example
python example_audio.py
```

---

## Core Concepts

### Content Parts

Each multimodal message contains a list of content parts. Each part has a `type` field:

| Type | Description | Use Case |
|------|-------------|----------|
| `text` | Plain text | Instructions, context |
| `image_url` | Image from URL | External images |
| `image_base64` | Base64 image | Embedded images |
| `file_url` | File from URL | External documents |
| `file_base64` | Base64 file | Embedded documents |
| `audio_url` | Audio from URL | External audio |
| `audio_base64` | Base64 audio | Voice messages |

### MultimodalContent Builder

Fluent API for constructing multimodal messages:

```python
from agenkit.protocols.agui import MultimodalContent
from agenkit import Message

# Build content
content = MultimodalContent()
content.add_text("Please analyze this:")
content.add_image("screenshot.png")
content.add_text("And review this document:")
content.add_file("report.pdf")

# Create message
message = Message(role="user", content=content.to_list())
```

### Helper Functions

Shorthand for creating content parts:

```python
from agenkit.protocols.agui import text, image_file, file, audio_file

# Text part
text_part = text("Hello, world!")

# Image part
image_part = image_file("photo.jpg")

# File part
file_part = file("document.pdf")

# Audio part
audio_part = audio_file("recording.wav")
```

---

## Examples

### 1. Image & Text (`example_image_text.py`)

**Demonstrates:**
- Combining text and images
- Image URLs vs base64 encoding
- Multiple images in one message
- Vision agent processing

**Key Features:**
- VisionAgent processes multimodal content
- Analyzes images alongside text
- Supports multiple image formats (PNG, JPEG, etc.)
- Auto MIME type detection

**Run:**
```bash
python example_image_text.py
```

**Expected Output:**
```
Demo 1: Image URL
============================================================
I received a multimodal message with 1 image(s):

Please analyze this image:
[Image from URL: https://example.com/photo.jpg]

Demo 2: Base64-Encoded Image
============================================================
I received a multimodal message with 1 image(s):

I created a blue square. What do you see?
[Image: image/png, 1234 chars base64]
```

**Code Pattern:**
```python
# Using MultimodalContent
content = MultimodalContent()
content.add_text("Analyze this:")
content.add_image_url("https://example.com/image.jpg")
content.add_image("local_photo.png")  # Base64-encoded

message = Message(role="user", content=content.to_list())
```

### 2. File Attachments (`example_file_attachments.py`)

**Demonstrates:**
- File URLs and base64 encoding
- Multiple file attachments
- File metadata (filename, MIME type)
- Document processing

**Key Features:**
- FileProcessorAgent handles documents
- Supports any file type (PDF, TXT, JSON, etc.)
- Auto MIME type detection
- File metadata preservation

**Run:**
```bash
python example_file_attachments.py
```

**Expected Output:**
```
Demo 1: File URL
============================================================
Received 1 file(s):

1. Q4_Report.pdf (application/pdf)
   URL: https://example.com/report.pdf...

Demo 2: Base64-Encoded File
============================================================
Received 1 file(s):

1. document.txt (text/plain)
   Size: 523 chars (base64)

Context: I'm attaching a document for review: Please summarize the contents.
```

**Code Pattern:**
```python
content = MultimodalContent()
content.add_text("Review these documents:")
content.add_file_url("https://example.com/doc.pdf", "report.pdf")
content.add_file("local_doc.txt")  # Base64-encoded

message = Message(role="user", content=content.to_list())
```

### 3. Audio (`example_audio.py`)

**Demonstrates:**
- Audio URLs and base64 encoding
- Audio metadata (duration, format)
- Transcription simulation
- Voice message handling

**Key Features:**
- AudioAgent processes voice messages
- Duration tracking
- Format support (WAV, MP3, AAC, etc.)
- Simulated transcription

**Run:**
```bash
python example_audio.py
```

**Expected Output:**
```
Demo 1: Audio URL
============================================================
🎵 Received 1 audio clip(s):

1. Audio from URL (duration: 45.5s)
   URL: https://example.com/voice_message.mp3...
   🎤 Transcription: [Simulated transcription of audio clip 1]

💬 Context: Please transcribe this recording:

Demo 2: Base64-Encoded Audio
============================================================
🎵 Received 1 audio clip(s):

1. Audio: audio/wav (duration: 2.0s)
   Size: 176444 chars (base64)
   🎤 Transcription: [Simulated transcription of audio clip 1]
```

**Code Pattern:**
```python
content = MultimodalContent()
content.add_text("Voice message:")
content.add_audio_url("https://example.com/audio.mp3", duration=30.5)
content.add_audio("recording.wav")  # Base64-encoded

message = Message(role="user", content=content.to_list())
```

---

## Content Part Specifications

### Text Content Part

```python
{"type": "text", "text": "Hello, world!"}
```

### Image URL Content Part

```python
{
    "type": "image_url",
    "image_url": {
        "url": "https://example.com/image.jpg",
        "detail": "auto",  # "auto", "low", or "high"
    },
}
```

### Image Base64 Content Part

```python
{
    "type": "image_base64",
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
    "mime_type": "image/png",
}
```

### File URL Content Part

```python
{
    "type": "file_url",
    "file_url": "https://example.com/document.pdf",
    "filename": "report.pdf",  # Optional
    "mime_type": "application/pdf",  # Optional
}
```

### File Base64 Content Part

```python
{
    "type": "file_base64",
    "file_base64": "JVBERi0xLjQKJeLjz9MKMy...",
    "filename": "document.pdf",
    "mime_type": "application/pdf",
}
```

### Audio URL Content Part

```python
{
    "type": "audio_url",
    "audio_url": "https://example.com/audio.mp3",
    "duration": 120.5,  # Seconds, optional
}
```

### Audio Base64 Content Part

```python
{
    "type": "audio_base64",
    "audio_base64": "UklGRiQAAABXQVZFZm10...",
    "mime_type": "audio/wav",
    "duration": 2.0,  # Seconds, optional
}
```

---

## Agent Processing Patterns

### Pattern 1: Type-Based Dispatch

```python
class MultimodalAgent(Agent):
    async def process(self, message: Message) -> Message:
        content = message.content

        # Handle plain text
        if isinstance(content, str):
            return self._process_text(content)

        # Handle multimodal
        if isinstance(content, list):
            for part in content:
                part_type = part.get("type")

                if part_type == "text":
                    text = part.get("text")
                elif part_type == "image_base64":
                    image_data = part.get("image_base64")
                    # Process image...
                elif part_type == "file_base64":
                    file_data = part.get("file_base64")
                    filename = part.get("filename")
                    # Process file...
```

### Pattern 2: Content Extraction

```python
def extract_content(message: Message) -> dict:
    """Extract different content types from multimodal message."""
    content = message.content

    if isinstance(content, str):
        return {"text": [content], "images": [], "files": [], "audio": []}

    result = {"text": [], "images": [], "files": [], "audio": []}

    if isinstance(content, list):
        for part in content:
            part_type = part.get("type")

            if part_type == "text":
                result["text"].append(part.get("text"))
            elif part_type in ["image_url", "image_base64"]:
                result["images"].append(part)
            elif part_type in ["file_url", "file_base64"]:
                result["files"].append(part)
            elif part_type in ["audio_url", "audio_base64"]:
                result["audio"].append(part)

    return result
```

### Pattern 3: Selective Processing

```python
class ImageOnlyAgent(Agent):
    async def process(self, message: Message) -> Message:
        # Extract only images
        images = []

        if isinstance(message.content, list):
            for part in message.content:
                if part.get("type") in ["image_url", "image_base64"]:
                    images.append(part)

        if not images:
            return Message(role="assistant", content="No images found!")

        # Process images...
        return Message(role="assistant", content=f"Processed {len(images)} images")
```

---

## Frontend Integration

### React Example

```jsx
import { useState } from 'react';

function MultimodalMessageInput() {
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    const reader = new FileReader();

    reader.onload = (event) => {
      const base64 = event.target.result.split(',')[1];
      setFiles([...files, {
        type: file.type.startsWith('image/') ? 'image_base64' : 'file_base64',
        [file.type.startsWith('image/') ? 'image_base64' : 'file_base64']: base64,
        mime_type: file.type,
        filename: file.name,
      }]);
    };

    reader.readAsDataURL(file);
  };

  const sendMessage = async () => {
    const content = [
      { type: 'text', text },
      ...files
    ];

    const response = await fetch('/agui', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: { role: 'user', content }
      })
    });

    // Handle response...
  };

  return (
    <div>
      <textarea value={text} onChange={(e) => setText(e.target.value)} />
      <input type="file" onChange={handleFileUpload} multiple />
      <button onClick={sendMessage}>Send</button>

      {/* Preview uploaded files */}
      {files.map((file, i) => (
        <div key={i}>
          {file.type === 'image_base64' && (
            <img src={`data:${file.mime_type};base64,${file.image_base64}`} />
          )}
          {file.type === 'file_base64' && <span>📄 {file.filename}</span>}
        </div>
      ))}
    </div>
  );
}
```

### Vue Example

```vue
<template>
  <div class="multimodal-input">
    <textarea v-model="text" placeholder="Type a message..." />
    <input type="file" @change="handleFileUpload" multiple />
    <button @click="sendMessage">Send</button>

    <div class="file-preview">
      <div v-for="(file, index) in files" :key="index">
        <img v-if="file.type === 'image_base64'"
             :src="`data:${file.mime_type};base64,${file.image_base64}`" />
        <span v-else>📄 {{ file.filename }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const text = ref('');
const files = ref([]);

const handleFileUpload = async (event) => {
  const fileList = Array.from(event.target.files);

  for (const file of fileList) {
    const base64 = await fileToBase64(file);
    const contentPart = {
      type: file.type.startsWith('image/') ? 'image_base64' : 'file_base64',
      [file.type.startsWith('image/') ? 'image_base64' : 'file_base64']: base64,
      mime_type: file.type,
      filename: file.name,
    };

    files.value.push(contentPart);
  }
};

const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

const sendMessage = async () => {
  const content = [
    { type: 'text', text: text.value },
    ...files.value
  ];

  const response = await fetch('/agui', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: { role: 'user', content }
    })
  });

  // Handle response...
};
</script>
```

---

## Performance Considerations

### Base64 Encoding

**Pros:**
- Self-contained messages
- No external dependencies
- Works offline

**Cons:**
- 33% larger than binary
- Slow for large files
- Memory overhead

**Guidelines:**
- Images: Use base64 for <500KB, URL for larger
- Files: Use base64 for <1MB, URL for larger
- Audio: Use base64 for <2MB, URL for larger

### MIME Type Detection

Auto-detected from file extension:
- `.png` → `image/png`
- `.jpg` → `image/jpeg`
- `.pdf` → `application/pdf`
- `.txt` → `text/plain`
- `.mp3` → `audio/mpeg`
- `.wav` → `audio/wav`

### File Size Limits

Current Message limit: 16MB total

**Recommendations:**
- Images: Max 5MB (base64)
- Files: Max 10MB (base64)
- Audio: Max 10MB (base64)

For larger files, use URLs or streaming.

---

## Best Practices

### 1. Choose Encoding Wisely

```python
# Good: URL for large files
content.add_image_url("https://cdn.example.com/large_image.jpg")

# Bad: Base64 for 10MB image
content.add_image("huge_image.jpg")  # Will be slow!
```

### 2. Provide Context

```python
# Good: Context around media
content.add_text("Screenshot from step 3:")
content.add_image("step3.png")
content.add_text("Notice the error in the console.")

# Bad: No context
content.add_image("step3.png")
```

### 3. Include Metadata

```python
# Good: Rich metadata
content.add_file_url(
    "https://example.com/report.pdf",
    filename="Q4_2025_Financial_Report.pdf",
    mime_type="application/pdf",
)

# Acceptable: Minimal metadata (auto-detected)
content.add_file("report.pdf")
```

### 4. Validate on Frontend

```javascript
// Check file size before encoding
if (file.size > 5 * 1024 * 1024) {  // 5MB
  alert("File too large. Please use a URL or smaller file.");
  return;
}

// Check MIME type
const allowedTypes = ['image/png', 'image/jpeg', 'application/pdf'];
if (!allowedTypes.includes(file.type)) {
  alert("Unsupported file type.");
  return;
}
```

---

## Troubleshooting

**Issue**: Base64 encoding fails
**Solution**: Check file exists and is readable

**Issue**: MIME type incorrect
**Solution**: Specify mime_type explicitly

**Issue**: Message too large
**Solution**: Use URLs instead of base64 for large files

**Issue**: Images not displaying
**Solution**: Verify base64 string is valid and includes correct MIME type

---

## Resources

### Libraries
- **Python**: `Pillow` for images, `wave` for audio
- **JavaScript**: `FileReader` API, `fast-base64` for encoding
- **MIME Types**: https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types

### Related Examples
- **State Management**: `examples/agui-standard/state-management/`
- **Tool Streaming**: `examples/agui-standard/tool-streaming/`
- **Custom Frontends**: `examples/integrations/custom-frontends/`

---

## Next Steps

1. **Run Examples**: Test with sample files
2. **Build Agent**: Create multimodal-aware agent
3. **Frontend Integration**: Add file upload UI
4. **Test Thoroughly**: Handle edge cases
5. **Optimize**: Use URLs for large files

---

**Built with ❤️ using Agenkit AG-UI Standard**

"""File attachment multimodal example.

This example demonstrates:
- Attaching files to messages (PDFs, documents, etc.)
- File URLs and base64-encoded files
- Multiple file attachments
- File metadata (filename, MIME type)
"""

import asyncio
from pathlib import Path

from agenkit import Agent, Message
from agenkit.protocols.agui import (
    AGUIAdapter,
    MultimodalContent,
    file,
    file_url,
    text,
)


class FileProcessorAgent(Agent):
    """Agent that processes messages with file attachments."""

    @property
    def name(self) -> str:
        return "FileProcessorAgent"

    async def process(self, message: Message) -> Message:
        """Process message with file attachments."""
        content = message.content

        # Handle plain text
        if isinstance(content, str):
            return Message(
                role="assistant",
                content="Send me files to analyze!",
            )

        # Handle multimodal content
        if isinstance(content, list):
            text_parts = []
            files = []

            for part in content:
                if isinstance(part, dict):
                    part_type = part.get("type")

                    if part_type == "text":
                        text_parts.append(part.get("text", ""))

                    elif part_type == "file_url":
                        url = part.get("file_url", "")
                        filename = part.get("filename", "unknown")
                        mime_type = part.get("mime_type", "application/octet-stream")
                        files.append(
                            {
                                "filename": filename,
                                "mime_type": mime_type,
                                "source": "url",
                                "url": url,
                            }
                        )

                    elif part_type == "file_base64":
                        filename = part.get("filename", "unknown")
                        mime_type = part.get("mime_type", "application/octet-stream")
                        data_len = len(part.get("file_base64", ""))
                        files.append(
                            {
                                "filename": filename,
                                "mime_type": mime_type,
                                "source": "base64",
                                "size": data_len,
                            }
                        )

            # Generate response
            response_parts = [f"Received {len(files)} file(s):"]
            for i, file_info in enumerate(files, 1):
                if file_info["source"] == "url":
                    response_parts.append(
                        f"\n{i}. {file_info['filename']} ({file_info['mime_type']})"
                    )
                    response_parts.append(f"   URL: {file_info['url'][:50]}...")
                else:
                    response_parts.append(
                        f"\n{i}. {file_info['filename']} ({file_info['mime_type']})"
                    )
                    response_parts.append(f"   Size: {file_info['size']} chars (base64)")

            if text_parts:
                response_parts.append(f"\n\nContext: {' '.join(text_parts)}")

            return Message(role="assistant", content="".join(response_parts))

        return Message(role="assistant", content="Received your message!")


async def demo_file_url():
    """Demonstrate file URLs."""
    print("Demo 1: File URL")
    print("=" * 60)

    content = MultimodalContent()
    content.add_text("Please review this document:")
    content.add_file_url(
        "https://example.com/report.pdf",
        filename="Q4_Report.pdf",
        mime_type="application/pdf",
    )

    agent = FileProcessorAgent()
    adapter = AGUIAdapter(agent)

    message = Message(role="user", content=content.to_list())

    async for event in adapter.stream_events(message, thread_id="demo-1"):
        if event.type == "text_message_content":
            print(event.delta, end="", flush=True)

    print("\n")


async def demo_file_base64():
    """Demonstrate base64-encoded files."""
    print("\nDemo 2: Base64-Encoded File")
    print("=" * 60)

    # Use the sample document
    sample_file = Path(__file__).parent / "sample_files" / "document.txt"

    # Create sample if doesn't exist
    if not sample_file.exists():
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        sample_file.write_text(
            "Sample Document\n\nThis is a test document for multimodal examples."
        )

    # Build multimodal content
    content = MultimodalContent()
    content.add_text("I'm attaching a document for review:")
    content.add_file(sample_file)
    content.add_text("Please summarize the contents.")

    agent = FileProcessorAgent()
    adapter = AGUIAdapter(agent)

    message = Message(role="user", content=content.to_list())

    async for event in adapter.stream_events(message, thread_id="demo-2"):
        if event.type == "text_message_content":
            print(event.delta, end="", flush=True)

    print("\n")


async def demo_multiple_files():
    """Demonstrate multiple file attachments."""
    print("\nDemo 3: Multiple Files")
    print("=" * 60)

    import tempfile

    # Create temporary files
    temp_files = []
    for i, content_text in enumerate(
        [
            "Technical specifications...",
            "Project timeline...",
            "Budget breakdown...",
        ],
        1,
    ):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=f".txt", delete=False, prefix=f"doc{i}_"
        ) as f:
            f.write(content_text)
            temp_files.append(Path(f.name))

    try:
        # Build multimodal content
        content = MultimodalContent()
        content.add_text("Project documentation package:")

        for temp_file in temp_files:
            content.add_file(temp_file)

        content.add_text("Please review all documents and provide feedback.")

        agent = FileProcessorAgent()
        adapter = AGUIAdapter(agent)

        message = Message(role="user", content=content.to_list())

        async for event in adapter.stream_events(message, thread_id="demo-3"):
            if event.type == "text_message_content":
                print(event.delta, end="", flush=True)

        print("\n")

    finally:
        for temp_file in temp_files:
            temp_file.unlink()


async def main():
    """Run all file attachment demos."""
    print("=" * 60)
    print("File Attachment Multimodal Example")
    print("=" * 60)
    print()

    await demo_file_url()
    await demo_file_base64()
    await demo_multiple_files()

    print("\nKey Concepts:")
    print("-" * 60)
    print("""
1. **File Types**:
   - file_url: Reference external files
   - file_base64: Embed files directly
   - Auto MIME type detection from extension

2. **File Metadata**:
   - filename: Original filename
   - mime_type: Content type (application/pdf, text/plain, etc.)
   - Size info for base64-encoded files

3. **Use Cases**:
   - Document upload and analysis
   - Code file sharing
   - Configuration file processing
   - Data file import

4. **Frontend Integration**:
   - Download buttons for files
   - Preview for text/PDF files
   - Icon based on MIME type
   - Progress bars for large files
""")


if __name__ == "__main__":
    asyncio.run(main())

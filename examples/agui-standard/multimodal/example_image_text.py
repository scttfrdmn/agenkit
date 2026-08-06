"""Image and text multimodal example.

This example demonstrates:
- Combining text and images in a single message
- Image URLs and base64-encoded images
- Multimodal message construction
- Agent processing of multimodal content
"""

import asyncio
import base64
from io import BytesIO

from PIL import Image

from agenkit import Agent, Message
from agenkit.protocols.agui import (
    AGUIAdapter,
    MultimodalContent,
    image_file,
    image_url,
    text,
)


def create_sample_image(path: str, color: tuple[int, int, int] = (255, 0, 0)):
    """Create a simple sample image for testing.

    Args:
        path: Path to save image
        color: RGB color tuple
    """
    # Create a 100x100 pixel image
    img = Image.new("RGB", (100, 100), color)
    img.save(path)


class VisionAgent(Agent):
    """Agent that processes multimodal messages with images."""

    @property
    def name(self) -> str:
        return "VisionAgent"

    async def process(self, message: Message) -> Message:
        """Process multimodal message."""
        content = message.content

        # Handle plain text
        if isinstance(content, str):
            return Message(
                role="assistant",
                content=f"I received text: {content[:50]}...",
            )

        # Handle multimodal content (list of parts)
        if isinstance(content, list):
            text_parts = []
            image_count = 0

            for part in content:
                if isinstance(part, dict):
                    part_type = part.get("type")

                    if part_type == "text":
                        text_parts.append(part.get("text", ""))

                    elif part_type == "image_url":
                        image_count += 1
                        url = part.get("image_url", {}).get("url", "")
                        text_parts.append(f"[Image from URL: {url[:50]}...]")

                    elif part_type == "image_base64":
                        image_count += 1
                        mime_type = part.get("mime_type", "image/png")
                        data_len = len(part.get("image_base64", ""))
                        text_parts.append(f"[Image: {mime_type}, {data_len} chars base64]")

            response = f"I received a multimodal message with {image_count} image(s):\n\n"
            response += "\n".join(text_parts)

            return Message(role="assistant", content=response)

        # Fallback
        return Message(role="assistant", content="I received your message!")


async def demo_image_url():
    """Demonstrate image URLs."""
    print("Demo 1: Image URL")
    print("=" * 60)

    content = MultimodalContent()
    content.add_text("Please analyze this image:")
    content.add_image_url("https://example.com/photo.jpg", detail="high")

    agent = VisionAgent()
    adapter = AGUIAdapter(agent)

    message = Message(role="user", content=content.to_list())

    async for event in adapter.stream_events(message, thread_id="demo-1"):
        if event.type == "text_message_content":
            print(event.delta, end="", flush=True)

    print("\n")


async def demo_image_base64():
    """Demonstrate base64-encoded images."""
    print("\nDemo 2: Base64-Encoded Image")
    print("=" * 60)

    # Create sample image
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        temp_path = f.name

    create_sample_image(temp_path, color=(0, 0, 255))  # Blue image

    try:
        # Build multimodal content
        content = MultimodalContent()
        content.add_text("I created a blue square. What do you see?")
        content.add_image(temp_path)

        agent = VisionAgent()
        adapter = AGUIAdapter(agent)

        message = Message(role="user", content=content.to_list())

        async for event in adapter.stream_events(message, thread_id="demo-2"):
            if event.type == "text_message_content":
                print(event.delta, end="", flush=True)

        print("\n")

    finally:
        import os

        os.unlink(temp_path)


async def demo_multiple_images():
    """Demonstrate multiple images in one message."""
    print("\nDemo 3: Multiple Images")
    print("=" * 60)

    import tempfile

    # Create two sample images
    temp_paths = []
    for color, name in [((255, 0, 0), "red"), ((0, 255, 0), "green")]:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
            temp_paths.append(temp_path)
            create_sample_image(temp_path, color=color)

    try:
        # Build multimodal content
        content = MultimodalContent()
        content.add_text("Compare these two images:")
        content.add_image(temp_paths[0])
        content.add_text("versus")
        content.add_image(temp_paths[1])
        content.add_text("What are the differences?")

        agent = VisionAgent()
        adapter = AGUIAdapter(agent)

        message = Message(role="user", content=content.to_list())

        async for event in adapter.stream_events(message, thread_id="demo-3"):
            if event.type == "text_message_content":
                print(event.delta, end="", flush=True)

        print("\n")

    finally:
        for path in temp_paths:
            import os

            os.unlink(path)


async def main():
    """Run all multimodal image demos."""
    print("=" * 60)
    print("Multimodal Image & Text Example")
    print("=" * 60)
    print()

    await demo_image_url()
    await demo_image_base64()
    await demo_multiple_images()

    print("\nKey Concepts:")
    print("-" * 60)
    print("""
1. **MultimodalContent Builder**:
   - Fluent API for constructing multimodal messages
   - Supports text, images, files, audio
   - Converts to list format for Message

2. **Image Types**:
   - image_url: Reference external images
   - image_base64: Embed images directly
   - Auto MIME type detection

3. **Content Processing**:
   - Agent receives list of content parts
   - Each part has 'type' field
   - Extract data based on type

4. **Frontend Integration**:
   - Render images inline
   - Show thumbnails for large images
   - Support zoom and download
""")


if __name__ == "__main__":
    asyncio.run(main())

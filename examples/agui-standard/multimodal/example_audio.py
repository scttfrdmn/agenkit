"""Audio multimodal example.

This example demonstrates:
- Audio URLs and base64-encoded audio
- Audio metadata (duration, format)
- Voice transcription simulation
- Audio message processing
"""

import asyncio
import wave
from pathlib import Path

from agenkit import Agent, Message
from agenkit.protocols.agui import (
    AGUIAdapter,
    MultimodalContent,
    audio_file,
    audio_url,
    text,
)


def create_sample_audio(path: str, duration: float = 1.0):
    """Create a simple sample audio file (silence).

    Args:
        path: Path to save audio file
        duration: Duration in seconds
    """
    import struct

    # Create a simple WAV file with silence
    sample_rate = 44100  # CD quality
    num_samples = int(sample_rate * duration)

    with wave.open(path, "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Write silence
        for _ in range(num_samples):
            wav_file.writeframes(struct.pack("<h", 0))


class AudioAgent(Agent):
    """Agent that processes audio messages."""

    @property
    def name(self) -> str:
        return "AudioAgent"

    async def process(self, message: Message) -> Message:
        """Process message with audio."""
        content = message.content

        # Handle plain text
        if isinstance(content, str):
            return Message(
                role="assistant",
                content="Send me audio to transcribe!",
            )

        # Handle multimodal content
        if isinstance(content, list):
            text_parts = []
            audio_parts = []

            for part in content:
                if isinstance(part, dict):
                    part_type = part.get("type")

                    if part_type == "text":
                        text_parts.append(part.get("text", ""))

                    elif part_type == "audio_url":
                        url = part.get("audio_url", "")
                        duration = part.get("duration")
                        audio_parts.append(
                            {
                                "source": "url",
                                "url": url,
                                "duration": duration,
                            }
                        )

                    elif part_type == "audio_base64":
                        mime_type = part.get("mime_type", "audio/wav")
                        duration = part.get("duration")
                        data_len = len(part.get("audio_base64", ""))
                        audio_parts.append(
                            {
                                "source": "base64",
                                "mime_type": mime_type,
                                "duration": duration,
                                "size": data_len,
                            }
                        )

            # Generate response
            response_parts = [f"🎵 Received {len(audio_parts)} audio clip(s):"]

            for i, audio in enumerate(audio_parts, 1):
                duration_str = f"{audio['duration']:.1f}s" if audio.get("duration") else "unknown"

                if audio["source"] == "url":
                    response_parts.append(f"\n{i}. Audio from URL (duration: {duration_str})")
                    response_parts.append(f"   URL: {audio['url'][:50]}...")
                    response_parts.append(
                        f"   🎤 Transcription: [Simulated transcription of audio clip {i}]"
                    )
                else:
                    response_parts.append(
                        f"\n{i}. Audio: {audio['mime_type']} (duration: {duration_str})"
                    )
                    response_parts.append(f"   Size: {audio['size']} chars (base64)")
                    response_parts.append(
                        f"   🎤 Transcription: [Simulated transcription of audio clip {i}]"
                    )

            if text_parts:
                response_parts.append(f"\n\n💬 Context: {' '.join(text_parts)}")

            return Message(role="assistant", content="".join(response_parts))

        return Message(role="assistant", content="Received your message!")


async def demo_audio_url():
    """Demonstrate audio URLs."""
    print("Demo 1: Audio URL")
    print("=" * 60)

    content = MultimodalContent()
    content.add_text("Please transcribe this recording:")
    content.add_audio_url("https://example.com/voice_message.mp3", duration=45.5)

    agent = AudioAgent()
    adapter = AGUIAdapter(agent)

    message = Message(role="user", content=content.to_list())

    async for event in adapter.stream_events(message, thread_id="demo-1"):
        if event.type == "text_message_content":
            print(event.delta, end="", flush=True)

    print("\n")


async def demo_audio_base64():
    """Demonstrate base64-encoded audio."""
    print("\nDemo 2: Base64-Encoded Audio")
    print("=" * 60)

    import tempfile

    # Create sample audio file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name

    create_sample_audio(temp_path, duration=2.0)

    try:
        # Build multimodal content
        content = MultimodalContent()
        content.add_text("Voice message:")
        content.add_audio(temp_path)

        agent = AudioAgent()
        adapter = AGUIAdapter(agent)

        message = Message(role="user", content=content.to_list())

        async for event in adapter.stream_events(message, thread_id="demo-2"):
            if event.type == "text_message_content":
                print(event.delta, end="", flush=True)

        print("\n")

    finally:
        import os

        os.unlink(temp_path)


async def demo_conversation_with_audio():
    """Demonstrate conversation with audio messages."""
    print("\nDemo 3: Audio Conversation")
    print("=" * 60)

    import tempfile

    # Create sample audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name

    create_sample_audio(temp_path, duration=3.5)

    try:
        # Build multimodal content
        content = MultimodalContent()
        content.add_text("Quick question:")
        content.add_audio(temp_path)
        content.add_text("Can you help with this?")

        agent = AudioAgent()
        adapter = AGUIAdapter(agent)

        message = Message(role="user", content=content.to_list())

        async for event in adapter.stream_events(message, thread_id="demo-3"):
            if event.type == "text_message_content":
                print(event.delta, end="", flush=True)

        print("\n")

    finally:
        import os

        os.unlink(temp_path)


async def main():
    """Run all audio demos."""
    print("=" * 60)
    print("Audio Multimodal Example")
    print("=" * 60)
    print()

    await demo_audio_url()
    await demo_audio_base64()
    await demo_conversation_with_audio()

    print("\nKey Concepts:")
    print("-" * 60)
    print("""
1. **Audio Types**:
   - audio_url: Reference external audio files
   - audio_base64: Embed audio directly
   - Support for WAV, MP3, AAC, etc.

2. **Audio Metadata**:
   - duration: Length in seconds
   - mime_type: audio/wav, audio/mpeg, audio/aac, etc.
   - Automatic format detection

3. **Use Cases**:
   - Voice messages
   - Audio transcription
   - Speech-to-text
   - Voice commands
   - Music analysis

4. **Frontend Integration**:
   - Audio player with controls
   - Waveform visualization
   - Playback speed control
   - Download button
   - Transcript display

5. **Integration with AI**:
   - Whisper API for transcription
   - Voice activity detection
   - Speaker diarization
   - Sentiment analysis from audio
""")


if __name__ == "__main__":
    asyncio.run(main())

"""AG-UI Multimodal Content Support.

This module provides types and utilities for working with multimodal content
(text, images, files, audio) in AG-UI Standard protocol messages.

The content field in AG-UI messages can contain:
- Plain text: str
- Content parts: list[ContentPart]
- Mixed: Any structure

Each content part has a type and data:
- text: Plain text content
- image_url: Image from URL
- image_base64: Base64-encoded image
- file_url: File from URL
- file_base64: Base64-encoded file
- audio_url: Audio from URL
- audio_base64: Base64-encoded audio
"""

from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field


# ============================================
# Content Part Types
# ============================================


class TextContentPart(BaseModel):
    """Plain text content part."""

    type: Literal["text"] = "text"
    text: str = Field(description="Text content")


class ImageURLContentPart(BaseModel):
    """Image from URL."""

    type: Literal["image_url"] = "image_url"
    image_url: dict[str, str] = Field(
        description="Image URL object with 'url' and optional 'detail'"
    )


class ImageBase64ContentPart(BaseModel):
    """Base64-encoded image."""

    type: Literal["image_base64"] = "image_base64"
    image_base64: str = Field(description="Base64-encoded image data")
    mime_type: str = Field(default="image/png", description="Image MIME type")


class FileURLContentPart(BaseModel):
    """File from URL."""

    type: Literal["file_url"] = "file_url"
    file_url: str = Field(description="File URL")
    filename: Optional[str] = Field(default=None, description="Original filename")
    mime_type: Optional[str] = Field(default=None, description="File MIME type")


class FileBase64ContentPart(BaseModel):
    """Base64-encoded file."""

    type: Literal["file_base64"] = "file_base64"
    file_base64: str = Field(description="Base64-encoded file data")
    filename: str = Field(description="Original filename")
    mime_type: str = Field(description="File MIME type")


class AudioURLContentPart(BaseModel):
    """Audio from URL."""

    type: Literal["audio_url"] = "audio_url"
    audio_url: str = Field(description="Audio URL")
    duration: Optional[float] = Field(default=None, description="Duration in seconds")


class AudioBase64ContentPart(BaseModel):
    """Base64-encoded audio."""

    type: Literal["audio_base64"] = "audio_base64"
    audio_base64: str = Field(description="Base64-encoded audio data")
    mime_type: str = Field(default="audio/wav", description="Audio MIME type")
    duration: Optional[float] = Field(default=None, description="Duration in seconds")


# Union of all content part types
ContentPart = Union[
    TextContentPart,
    ImageURLContentPart,
    ImageBase64ContentPart,
    FileURLContentPart,
    FileBase64ContentPart,
    AudioURLContentPart,
    AudioBase64ContentPart,
]


# ============================================
# Helper Functions
# ============================================


def text(content: str) -> TextContentPart:
    """Create a text content part.

    Args:
        content: Text content

    Returns:
        Text content part

    Example:
        >>> part = text("Hello, world!")
    """
    return TextContentPart(text=content)


def image_url(url: str, detail: str = "auto") -> ImageURLContentPart:
    """Create an image URL content part.

    Args:
        url: Image URL
        detail: Detail level ("auto", "low", "high")

    Returns:
        Image URL content part

    Example:
        >>> part = image_url("https://example.com/image.png")
    """
    return ImageURLContentPart(image_url={"url": url, "detail": detail})


def image_file(path: str | Path) -> ImageBase64ContentPart:
    """Create an image content part from a file.

    Args:
        path: Path to image file

    Returns:
        Image base64 content part

    Example:
        >>> part = image_file("photo.jpg")
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    # Read and encode image
    with open(file_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"  # Default

    return ImageBase64ContentPart(image_base64=image_data, mime_type=mime_type)


def file_url(
    url: str, filename: Optional[str] = None, mime_type: Optional[str] = None
) -> FileURLContentPart:
    """Create a file URL content part.

    Args:
        url: File URL
        filename: Optional filename
        mime_type: Optional MIME type

    Returns:
        File URL content part

    Example:
        >>> part = file_url("https://example.com/document.pdf", "doc.pdf")
    """
    return FileURLContentPart(file_url=url, filename=filename, mime_type=mime_type)


def file(path: str | Path) -> FileBase64ContentPart:
    """Create a file content part from a file.

    Args:
        path: Path to file

    Returns:
        File base64 content part

    Example:
        >>> part = file("document.pdf")
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Read and encode file
    with open(file_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("utf-8")

    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = "application/octet-stream"  # Default

    return FileBase64ContentPart(
        file_base64=file_data,
        filename=file_path.name,
        mime_type=mime_type,
    )


def audio_url(url: str, duration: Optional[float] = None) -> AudioURLContentPart:
    """Create an audio URL content part.

    Args:
        url: Audio URL
        duration: Optional duration in seconds

    Returns:
        Audio URL content part

    Example:
        >>> part = audio_url("https://example.com/audio.mp3", duration=120.5)
    """
    return AudioURLContentPart(audio_url=url, duration=duration)


def audio_file(path: str | Path) -> AudioBase64ContentPart:
    """Create an audio content part from a file.

    Args:
        path: Path to audio file

    Returns:
        Audio base64 content part

    Example:
        >>> part = audio_file("recording.wav")
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    # Read and encode audio
    with open(file_path, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")

    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type or not mime_type.startswith("audio/"):
        mime_type = "audio/wav"  # Default

    return AudioBase64ContentPart(audio_base64=audio_data, mime_type=mime_type)


# ============================================
# Content Builder
# ============================================


@dataclass
class MultimodalContent:
    """Builder for multimodal message content.

    Example:
        >>> content = MultimodalContent()
        >>> content.add_text("Here's an image:")
        >>> content.add_image("photo.jpg")
        >>> content.add_text("And a document:")
        >>> content.add_file("report.pdf")
        >>> message = Message(role="user", content=content.to_list())
    """

    parts: list[ContentPart] = None  # type: ignore

    def __post_init__(self):
        """Initialize parts list."""
        if self.parts is None:
            object.__setattr__(self, "parts", [])

    def add_text(self, text_content: str) -> "MultimodalContent":
        """Add text content.

        Args:
            text_content: Text to add

        Returns:
            Self for chaining
        """
        self.parts.append(text(text_content))
        return self

    def add_image_url(self, url: str, detail: str = "auto") -> "MultimodalContent":
        """Add image from URL.

        Args:
            url: Image URL
            detail: Detail level

        Returns:
            Self for chaining
        """
        self.parts.append(image_url(url, detail))
        return self

    def add_image(self, path: str | Path) -> "MultimodalContent":
        """Add image from file.

        Args:
            path: Path to image

        Returns:
            Self for chaining
        """
        self.parts.append(image_file(path))
        return self

    def add_file_url(
        self, url: str, filename: Optional[str] = None, mime_type: Optional[str] = None
    ) -> "MultimodalContent":
        """Add file from URL.

        Args:
            url: File URL
            filename: Optional filename
            mime_type: Optional MIME type

        Returns:
            Self for chaining
        """
        self.parts.append(file_url(url, filename, mime_type))
        return self

    def add_file(self, path: str | Path) -> "MultimodalContent":
        """Add file.

        Args:
            path: Path to file

        Returns:
            Self for chaining
        """
        self.parts.append(file(path))
        return self

    def add_audio_url(self, url: str, duration: Optional[float] = None) -> "MultimodalContent":
        """Add audio from URL.

        Args:
            url: Audio URL
            duration: Optional duration

        Returns:
            Self for chaining
        """
        self.parts.append(audio_url(url, duration))
        return self

    def add_audio(self, path: str | Path) -> "MultimodalContent":
        """Add audio from file.

        Args:
            path: Path to audio

        Returns:
            Self for chaining
        """
        self.parts.append(audio_file(path))
        return self

    def to_list(self) -> list[dict[str, Any]]:
        """Convert to list of content parts for Message.

        Returns:
            List of content part dictionaries
        """
        return [part.model_dump() for part in self.parts]

    def to_dict_list(self) -> list[dict[str, Any]]:
        """Alias for to_list().

        Returns:
            List of content part dictionaries
        """
        return self.to_list()


__all__ = [
    "TextContentPart",
    "ImageURLContentPart",
    "ImageBase64ContentPart",
    "FileURLContentPart",
    "FileBase64ContentPart",
    "AudioURLContentPart",
    "AudioBase64ContentPart",
    "ContentPart",
    "text",
    "image_url",
    "image_file",
    "file_url",
    "file",
    "audio_url",
    "audio_file",
    "MultimodalContent",
]

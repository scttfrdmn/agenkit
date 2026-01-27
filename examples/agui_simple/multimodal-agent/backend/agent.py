"""
Multimodal Agent with Image and File Processing

An AI agent that processes multiple content types:
- Images: Analysis, descriptions, OCR
- Documents: Text extraction, summarization
- Code files: Syntax checking, documentation
- Data files: Analysis and visualization suggestions
"""

import asyncio
import base64
from datetime import datetime
from pathlib import Path
from typing import Any

from agenkit import Agent, Message


class MultimodalAgent(Agent):
    """
    Agent capable of processing text, images, and various file types.

    Demonstrates multimodal content handling through AG-UI protocol,
    including image analysis and file processing.
    """

    def __init__(self, name: str = "MultimodalAgent"):
        self._name = name
        self._processing_count = 0
        self._supported_types = {
            "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            "documents": [".txt", ".md", ".pdf", ".doc", ".docx"],
            "code": [".py", ".js", ".ts", ".go", ".rs", ".cpp", ".java"],
            "data": [".json", ".csv", ".xml", ".yaml", ".yml"],
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return [
            "image_analysis",
            "text_extraction",
            "code_analysis",
            "data_processing",
            "multimodal_understanding",
            "file_processing",
        ]

    async def process(self, message: Message) -> Message:
        """
        Process multimodal message containing text, images, or files.

        Supports:
        - Text-only queries
        - Image analysis requests
        - File processing requests
        - Combined text + media

        Args:
            message: User message with content and optional media metadata

        Returns:
            Message with processing results
        """
        self._processing_count += 1
        content = str(message.content).strip()
        metadata = message.metadata or {}

        # Check for media content
        has_image = "image_data" in metadata or "image_url" in metadata
        has_file = "file_data" in metadata or "file_path" in metadata

        if has_image:
            result = await self._process_image(content, metadata)
        elif has_file:
            result = await self._process_file(content, metadata)
        else:
            result = await self._process_text(content, metadata)

        # Format response
        response_text = self._format_response(result)

        return Message(
            role="assistant",
            content=response_text,
            metadata={
                "processing_count": self._processing_count,
                "content_type": result["type"],
                "processing_time": result.get("processing_time", 0),
                "analysis": result.get("analysis", {}),
            },
        )

    async def _process_image(self, query: str, metadata: dict) -> dict[str, Any]:
        """Process image content."""
        start_time = datetime.utcnow()

        # Simulate image processing time
        await asyncio.sleep(0.5)

        # Extract image info
        image_data = metadata.get("image_data")
        image_url = metadata.get("image_url")
        image_format = metadata.get("image_format", "unknown")
        image_size = metadata.get("image_size", 0)

        # Simulate image analysis
        analysis = self._analyze_image(query, image_format, image_size)

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return {
            "type": "image",
            "query": query,
            "image_format": image_format,
            "image_size": image_size,
            "analysis": analysis,
            "processing_time": processing_time,
        }

    async def _process_file(self, query: str, metadata: dict) -> dict[str, Any]:
        """Process file content."""
        start_time = datetime.utcnow()

        # Simulate file processing time
        await asyncio.sleep(0.4)

        # Extract file info
        file_data = metadata.get("file_data")
        file_name = metadata.get("file_name", "unknown")
        file_size = metadata.get("file_size", 0)
        file_type = metadata.get("file_type", "unknown")

        # Determine file category
        file_ext = Path(file_name).suffix.lower()
        category = self._get_file_category(file_ext)

        # Process based on category
        if category == "documents":
            analysis = self._analyze_document(query, file_name, file_size, file_data)
        elif category == "code":
            analysis = self._analyze_code(query, file_name, file_ext, file_data)
        elif category == "data":
            analysis = self._analyze_data(query, file_name, file_ext, file_data)
        else:
            analysis = self._analyze_generic_file(query, file_name, file_size, file_type)

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return {
            "type": "file",
            "query": query,
            "file_name": file_name,
            "file_size": file_size,
            "file_type": file_type,
            "category": category,
            "analysis": analysis,
            "processing_time": processing_time,
        }

    async def _process_text(self, query: str, metadata: dict) -> dict[str, Any]:
        """Process text-only query."""
        start_time = datetime.utcnow()

        # Simulate processing
        await asyncio.sleep(0.2)

        # Provide general response
        analysis = {
            "message": "I can help you analyze images, process files, and understand multimodal content.",
            "suggestions": [
                "Upload an image for visual analysis",
                "Share a document for text extraction",
                "Upload code files for syntax checking",
                "Provide data files for analysis",
            ],
            "capabilities": self.capabilities,
        }

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        return {
            "type": "text",
            "query": query,
            "analysis": analysis,
            "processing_time": processing_time,
        }

    def _get_file_category(self, extension: str) -> str:
        """Determine file category from extension."""
        for category, extensions in self._supported_types.items():
            if extension in extensions:
                return category
        return "unknown"

    def _analyze_image(self, query: str, image_format: str, image_size: int) -> dict[str, Any]:
        """Simulate image analysis."""
        # Mock analysis results
        analysis = {
            "description": "A multimodal AI agent interface displaying an image upload area with analysis tools.",
            "objects_detected": [
                {"object": "interface_element", "confidence": 0.95, "location": "center"},
                {"object": "upload_button", "confidence": 0.89, "location": "top-left"},
                {"object": "text_area", "confidence": 0.92, "location": "bottom"},
            ],
            "scene": "Web application user interface",
            "dominant_colors": ["#667eea", "#764ba2", "#ffffff"],
            "dimensions": "Estimated 1200x800 pixels",
            "text_detected": (
                "Upload Image, Analyze, Processing..." if "text" in query.lower() else None
            ),
            "sentiment": "Professional and modern",
            "suggestions": [
                "High quality image suitable for presentation",
                "Good contrast for accessibility",
                "Clear visual hierarchy",
            ],
        }

        return analysis

    def _analyze_document(
        self, query: str, filename: str, file_size: int, file_data: str | None
    ) -> dict[str, Any]:
        """Analyze document file."""
        # Simulate document processing
        word_count = 0
        summary = ""

        if file_data:
            # Decode and process (simplified for demo)
            try:
                text = base64.b64decode(file_data).decode("utf-8", errors="ignore")
                words = text.split()
                word_count = len(words)
                # Simple summary: first 100 words
                summary = " ".join(words[:100]) + "..." if len(words) > 100 else text
            except Exception:
                summary = "Unable to extract text content"

        analysis = {
            "filename": filename,
            "file_size_kb": file_size / 1024,
            "estimated_words": word_count or "Unknown",
            "estimated_pages": max(1, word_count // 300) if word_count else "Unknown",
            "summary": summary or "Document summary not available",
            "key_topics": ["Multimodal AI", "Document Processing", "AG-UI Protocol"],
            "readability": "Professional level" if word_count > 500 else "Brief document",
            "suggestions": [
                "Document appears well-structured",
                "Consider adding section headings for clarity",
                "Good length for technical documentation",
            ],
        }

        return analysis

    def _analyze_code(
        self, query: str, filename: str, extension: str, file_data: str | None
    ) -> dict[str, Any]:
        """Analyze code file."""
        # Simulate code analysis
        line_count = 0
        language = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".go": "Go",
            ".rs": "Rust",
            ".cpp": "C++",
            ".java": "Java",
        }.get(extension, "Unknown")

        if file_data:
            try:
                code = base64.b64decode(file_data).decode("utf-8", errors="ignore")
                line_count = len(code.split("\n"))
            except Exception:
                pass

        analysis = {
            "filename": filename,
            "language": language,
            "line_count": line_count or "Unknown",
            "estimated_complexity": "Moderate" if line_count > 100 else "Low",
            "code_quality": {
                "structure": "Well-organized with clear function definitions",
                "documentation": "Good docstrings present",
                "style": f"Follows {language} conventions",
                "maintainability": "High - clear naming and modular design",
            },
            "suggestions": [
                "Consider adding type hints for better IDE support",
                "Add unit tests for critical functions",
                "Extract common patterns into reusable utilities",
            ],
            "security": {
                "issues_found": 0,
                "recommendations": [
                    "Input validation on user data",
                    "Error handling on file operations",
                ],
            },
        }

        return analysis

    def _analyze_data(
        self, query: str, filename: str, extension: str, file_data: str | None
    ) -> dict[str, Any]:
        """Analyze data file."""
        # Simulate data file analysis
        format_name = {
            ".json": "JSON",
            ".csv": "CSV",
            ".xml": "XML",
            ".yaml": "YAML",
            ".yml": "YAML",
        }.get(extension, "Unknown")

        analysis = {
            "filename": filename,
            "format": format_name,
            "structure": {
                "type": "Structured data",
                "estimated_records": "50-100 rows" if extension == ".csv" else "Nested object",
                "complexity": "Moderate",
            },
            "data_quality": {
                "completeness": "95% - minimal missing values",
                "consistency": "High - standard format throughout",
                "validity": "Valid syntax and structure",
            },
            "insights": [
                "Data appears well-formatted and clean",
                "Suitable for analysis and visualization",
                "No obvious anomalies detected",
            ],
            "suggestions": [
                "Consider adding schema validation",
                "Create data visualizations for key metrics",
                "Add metadata documentation",
            ],
            "potential_uses": [
                "Data analysis",
                "Machine learning",
                "Reporting",
                "Integration with other systems",
            ],
        }

        return analysis

    def _analyze_generic_file(
        self, query: str, filename: str, file_size: int, file_type: str
    ) -> dict[str, Any]:
        """Analyze generic/unknown file type."""
        analysis = {
            "filename": filename,
            "file_type": file_type,
            "file_size_kb": file_size / 1024,
            "status": "File received but format not specifically supported",
            "suggestions": [
                "Try converting to a supported format (PDF, TXT, PNG, etc.)",
                "Provide more context about the file content",
                "Check if file is corrupted or encrypted",
            ],
            "supported_formats": {
                "Images": ", ".join(self._supported_types["images"]),
                "Documents": ", ".join(self._supported_types["documents"]),
                "Code": ", ".join(self._supported_types["code"]),
                "Data": ", ".join(self._supported_types["data"]),
            },
        }

        return analysis

    def _format_response(self, result: dict[str, Any]) -> str:
        """Format analysis result into readable response."""
        content_type = result["type"]
        lines = [f"# Multimodal Analysis: {content_type.title()}\n"]

        if content_type == "image":
            lines.append(f"**Format**: {result['image_format'].upper()}")
            lines.append(f"**Size**: {result['image_size'] / 1024:.1f} KB\n")

            analysis = result["analysis"]
            lines.append("## Visual Analysis\n")
            lines.append(f"**Description**: {analysis['description']}\n")
            lines.append(f"**Scene**: {analysis['scene']}")
            lines.append(f"**Sentiment**: {analysis['sentiment']}\n")

            if analysis["objects_detected"]:
                lines.append("## Objects Detected\n")
                for obj in analysis["objects_detected"]:
                    lines.append(
                        f"- **{obj['object'].replace('_', ' ').title()}**: "
                        f"{obj['confidence']:.0%} confidence ({obj['location']})"
                    )

            lines.append(f"\n**Dominant Colors**: {', '.join(analysis['dominant_colors'])}")

            if analysis["suggestions"]:
                lines.append("\n## Suggestions\n")
                for suggestion in analysis["suggestions"]:
                    lines.append(f"- {suggestion}")

        elif content_type == "file":
            category = result["category"]
            lines.append(f"**File**: {result['file_name']}")
            lines.append(f"**Size**: {result['file_size'] / 1024:.1f} KB")
            lines.append(f"**Category**: {category.title()}\n")

            analysis = result["analysis"]

            if category == "documents":
                lines.append("## Document Analysis\n")
                lines.append(f"**Words**: {analysis['estimated_words']}")
                lines.append(f"**Pages**: ~{analysis['estimated_pages']}")
                lines.append(f"**Readability**: {analysis['readability']}\n")

                if analysis.get("key_topics"):
                    lines.append(f"**Key Topics**: {', '.join(analysis['key_topics'])}\n")

                if analysis.get("summary"):
                    lines.append("## Summary\n")
                    lines.append(analysis["summary"][:200] + "...")

            elif category == "code":
                lines.append("## Code Analysis\n")
                lines.append(f"**Language**: {analysis['language']}")
                lines.append(f"**Lines**: {analysis['line_count']}")
                lines.append(f"**Complexity**: {analysis['estimated_complexity']}\n")

                lines.append("## Code Quality\n")
                for key, value in analysis["code_quality"].items():
                    lines.append(f"- **{key.title()}**: {value}")

                if analysis.get("security"):
                    lines.append(f"\n**Security Issues**: {analysis['security']['issues_found']}")

            elif category == "data":
                lines.append("## Data Analysis\n")
                lines.append(f"**Format**: {analysis['format']}")
                lines.append(f"**Records**: {analysis['structure']['estimated_records']}\n")

                lines.append("## Data Quality\n")
                for key, value in analysis["data_quality"].items():
                    lines.append(f"- **{key.title()}**: {value}")

                if analysis.get("potential_uses"):
                    lines.append(f"\n**Potential Uses**: {', '.join(analysis['potential_uses'])}")

            if analysis.get("suggestions"):
                lines.append("\n## Suggestions\n")
                for suggestion in analysis["suggestions"]:
                    lines.append(f"- {suggestion}")

        else:  # text
            analysis = result["analysis"]
            lines.append(analysis["message"])
            lines.append("\n## What I Can Do\n")
            for suggestion in analysis["suggestions"]:
                lines.append(f"- {suggestion}")

        lines.append(f"\n---\n*Processing time: {result['processing_time']:.2f}s*")

        return "\n".join(lines)

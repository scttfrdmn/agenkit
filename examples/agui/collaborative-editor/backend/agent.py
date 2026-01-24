"""
Collaborative Document Editor Agent

An AI agent that assists with collaborative document editing through:
- Writing suggestions and improvements
- Grammar and style checking
- Content expansion
- Summarization
- Real-time feedback on edits
"""

import asyncio
import re
from datetime import datetime
from typing import Any

from agenkit import Agent, Message


class DocumentEditorAgent(Agent):
    """
    AI writing assistant for collaborative document editing.

    Provides intelligent suggestions, grammar fixes, style improvements,
    and content generation while preserving document state.
    """

    def __init__(self, name: str = "EditorAgent"):
        self._name = name
        self._assistance_count = 0
        self._document_versions = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return [
            "writing_assistance",
            "grammar_checking",
            "style_improvement",
            "content_expansion",
            "summarization",
            "collaborative_editing",
        ]

    async def process(self, message: Message) -> Message:
        """
        Process user request for writing assistance.

        Supports commands:
        - "suggest improvements": Grammar and style suggestions
        - "expand": Add more detail to content
        - "summarize": Create summary
        - "check grammar": Grammar check only
        - "improve style": Style suggestions
        - "complete": Auto-complete partial sentences

        Args:
            message: User message with command and document content

        Returns:
            Message with suggestions and improvements
        """
        self._assistance_count += 1
        content = str(message.content).lower().strip()
        metadata = message.metadata or {}

        # Extract document content and cursor position
        document_content = metadata.get("document_content", "")
        cursor_position = metadata.get("cursor_position", 0)
        selection = metadata.get("selection", "")
        command = self._parse_command(content)

        # Perform requested assistance
        result = await self._perform_assistance(
            command, document_content, selection, cursor_position
        )

        # Store document version
        self._document_versions.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "content": document_content,
                "command": command,
                "result": result,
            }
        )

        # Format response
        response_text = self._format_response(command, result)

        return Message(
            role="assistant",
            content=response_text,
            metadata={
                "assistance_count": self._assistance_count,
                "command": command,
                "suggestions": result.get("suggestions", []),
                "improved_content": result.get("improved_content"),
                "grammar_issues": result.get("grammar_issues", []),
                "style_recommendations": result.get("style_recommendations", []),
                "processing_time": result.get("processing_time", 0),
            },
        )

    def _parse_command(self, content: str) -> str:
        """Parse user command from message content."""
        if any(word in content for word in ["suggest", "improve", "better"]):
            return "suggest_improvements"
        elif "expand" in content or "elaborate" in content or "more detail" in content:
            return "expand"
        elif "summarize" in content or "summary" in content:
            return "summarize"
        elif "grammar" in content:
            return "check_grammar"
        elif "style" in content:
            return "improve_style"
        elif "complete" in content or "finish" in content:
            return "auto_complete"
        else:
            return "general_assistance"

    async def _perform_assistance(
        self, command: str, document: str, selection: str, cursor: int
    ) -> dict[str, Any]:
        """Perform the requested writing assistance."""
        start_time = datetime.utcnow()

        # Simulate AI processing time
        await asyncio.sleep(0.3)

        result: dict[str, Any] = {}

        if command == "suggest_improvements":
            result = self._suggest_improvements(document, selection)

        elif command == "expand":
            result = self._expand_content(selection or document)

        elif command == "summarize":
            result = self._summarize(document)

        elif command == "check_grammar":
            result = self._check_grammar(document, selection)

        elif command == "improve_style":
            result = self._improve_style(document, selection)

        elif command == "auto_complete":
            result = self._auto_complete(document, cursor)

        else:
            result = self._general_assistance(document, selection)

        processing_time = (datetime.utcnow() - start_time).total_seconds()
        result["processing_time"] = processing_time

        return result

    def _suggest_improvements(self, document: str, selection: str) -> dict[str, Any]:
        """Suggest grammar and style improvements."""
        target = selection if selection else document
        suggestions = []

        # Grammar checks
        if "their" in target.lower() and ("is" in target.lower() or "was" in target.lower()):
            suggestions.append(
                {
                    "type": "grammar",
                    "severity": "error",
                    "message": "Subject-verb agreement: 'their' is plural, use 'are' or 'were'",
                    "suggestion": target.replace(" is ", " are ").replace(" was ", " were "),
                }
            )

        # Passive voice detection
        passive_patterns = [
            r"\b(is|are|was|were|been|be)\s+\w+ed\b",
            r"\b(is|are|was|were)\s+being\s+\w+ed\b",
        ]
        for pattern in passive_patterns:
            if re.search(pattern, target, re.IGNORECASE):
                suggestions.append(
                    {
                        "type": "style",
                        "severity": "warning",
                        "message": "Consider using active voice for clarity",
                        "suggestion": "Rewrite in active voice: [agent suggests active form]",
                    }
                )
                break

        # Wordiness detection
        wordy_phrases = {
            "in order to": "to",
            "due to the fact that": "because",
            "at this point in time": "now",
            "for the purpose of": "for",
        }

        for wordy, concise in wordy_phrases.items():
            if wordy in target.lower():
                suggestions.append(
                    {
                        "type": "style",
                        "severity": "info",
                        "message": f"Consider replacing '{wordy}' with '{concise}'",
                        "suggestion": target.replace(wordy, concise),
                    }
                )

        return {
            "suggestions": suggestions,
            "improved_content": (
                self._apply_suggestions(target, suggestions) if suggestions else target
            ),
            "total_issues": len(suggestions),
        }

    def _expand_content(self, content: str) -> dict[str, Any]:
        """Expand content with additional details."""
        # Simulate content expansion
        if len(content) < 50:
            expanded = f"{content}\n\nThis concept is particularly important because it demonstrates how modern AI systems can assist with writing tasks. The implications extend beyond simple editing to encompass collaborative workflows and real-time feedback mechanisms."
        else:
            # Add transitional content
            sentences = content.split(". ")
            if len(sentences) > 1:
                expanded = ". ".join(sentences[:-1]) + ". "
                expanded += "Furthermore, it's worth noting that this approach enables teams to work together seamlessly. "
                expanded += sentences[-1]
            else:
                expanded = (
                    content
                    + "\n\nExpanding on this idea, we can explore several key aspects that enhance understanding and provide practical value."
                )

        return {
            "improved_content": expanded,
            "original_length": len(content),
            "expanded_length": len(expanded),
            "expansion_ratio": len(expanded) / max(len(content), 1),
        }

    def _summarize(self, document: str) -> dict[str, Any]:
        """Create a summary of the document."""
        # Extract key sentences (simple extractive summarization)
        sentences = [s.strip() for s in document.split(".") if len(s.strip()) > 20]

        if len(sentences) == 0:
            summary = "Document is too short to summarize."
        elif len(sentences) <= 3:
            summary = document
        else:
            # Take first sentence, middle sentence, and last sentence
            key_sentences = [
                sentences[0],
                sentences[len(sentences) // 2],
                sentences[-1],
            ]
            summary = ". ".join(key_sentences) + "."

        return {
            "improved_content": summary,
            "original_length": len(document),
            "summary_length": len(summary),
            "compression_ratio": len(summary) / max(len(document), 1),
            "sentences_extracted": len(summary.split(".")),
        }

    def _check_grammar(self, document: str, selection: str) -> dict[str, Any]:
        """Check grammar in document or selection."""
        target = selection if selection else document
        issues = []

        # Basic grammar checks
        # Double spaces
        if "  " in target:
            issues.append(
                {
                    "type": "spacing",
                    "severity": "warning",
                    "message": "Multiple consecutive spaces detected",
                    "location": target.find("  "),
                }
            )

        # Sentence capitalization
        sentences = target.split(". ")
        for i, sentence in enumerate(sentences):
            if sentence and not sentence[0].isupper():
                issues.append(
                    {
                        "type": "capitalization",
                        "severity": "error",
                        "message": "Sentence should start with capital letter",
                        "location": sum(len(s) + 2 for s in sentences[:i]),
                    }
                )

        # Common mistakes
        common_errors = {
            "alot": "a lot",
            "occured": "occurred",
            "recieve": "receive",
            "definately": "definitely",
        }

        for error, correction in common_errors.items():
            if error in target.lower():
                issues.append(
                    {
                        "type": "spelling",
                        "severity": "error",
                        "message": f"'{error}' should be '{correction}'",
                        "suggestion": target.replace(error, correction),
                    }
                )

        return {
            "grammar_issues": issues,
            "total_issues": len(issues),
            "has_errors": len(issues) > 0,
        }

    def _improve_style(self, document: str, selection: str) -> dict[str, Any]:
        """Provide style improvement suggestions."""
        target = selection if selection else document
        recommendations = []

        # Check sentence length
        sentences = [s.strip() for s in target.split(".") if s.strip()]
        avg_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

        if avg_length > 25:
            recommendations.append(
                {
                    "type": "readability",
                    "severity": "info",
                    "message": "Average sentence length is high (>25 words). Consider breaking into shorter sentences.",
                }
            )

        # Check paragraph length
        paragraphs = [p.strip() for p in target.split("\n\n") if p.strip()]
        if paragraphs and max(len(p.split()) for p in paragraphs) > 150:
            recommendations.append(
                {
                    "type": "structure",
                    "severity": "info",
                    "message": "Long paragraph detected (>150 words). Consider breaking into multiple paragraphs.",
                }
            )

        # Check repetition
        words = target.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 5:  # Only check longer words
                word_freq[word] = word_freq.get(word, 0) + 1

        repeated_words = [(w, c) for w, c in word_freq.items() if c > 3]
        if repeated_words:
            recommendations.append(
                {
                    "type": "vocabulary",
                    "severity": "info",
                    "message": f"Repeated words detected: {', '.join(w for w, _ in repeated_words[:3])}",
                }
            )

        return {
            "style_recommendations": recommendations,
            "total_recommendations": len(recommendations),
        }

    def _auto_complete(self, document: str, cursor: int) -> dict[str, Any]:
        """Auto-complete sentence at cursor position."""
        # Get text before cursor
        text_before = document[:cursor]

        # Check if in middle of sentence
        if not text_before.endswith((".", "!", "?")):
            # Find last sentence start
            last_sentence_start = max(
                text_before.rfind(". "),
                text_before.rfind("! "),
                text_before.rfind("? "),
                0,
            )

            partial_sentence = text_before[last_sentence_start:].strip()

            # Generate completion
            completions = [
                " and demonstrates the power of collaborative editing.",
                " while maintaining consistency across multiple users.",
                " through real-time synchronization and conflict resolution.",
                " with AI-powered suggestions and improvements.",
            ]

            # Simple context-based selection
            if "ai" in partial_sentence.lower() or "agent" in partial_sentence.lower():
                completion = completions[3]
            elif "real" in partial_sentence.lower() or "time" in partial_sentence.lower():
                completion = completions[2]
            elif "user" in partial_sentence.lower() or "multiple" in partial_sentence.lower():
                completion = completions[1]
            else:
                completion = completions[0]

            completed = text_before + completion + document[cursor:]

            return {"improved_content": completed, "completion": completion, "inserted_at": cursor}

        return {
            "improved_content": document,
            "completion": None,
            "message": "Already at sentence end",
        }

    def _general_assistance(self, document: str, selection: str) -> dict[str, Any]:
        """Provide general writing assistance."""
        target = selection if selection else document

        suggestions = []
        suggestions.append(
            {
                "type": "general",
                "message": "Document is being analyzed for improvements.",
            }
        )

        if len(target) < 50:
            suggestions.append(
                {
                    "type": "content",
                    "message": "Consider adding more detail to strengthen your writing.",
                }
            )

        if len(target) > 500:
            suggestions.append(
                {
                    "type": "structure",
                    "message": "For longer documents, ensure clear section headings and transitions.",
                }
            )

        return {"suggestions": suggestions, "analysis_complete": True}

    def _apply_suggestions(self, content: str, suggestions: list[dict[str, Any]]) -> str:
        """Apply suggestions to content."""
        improved = content

        for suggestion in suggestions:
            if "suggestion" in suggestion and isinstance(suggestion["suggestion"], str):
                # Simple replacement for demo purposes
                improved = suggestion["suggestion"]
                break

        return improved

    def _format_response(self, command: str, result: dict[str, Any]) -> str:
        """Format assistance result into readable response."""
        lines = [f"# Writing Assistance: {command.replace('_', ' ').title()}\n"]

        if command == "suggest_improvements":
            lines.append(f"**Found {result['total_issues']} potential improvements**\n")
            if result["suggestions"]:
                lines.append("## Suggestions:\n")
                for i, suggestion in enumerate(result["suggestions"][:5], 1):
                    severity_emoji = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(
                        suggestion["severity"], "•"
                    )
                    lines.append(
                        f"{i}. {severity_emoji} **{suggestion['type'].title()}**: {suggestion['message']}"
                    )

        elif command == "expand":
            lines.append(
                f"**Expanded content from {result['original_length']} to "
                f"{result['expanded_length']} characters** "
                f"({result['expansion_ratio']:.1f}x)\n"
            )
            lines.append("## Expanded Content:\n")
            lines.append(result["improved_content"])

        elif command == "summarize":
            lines.append(
                f"**Summary created** ({result['summary_length']} chars, "
                f"{result['compression_ratio']:.0%} of original)\n"
            )
            lines.append("## Summary:\n")
            lines.append(result["improved_content"])

        elif command == "check_grammar":
            lines.append(f"**Grammar check found {result['total_issues']} issues**\n")
            if result["grammar_issues"]:
                lines.append("## Issues:\n")
                for issue in result["grammar_issues"][:5]:
                    lines.append(f"• **{issue['type'].title()}**: {issue['message']}")

        elif command == "improve_style":
            lines.append(f"**Style analysis: {result['total_recommendations']} recommendations**\n")
            if result["style_recommendations"]:
                lines.append("## Recommendations:\n")
                for rec in result["style_recommendations"]:
                    lines.append(f"• {rec['message']}")

        elif command == "auto_complete":
            if result.get("completion"):
                lines.append("**Sentence completed**\n")
                lines.append(f"Added: `{result['completion']}`")
            else:
                lines.append(result.get("message", "No completion available"))

        lines.append(f"\n---\n*Processing time: {result.get('processing_time', 0):.2f}s*")

        return "\n".join(lines)

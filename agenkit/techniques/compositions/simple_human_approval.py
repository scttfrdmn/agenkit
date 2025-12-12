"""
Simple Human Approval Composition

A minimal composition that demonstrates basic human-in-the-loop approval.
This is intentionally simple to show the difference between a quick prototype
composition and a full production pattern.

For production use cases, use the HumanInLoopAgent pattern instead, which provides:
- Confidence thresholds
- Timeout handling
- Retry logic
- Audit trails
- Async approval mechanisms

This composition is perfect for:
- Quick prototypes
- Learning exercises
- Simple scripts
- Non-critical workflows

References:
    Upgrade to: agenkit.patterns.human_in_loop.HumanInLoopAgent

Example:
    Basic usage::

        from agenkit.techniques.compositions import SimpleApprovalTool
        from agenkit import Message

        tool = SimpleApprovalTool()
        result = await tool.execute(
            action="delete database",
            details="Will delete 'users' table"
        )

        if result["approved"]:
            # Proceed with action
            pass
"""

from typing import Dict, Any, Optional


class SimpleApprovalTool:
    """
    Simple approval tool for human-in-the-loop workflows.

    This is a minimal composition that prompts for yes/no approval via input().
    It has no error handling, timeouts, or sophisticated features - by design.

    For production systems, use agenkit.patterns.human_in_loop.HumanInLoopAgent
    which provides proper error handling, confidence thresholds, audit trails, etc.

    Attributes:
        prompt_template: Template for approval prompt
    """

    def __init__(self, prompt_template: str = "Approve {action}? (y/n): "):
        """
        Initialize simple approval tool.

        Args:
            prompt_template: Template string with {action} placeholder.
                Default: "Approve {action}? (y/n): "
        """
        self.prompt_template = prompt_template

    async def execute(
        self,
        action: str,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Request approval for an action.

        Args:
            action: The action to approve (e.g., "delete database")
            details: Optional details about the action

        Returns:
            Dictionary with:
                - approved (bool): Whether action was approved
                - response (str): The raw user response

        Example:
            >>> tool = SimpleApprovalTool()
            >>> result = await tool.execute("delete file")
            Approve delete file? (y/n): y
            >>> result["approved"]
            True
        """
        # Show details if provided
        if details:
            print(f"\nAction: {action}")
            print(f"Details: {details}")
            prompt = "Approve? (y/n): "
        else:
            prompt = self.prompt_template.format(action=action)

        # Get user input
        response = input(prompt).strip().lower()

        return {
            "approved": response in ("y", "yes"),
            "response": response
        }


def simple_approval(action: str, details: Optional[str] = None) -> bool:
    """
    Convenience function for simple synchronous approval.

    This is an even simpler wrapper around SimpleApprovalTool for
    quick scripts where you just need a boolean result.

    Args:
        action: The action to approve
        details: Optional details about the action

    Returns:
        True if approved, False otherwise

    Example:
        >>> from agenkit.techniques.compositions import simple_approval
        >>> if simple_approval("delete file", "file.txt"):
        ...     # Proceed with deletion
        ...     pass
    """
    tool = SimpleApprovalTool()

    # Create simple event loop for async call
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(tool.execute(action, details))
    return result["approved"]

"""
MCP Resource Management.

Handles registration and access to MCP resources (data sources).

Resources are identified by URIs and can return text, JSON, or binary data.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .schema import MCPResourceInfo


@dataclass
class Resource:
    """
    MCP Resource.

    Represents a data source that can be accessed via URI.
    """
    uri: str
    name: str
    description: str | None
    handler: Callable[[dict[str, Any]], Awaitable[Any]]
    mime_type: str = "text/plain"
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    async def fetch(self, params: dict[str, Any]) -> Any:
        """
        Fetch resource data.

        Args:
            params: Parameters for fetching resource

        Returns:
            Resource data
        """
        return await self.handler(params)

    def to_info(self) -> MCPResourceInfo:
        """Convert to MCPResourceInfo."""
        return MCPResourceInfo(
            uri=self.uri,
            name=self.name,
            description=self.description,
            mime_type=self.mime_type,
            metadata=self.metadata
        )


class ResourceRegistry:
    """
    Registry for MCP resources.

    Manages resource registration and lookup.
    """

    def __init__(self):
        """Initialize empty registry."""
        self.resources: dict[str, Resource] = {}

    def register(
        self,
        uri: str,
        name: str,
        handler: Callable[[dict[str, Any]], Awaitable[Any]],
        description: str | None = None,
        mime_type: str = "text/plain",
        metadata: dict[str, Any] | None = None
    ) -> Resource:
        """
        Register a resource.

        Args:
            uri: Resource URI (e.g., "file://doc.txt", "db://users")
            name: Human-readable name
            handler: Async function that returns resource data
            description: Optional description
            mime_type: MIME type of resource data
            metadata: Additional metadata

        Returns:
            Registered Resource

        Example:
            >>> async def get_user(params):
            ...     return {"name": "John", "email": "john@example.com"}
            >>>
            >>> registry.register(
            ...     uri="user://profile",
            ...     name="User Profile",
            ...     handler=get_user,
            ...     mime_type="application/json"
            ... )
        """
        resource = Resource(
            uri=uri,
            name=name,
            description=description,
            handler=handler,
            mime_type=mime_type,
            metadata=metadata or {}
        )

        self.resources[uri] = resource
        return resource

    def unregister(self, uri: str) -> bool:
        """
        Unregister a resource.

        Args:
            uri: Resource URI to remove

        Returns:
            True if removed, False if not found
        """
        if uri in self.resources:
            del self.resources[uri]
            return True
        return False

    def get(self, uri: str) -> Resource | None:
        """
        Get resource by URI.

        Args:
            uri: Resource URI

        Returns:
            Resource if found, None otherwise
        """
        return self.resources.get(uri)

    def list(self) -> list[MCPResourceInfo]:
        """
        List all registered resources.

        Returns:
            List of resource information
        """
        return [resource.to_info() for resource in self.resources.values()]

    async def fetch(self, uri: str, params: dict[str, Any] | None = None) -> Any:
        """
        Fetch resource data.

        Args:
            uri: Resource URI
            params: Parameters for fetching

        Returns:
            Resource data

        Raises:
            ValueError: If resource not found
        """
        resource = self.get(uri)
        if resource is None:
            raise ValueError(f"Resource not found: {uri}")

        return await resource.fetch(params or {})

    def has_resource(self, uri: str) -> bool:
        """
        Check if resource exists.

        Args:
            uri: Resource URI

        Returns:
            True if resource exists
        """
        return uri in self.resources

    def clear(self):
        """Clear all registered resources."""
        self.resources.clear()

    def __len__(self) -> int:
        """Return number of registered resources."""
        return len(self.resources)


def resource_decorator(
    uri: str,
    name: str,
    description: str | None = None,
    mime_type: str = "text/plain",
    metadata: dict[str, Any] | None = None
):
    """
    Decorator for registering resources.

    Args:
        uri: Resource URI
        name: Resource name
        description: Resource description
        mime_type: MIME type
        metadata: Additional metadata

    Example:
        >>> registry = ResourceRegistry()
        >>>
        >>> @resource_decorator(
        ...     uri="user://profile",
        ...     name="User Profile",
        ...     mime_type="application/json"
        ... )
        ... async def get_user_profile(params):
        ...     return {"name": "John"}
    """
    def decorator(func: Callable[[dict[str, Any]], Awaitable[Any]]):
        # Store registration info on function
        func._mcp_resource = {
            "uri": uri,
            "name": name,
            "description": description,
            "mime_type": mime_type,
            "metadata": metadata or {}
        }
        return func
    return decorator

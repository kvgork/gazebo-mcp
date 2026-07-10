"""
Shared MCPTool definition.

Single source of truth for the MCPTool dataclass used by all adapters.
"""

from dataclasses import dataclass
from typing import Dict, Any, Callable


@dataclass
class MCPTool:
    """MCP tool definition following Anthropic schema."""

    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.parameters.get("properties", {}),
                "required": self.parameters.get("required", []),
            },
        }

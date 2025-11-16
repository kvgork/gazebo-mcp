"""
Gazebo MCP Server.

Model Context Protocol server that exposes Gazebo control tools to AI assistants.
Provides model management, sensor data, world control, and simulation operations.

Architecture:
- Main server implements MCP protocol
- Adapters convert tool functions to MCP tool definitions
- Schema definitions follow Anthropic best practices
- ResultFilter pattern for token efficiency

Usage:
    python -m mcp.server.server

References:
- MCP Specification: https://modelcontextprotocol.io/
- Anthropic Best Practices: CLAUDE.md
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.utils import OperationResult
from gazebo_mcp.utils.logger import get_logger

# Import adapters:
from mcp.server.adapters import (
    model_management_adapter,
    sensor_tools_adapter,
    world_tools_adapter,
    simulation_tools_adapter,
)

_logger = get_logger("mcp_server")


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
                "required": self.parameters.get("required", [])
            }
        }


class GazeboMCPServer:
    """
    MCP Server for Gazebo control.

    Exposes Gazebo operations as MCP tools following Anthropic best practices:
    - Progressive disclosure (summary by default, details on request)
    - Token efficiency (ResultFilter pattern)
    - Clear error messages with suggestions
    - Agent-friendly response formats
    """

    def __init__(self):
        """Initialize MCP server with all tool adapters."""
        self.tools: Dict[str, MCPTool] = {}
        self._register_tools()
        _logger.info("Gazebo MCP Server initialized")

    def _register_tools(self):
        """Register all tools from adapters."""
        adapters = [
            model_management_adapter,
            sensor_tools_adapter,
            world_tools_adapter,
            simulation_tools_adapter,
        ]

        for adapter in adapters:
            tools = adapter.get_tools()
            for tool in tools:
                self.tools[tool.name] = tool
                _logger.debug(f"Registered tool: {tool.name}")

        _logger.info(f"Registered {len(self.tools)} MCP tools")

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools.

        Returns MCP-compliant tool list for discovery.
        """
        return [tool.to_dict() for tool in self.tools.values()]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool by name with arguments.

        Args:
            name: Tool name
            arguments: Tool arguments (validated against schema)

        Returns:
            MCP-compliant response:
            {
                "content": [{
                    "type": "text",
                    "text": <JSON result>
                }],
                "isError": false
            }

        Raises:
            ValueError: If tool not found
        """
        if name not in self.tools:
            available = ", ".join(self.tools.keys())
            raise ValueError(
                f"Tool '{name}' not found. Available tools: {available}"
            )

        tool = self.tools[name]

        try:
            # Call tool handler:
            result: OperationResult = tool.handler(**arguments)

            # Convert to MCP response:
            return self._format_response(result)

        except Exception as e:
            _logger.exception(f"Error calling tool {name}", error=str(e))
            return self._format_error(str(e))

    def _format_response(self, result: OperationResult) -> Dict[str, Any]:
        """
        Format OperationResult as MCP response.

        Args:
            result: Tool operation result

        Returns:
            MCP-compliant response with text content
        """
        # Convert result to dict:
        result_dict = {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "error_code": result.error_code,
            "suggestions": result.suggestions
        }

        # Format as JSON text:
        response_text = json.dumps(result_dict, indent=2)

        return {
            "content": [
                {
                    "type": "text",
                    "text": response_text
                }
            ],
            "isError": not result.success
        }

    def _format_error(self, error_message: str) -> Dict[str, Any]:
        """
        Format error as MCP response.

        Args:
            error_message: Error message

        Returns:
            MCP error response
        """
        error_dict = {
            "success": False,
            "data": None,
            "error": error_message,
            "error_code": "INTERNAL_ERROR",
            "suggestions": [
                "Check tool arguments",
                "Verify Gazebo is running",
                "Check server logs"
            ]
        }

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(error_dict, indent=2)
                }
            ],
            "isError": True
        }

    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP protocol message.

        Args:
            message: MCP message (JSON-RPC 2.0)

        Returns:
            MCP response
        """
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")

        try:
            if method == "tools/list":
                result = self.list_tools()
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": result}
                }

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = self.call_tool(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": result
                }

            else:
                raise ValueError(f"Unknown method: {method}")

        except Exception as e:
            _logger.exception(f"Error handling message", error=str(e))
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    def run(self):
        """
        Run MCP server (stdio protocol).

        Reads JSON-RPC messages from stdin, writes responses to stdout.
        """
        _logger.info("Starting Gazebo MCP Server on stdio")

        try:
            for line in sys.stdin:
                if not line.strip():
                    continue

                try:
                    message = json.loads(line)
                    response = self.handle_message(message)
                    print(json.dumps(response), flush=True)

                except json.JSONDecodeError as e:
                    _logger.error(f"Invalid JSON", error=str(e))
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response), flush=True)

        except KeyboardInterrupt:
            _logger.info("Server stopped by user")

        except Exception as e:
            _logger.exception("Server error", error=str(e))
            raise


def main():
    """Main entry point for MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    server = GazeboMCPServer()
    server.run()


if __name__ == "__main__":
    main()

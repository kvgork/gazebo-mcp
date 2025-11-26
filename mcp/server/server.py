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
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.utils import OperationResult
from gazebo_mcp.utils.logger import get_logger
from gazebo_mcp.utils.metrics import get_metrics_collector

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
        metrics = get_metrics_collector()

        # Start timing:
        start_time = time.time()

        try:
            # Call tool handler:
            result: OperationResult = tool.handler(**arguments)

            # Calculate duration:
            duration = time.time() - start_time

            # Estimate token usage:
            tokens_sent, tokens_saved = self._estimate_tokens(result, arguments)

            # Record metrics:
            metrics.record_tool_call(
                tool_name=name,
                duration=duration,
                tokens_sent=tokens_sent,
                tokens_saved=tokens_saved,
                success=result.success
            )

            # Convert to MCP response:
            return self._format_response(result)

        except Exception as e:
            # Record error:
            duration = time.time() - start_time
            metrics.record_tool_call(
                tool_name=name,
                duration=duration,
                success=False
            )
            metrics.record_error(
                error_type=type(e).__name__,
                error_message=str(e)
            )

            _logger.exception(f"Error calling tool {name}", error=str(e))
            return self._format_error(str(e))

    def _estimate_tokens(self, result: OperationResult, arguments: Dict[str, Any]) -> tuple[int, int]:
        """
        Estimate token usage for a tool call.

        Args:
            result: Tool operation result
            arguments: Tool arguments

        Returns:
            Tuple of (tokens_sent, tokens_saved)
        """
        tokens_sent = 0
        tokens_saved = 0

        if not result.success or not result.data:
            return (0, 0)

        # Check for explicit token info in result:
        if "tokens_saved" in result.data:
            tokens_saved = result.data["tokens_saved"]
        if "tokens_sent" in result.data:
            tokens_sent = result.data["tokens_sent"]
            return (tokens_sent, tokens_saved)

        # Estimate based on response format for list operations:
        response_format = arguments.get("response_format", "filtered")

        # For model listings:
        if "models" in result.data:
            models = result.data["models"]
            if isinstance(models, list):
                model_count = len(models)

                if response_format == "summary":
                    # Summary format: just counts and names
                    tokens_sent = 100 + (model_count * 2)  # ~2 tokens per name
                    # Calculate tokens saved (what filtered would have used):
                    tokens_saved = (model_count * 50) - tokens_sent  # ~50 tokens per full model
                else:
                    # Filtered format: full details
                    tokens_sent = model_count * 50

        # For sensor listings:
        elif "sensors" in result.data:
            sensors = result.data["sensors"]
            if isinstance(sensors, list):
                sensor_count = len(sensors)

                if response_format == "summary":
                    tokens_sent = 100 + (sensor_count * 2)
                    tokens_saved = (sensor_count * 40) - tokens_sent
                else:
                    tokens_sent = sensor_count * 40

        # For simple operations (spawn, delete, state queries):
        else:
            # Estimate based on JSON response size:
            json_str = json.dumps(result.data)
            tokens_sent = len(json_str) // 4  # Rough estimate: 4 chars per token

        return (tokens_sent, tokens_saved)

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
            if method == "initialize":
                # Handle MCP initialization
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "gazebo-mcp-server",
                            "version": "0.1.0"
                        }
                    }
                }

            elif method == "tools/list":
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

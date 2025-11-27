"""
ROS2 Gazebo MCP Server.

Extends the Claude Code Learning System MCP Server with ROS2/Gazebo-specific functionality.

Implements the Model Context Protocol pattern for 98.7% token reduction:
- Exposes Gazebo tools as importable Python modules
- Executes code locally in sandboxed environment
- Returns only filtered results to agent
- Manages ROS2 connection lifecycle

Based on: claude/mcp/servers/skills-mcp/server.py
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

# Add claude project to path for importing infrastructure
# Use environment variable or relative path from project root
CLAUDE_ROOT = Path(os.environ.get("CLAUDE_ROOT", Path(__file__).parents[2] / "claude"))
if CLAUDE_ROOT.exists():
    sys.path.insert(0, str(CLAUDE_ROOT))

# Add current project to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from skills.execution.sandboxed_executor import SandboxedExecutor, SandboxConfig
from skills.execution.code_executor import ExecutionResult


@dataclass
class MCPRequest:
    """MCP execution request."""
    code: str
    context: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None


@dataclass
class MCPResponse:
    """MCP execution response."""
    success: bool
    result: Any = None
    error: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    tokens_saved: Optional[int] = None
    ros2_status: Optional[str] = None


class GazeboMCPServer:
    """
    ROS2 Gazebo MCP Server.

    Extends base MCP Server with ROS2/Gazebo-specific functionality:
    - ROS2 connection management
    - Gazebo simulation state tracking
    - Extended sandbox for ROS2/Gazebo paths
    - Health monitoring for ROS2 nodes

    Example usage:
        server = GazeboMCPServer(
            workspace_dir="/path/to/ros2_ws",
            ros2_workspace="/opt/ros/humble"
        )

        request = MCPRequest(code='''
from gazebo_mcp.tools.model_management import list_models
from skills.common.filters import ResultFilter

# Get all models (filtered format):
result = list_models(response_format="filtered")

# Filter locally (98.7% token savings!):
turtlebots = ResultFilter.search(result["models"], "turtlebot3", ["name"])
burger = ResultFilter.filter_by_field(turtlebots, "variant", "burger")

print(f"Found: {burger[0]['name']}")
        ''')

        response = server.execute(request)
        print(response.result)
    """

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        ros2_workspace: Optional[str] = None,
        gazebo_model_path: Optional[str] = None
    ):
        """
        Initialize Gazebo MCP server.

        Args:
            workspace_dir: Project workspace directory (default: current dir)
            ros2_workspace: ROS2 installation path (default: $ROS2_WS or /opt/ros/humble)
            gazebo_model_path: Gazebo models path (default: /usr/share/gazebo)
        """
        self.workspace_dir = workspace_dir or os.getcwd()
        self.ros2_workspace = ros2_workspace or os.getenv("ROS2_WS", "/opt/ros/humble")
        self.gazebo_model_path = gazebo_model_path or "/usr/share/gazebo"

        # Configure sandbox for ROS2/Gazebo:
        config = SandboxConfig(
            workspace_dir=self.workspace_dir,
            allowed_paths=[
                self.workspace_dir,
                self.ros2_workspace,
                self.gazebo_model_path,
                "/tmp",
                "/home"  # For ROS2 logs
            ],
            read_only_paths=[
                self.ros2_workspace,
                self.gazebo_model_path
            ],
            allowed_domains=[
                "api.anthropic.com",
                "packages.ros.org",
                "gazebosim.org",
                "github.com",  # For model downloads
                "osrfoundation.org"  # For Gazebo resources
            ],
            max_cpu_time=60,  # Allow 60s for Gazebo startup
            max_memory=2048,  # 2GB for Gazebo simulation
            max_processes=20  # Allow more processes for ROS2 nodes
        )

        # Initialize sandboxed executor:
        self.executor = SandboxedExecutor(
            workspace_dir=self.workspace_dir,
            config=config
        )

        # ROS2 connection manager (will be initialized when first needed):
        self._connection_manager = None
        self._ros2_initialized = False

    def _ensure_ros2_connection(self) -> tuple[bool, Optional[str]]:
        """
        Ensure ROS2 connection is established.

        Returns:
            Tuple of (connected: bool, error_message: Optional[str])
        """
        if self._ros2_initialized:
            # Check if still connected:
            if self._connection_manager and hasattr(self._connection_manager, 'is_connected'):
                if self._connection_manager.is_connected():
                    return True, None
                else:
                    return False, "ROS2 connection lost"

        # Try to initialize ROS2 connection:
        try:
            # Import connection manager (will be implemented in Phase 2):
            try:
                from gazebo_mcp.bridge.connection_manager import ConnectionManager
                self._connection_manager = ConnectionManager()
                self._connection_manager.connect()
                self._ros2_initialized = True
                return True, None

            except ImportError:
                # Connection manager not yet implemented - that's OK for now
                # Server will work but tools requiring ROS2 will fail gracefully
                return False, "ROS2 ConnectionManager not yet implemented (Phase 2)"

        except Exception as e:
            return False, f"ROS2 connection failed: {str(e)}"

    def execute(self, request: MCPRequest) -> MCPResponse:
        """
        Execute MCP request with ROS2 connection check.

        Args:
            request: MCP execution request

        Returns:
            MCPResponse with results and ROS2 status
        """
        # Check ROS2 connection (non-blocking - just log status):
        ros2_connected, ros2_error = self._ensure_ros2_connection()
        ros2_status = "connected" if ros2_connected else f"disconnected: {ros2_error}"

        # Execute in sandbox:
        result = self.executor.execute(
            code=request.code,
            context=request.context,
            timeout=request.timeout or 60  # Default 60s for Gazebo
        )

        # Convert ExecutionResult to MCPResponse:
        return self._convert_result(result, ros2_status)

    def _convert_result(
        self,
        result: ExecutionResult,
        ros2_status: str
    ) -> MCPResponse:
        """Convert ExecutionResult to MCPResponse with ROS2 status."""
        return MCPResponse(
            success=result.success,
            result=result.output,
            error=result.error,
            stdout=result.stdout,
            stderr=result.stderr,
            duration=result.duration,
            tokens_saved=result.tokens_saved,
            ros2_status=ros2_status
        )

    def execute_json(self, request_json: str) -> str:
        """
        Execute code request from JSON.

        Args:
            request_json: JSON-encoded MCPRequest

        Returns:
            JSON-encoded MCPResponse
        """
        try:
            # Parse request:
            data = json.loads(request_json)
            request = MCPRequest(**data)

            # Execute:
            response = self.execute(request)

            # Return JSON:
            return json.dumps(asdict(response), indent=2)

        except Exception as e:
            error_response = MCPResponse(
                success=False,
                error=f"Server error: {str(e)}"
            )
            return json.dumps(asdict(error_response), indent=2)

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available Gazebo tools.

        Returns:
            List of tool metadata
        """
        tools_dir = Path(PROJECT_ROOT) / "src" / "gazebo_mcp" / "tools"

        if not tools_dir.exists():
            return []

        available_tools = []

        for tool_file in tools_dir.glob("*.py"):
            if tool_file.name.startswith("__"):
                continue

            tool_name = tool_file.stem
            available_tools.append({
                "name": tool_name,
                "path": f"gazebo_mcp.tools.{tool_name}",
                "file": str(tool_file)
            })

        return available_tools

    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        ros2_connected, ros2_error = self._ensure_ros2_connection()

        return {
            "workspace_dir": self.workspace_dir,
            "ros2_workspace": self.ros2_workspace,
            "gazebo_model_path": self.gazebo_model_path,
            "ros2_status": "connected" if ros2_connected else f"disconnected: {ros2_error}",
            "sandbox_stats": self.executor.get_stats(),
            "available_tools": len(self.get_available_tools()),
            "tools": [t["name"] for t in self.get_available_tools()]
        }

    def shutdown(self):
        """Clean shutdown with ROS2 disconnect."""
        print("Shutting down Gazebo MCP server...", file=sys.stderr)

        # Disconnect ROS2:
        if self._connection_manager and hasattr(self._connection_manager, 'disconnect'):
            try:
                self._connection_manager.disconnect()
                print("ROS2 connection closed", file=sys.stderr)
            except Exception as e:
                print(f"Warning: ROS2 disconnect error: {e}", file=sys.stderr)

        # Executor cleanup:
        if hasattr(self.executor, 'cleanup'):
            self.executor.cleanup()


def start_stdio_server():
    """
    Start Gazebo MCP server in STDIO mode.

    This is the standard MCP server mode where:
    - Requests come via stdin (JSON)
    - Responses go via stdout (JSON)
    - Agent communicates via standard I/O
    """
    server = GazeboMCPServer()

    # Send ready message:
    print(json.dumps({
        "status": "ready",
        "server": "ros2-gazebo-mcp",
        "version": "1.0.0",
        "capabilities": {
            "code_execution": True,
            "gazebo_tools": True,
            "ros2_integration": True,
            "sandboxed": True,
            "token_optimization": True
        },
        "stats": server.get_stats()
    }), flush=True)

    # Process requests from stdin:
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                # Parse request:
                request_data = json.loads(line)

                if request_data.get("type") == "execute":
                    # Execute code:
                    request = MCPRequest(
                        code=request_data["code"],
                        context=request_data.get("context"),
                        timeout=request_data.get("timeout")
                    )
                    response = server.execute(request)
                    print(json.dumps(asdict(response)), flush=True)

                elif request_data.get("type") == "list_tools":
                    # List available tools:
                    tools = server.get_available_tools()
                    print(json.dumps({"tools": tools}), flush=True)

                elif request_data.get("type") == "stats":
                    # Get server stats:
                    stats = server.get_stats()
                    print(json.dumps(stats), flush=True)

                elif request_data.get("type") == "shutdown":
                    # Shutdown server:
                    server.shutdown()
                    print(json.dumps({"status": "shutdown"}), flush=True)
                    break

                else:
                    print(json.dumps({
                        "error": f"Unknown request type: {request_data.get('type')}"
                    }), flush=True)

            except Exception as e:
                print(json.dumps({
                    "error": f"Request processing error: {str(e)}"
                }), flush=True)

    except KeyboardInterrupt:
        server.shutdown()
        print(json.dumps({"status": "shutdown"}), flush=True)


def start_http_server(port: int = 8080):
    """
    Start Gazebo MCP server in HTTP mode (for development/testing).

    Args:
        port: Port to listen on
    """
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
    except ImportError:
        print("HTTP server requires Python 3.x", file=sys.stderr)
        sys.exit(1)

    server = GazeboMCPServer()

    class MCPRequestHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length).decode('utf-8')

            response_json = server.execute_json(body)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_json.encode('utf-8'))

        def do_GET(self):
            if self.path == "/stats":
                stats = server.get_stats()
                response = json.dumps(stats, indent=2)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(response.encode('utf-8'))

            elif self.path == "/tools":
                tools = server.get_available_tools()
                response = json.dumps({"tools": tools}, indent=2)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(response.encode('utf-8'))

            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            # Log to stderr (not stdout - reserved for MCP protocol):
            sys.stderr.write(f"{self.address_string()} - {format % args}\n")

    httpd = HTTPServer(('localhost', port), MCPRequestHandler)
    print(f"✓ Gazebo MCP server listening on http://localhost:{port}", file=sys.stderr)
    print(f"  POST /execute - Execute code", file=sys.stderr)
    print(f"  GET /stats - Server statistics", file=sys.stderr)
    print(f"  GET /tools - Available tools", file=sys.stderr)
    print(f"\nExample request:", file=sys.stderr)
    print(f"  curl -X POST http://localhost:{port}/execute \\", file=sys.stderr)
    print(f"    -H 'Content-Type: application/json' \\", file=sys.stderr)
    print(f"    -d '{{'\"code\"': '\"print(\\\\\"Hello from Gazebo MCP!\\\\\")\"'}}'\n", file=sys.stderr)

    httpd.serve_forever()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ROS2 Gazebo MCP Server")
    parser.add_argument(
        "--mode",
        choices=["stdio", "http"],
        default="stdio",
        help="Server mode (stdio for Claude Desktop, http for testing)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HTTP mode"
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default=None,
        help="ROS2 workspace directory"
    )
    parser.add_argument(
        "--ros2-workspace",
        type=str,
        default=None,
        help="ROS2 installation path (default: $ROS2_WS or /opt/ros/humble)"
    )

    args = parser.parse_args()

    if args.mode == "stdio":
        start_stdio_server()
    else:
        start_http_server(port=args.port)

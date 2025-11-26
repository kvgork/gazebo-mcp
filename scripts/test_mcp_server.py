#!/usr/bin/env python3
"""
Test MCP Server Functionality.

Simple script to verify the MCP server can initialize and list tools.
"""

import sys
from pathlib import Path

# Add src to path:
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.server import GazeboMCPServer


def test_server_initialization():
    """Test that server initializes correctly."""
    print("Testing MCP Server Initialization...")

    try:
        server = GazeboMCPServer()
        print(f"✓ Server initialized successfully")
        return server
    except Exception as e:
        print(f"✗ Server initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def test_list_tools(server):
    """Test that server can list tools."""
    print("\nTesting Tool Listing...")

    try:
        tools = server.list_tools()
        print(f"✓ Found {len(tools)} tools")

        # Group by category:
        categories = {}
        for tool in tools:
            name = tool["name"]
            if "model" in name:
                category = "Model Management"
            elif "sensor" in name:
                category = "Sensor Tools"
            elif "world" in name:
                category = "World Tools"
            elif "simulation" in name or "pause" in name or "unpause" in name or "reset" in name:
                category = "Simulation Control"
            else:
                category = "Other"

            if category not in categories:
                categories[category] = []
            categories[category].append(name)

        print("\nTools by Category:")
        for category, tool_names in sorted(categories.items()):
            print(f"\n  {category} ({len(tool_names)} tools):")
            for tool_name in sorted(tool_names):
                print(f"    - {tool_name}")

        return tools
    except Exception as e:
        print(f"✗ Tool listing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def test_call_tool(server):
    """Test that server can call a tool."""
    print("\nTesting Tool Invocation...")

    try:
        # Test get_simulation_status (doesn't require Gazebo):
        result = server.call_tool("gazebo_get_simulation_status", {})
        print(f"✓ Tool call successful")

        # Check result structure:
        if "content" in result and result["content"]:
            import json
            content_text = result["content"][0]["text"]
            data = json.loads(content_text)
            print(f"  - Success: {data['success']}")
            print(f"  - Running: {data['data'].get('running', 'N/A')}")
            print(f"  - Gazebo Connected: {data['data'].get('gazebo_connected', 'N/A')}")

            if data['data'].get('note'):
                print(f"  - Note: {data['data']['note']}")

        return result
    except Exception as e:
        print(f"✗ Tool call failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def test_handle_message(server):
    """Test JSON-RPC message handling."""
    print("\nTesting JSON-RPC Message Handling...")

    try:
        # Test tools/list message:
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        response = server.handle_message(message)
        print(f"✓ Message handled successfully")
        print(f"  - Response ID: {response.get('id')}")
        print(f"  - Tools count: {len(response.get('result', {}).get('tools', []))}")

        return response
    except Exception as e:
        print(f"✗ Message handling failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Run all tests."""
    print("=" * 60)
    print("Gazebo MCP Server Verification")
    print("=" * 60)

    # Test 1: Initialization
    server = test_server_initialization()

    # Test 2: List tools
    tools = test_list_tools(server)

    # Test 3: Call a tool
    result = test_call_tool(server)

    # Test 4: Handle JSON-RPC message
    response = test_handle_message(server)

    print("\n" + "=" * 60)
    print("All Tests Passed! ✓")
    print("=" * 60)
    print("\nThe MCP server is ready to use!")
    print("\nTo run the server:")
    print("  python -m mcp.server.server")
    print("\nTo integrate with Claude Desktop:")
    print("  See mcp/README.md for configuration instructions")
    print("=" * 60)


if __name__ == "__main__":
    main()

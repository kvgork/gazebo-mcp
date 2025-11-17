#!/usr/bin/env python3
"""
Example 1: Basic Connection and Model Listing

This example demonstrates:
- Creating an MCP server instance
- Listing available MCP tools
- Getting simulation status
- Listing models (with different response formats)
- Understanding graceful fallback when Gazebo unavailable

Prerequisites:
- None (works without ROS2/Gazebo, will use mock data)

Optional:
- ROS2 sourced for real connection
- Gazebo running for real data

Usage:
    python examples/01_basic_connection.py
"""

import sys
from pathlib import Path
import json

# Add project to path:
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mcp.server.server import GazeboMCPServer


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(result: dict, indent: int = 0):
    """Pretty print MCP result."""
    spacing = "  " * indent

    # Extract content from MCP response:
    if "content" in result and result["content"]:
        content_text = result["content"][0]["text"]
        data = json.loads(content_text)

        if data["success"]:
            print(f"{spacing}✓ Success")
            if "data" in data and data["data"]:
                print(f"{spacing}Data:")
                print(json.dumps(data["data"], indent=2))
        else:
            print(f"{spacing}✗ Error: {data['error']}")
            if data.get("suggestions"):
                print(f"{spacing}Suggestions:")
                for suggestion in data["suggestions"]:
                    print(f"{spacing}  - {suggestion}")
    else:
        print(json.dumps(result, indent=2))


def main():
    """Run basic connection example."""

    print_section("Gazebo MCP Server - Basic Connection Example")

    # Step 1: Create MCP server instance
    print("\n1. Creating MCP Server...")
    try:
        server = GazeboMCPServer()
        print("   ✓ Server created successfully")
        print(f"   ✓ Registered {len(server.tools)} tools")
    except Exception as e:
        print(f"   ✗ Failed to create server: {e}")
        return

    # Step 2: List all available tools
    print_section("2. Available MCP Tools")
    tools = server.list_tools()

    # Group by category:
    categories = {}
    for tool in tools:
        name = tool["name"]
        desc = tool["description"].split("\n")[0]  # First line only

        # Categorize:
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
        categories[category].append((name, desc))

    for category, tool_list in sorted(categories.items()):
        print(f"\n{category} ({len(tool_list)} tools):")
        for tool_name, tool_desc in sorted(tool_list):
            print(f"  • {tool_name}")
            print(f"    {tool_desc[:70]}...")

    # Step 3: Get simulation status
    print_section("3. Simulation Status")
    print("\nQuerying simulation status...")
    result = server.call_tool("gazebo_get_simulation_status", {})
    print_result(result, indent=1)

    # Note about connection:
    content = json.loads(result["content"][0]["text"])
    if not content["data"].get("gazebo_connected", False):
        print("\n   ℹ Note: Gazebo not connected")
        print("   The server is working in MOCK mode")
        print("   To connect to real Gazebo:")
        print("     1. Source ROS2: source /opt/ros/humble/setup.bash")
        print("     2. Start Gazebo: ros2 launch gazebo_ros gazebo.launch.py")
        print("     3. Re-run this script")

    # Step 4: List models (summary format)
    print_section("4. List Models (Summary Format)")
    print("\nGetting model summary...")
    result = server.call_tool("gazebo_list_models", {
        "response_format": "summary"
    })
    print_result(result, indent=1)

    # Step 5: List models (filtered format with examples)
    print_section("5. List Models (Filtered Format)")
    print("\nGetting models with filter examples...")
    result = server.call_tool("gazebo_list_models", {
        "response_format": "filtered"
    })

    # Show filter examples:
    content = json.loads(result["content"][0]["text"])
    if content["success"] and "data" in content:
        data = content["data"]
        print(f"   ✓ Found {len(data.get('models', []))} models")

        if "filter_examples" in data:
            print("\n   Filter Examples (for client-side filtering):")
            for key, example in data["filter_examples"].items():
                print(f"     {key}:")
                print(f"       {example}")

        # Show first few models:
        models = data.get("models", [])
        if models:
            print(f"\n   First {min(3, len(models))} models:")
            for model in models[:3]:
                print(f"     • {model.get('name', 'unknown')}")
                if "position" in model:
                    pos = model["position"]
                    print(f"       Position: ({pos['x']:.2f}, {pos['y']:.2f}, {pos['z']:.2f})")

    # Step 6: Token efficiency demonstration
    print_section("6. Token Efficiency")
    print("\nComparing response sizes...")

    # Get both formats:
    summary_result = server.call_tool("gazebo_list_models", {
        "response_format": "summary"
    })
    filtered_result = server.call_tool("gazebo_list_models", {
        "response_format": "filtered"
    })

    summary_text = summary_result["content"][0]["text"]
    filtered_text = filtered_result["content"][0]["text"]

    summary_size = len(summary_text)
    filtered_size = len(filtered_text)

    print(f"   Summary format size: {summary_size} chars")
    print(f"   Filtered format size: {filtered_size} chars")

    if filtered_size > 0:
        savings = ((filtered_size - summary_size) / filtered_size) * 100
        print(f"   Token savings: ~{savings:.1f}% with summary format")

    print("\n   💡 For large simulations with 100+ models:")
    print("      - Summary format: ~500 tokens")
    print("      - Filtered format: ~50,000+ tokens")
    print("      - Savings: 95-99%!")

    # Summary
    print_section("Summary")
    print("""
This example demonstrated:
  ✓ Creating an MCP server
  ✓ Listing available tools (17 tools across 4 categories)
  ✓ Getting simulation status
  ✓ Listing models with different formats
  ✓ Token efficiency with ResultFilter pattern

Next steps:
  • Run Example 2 to spawn and control models
  • Run Example 3 to stream sensor data
  • Check examples/README.md for more examples

Note: This example works WITHOUT Gazebo running (mock mode).
      For real data, start Gazebo before running the script.
    """)

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()

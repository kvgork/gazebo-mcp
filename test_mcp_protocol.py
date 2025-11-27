#!/usr/bin/env python3
"""Test MCP protocol directly."""
import subprocess
import json
import sys
import os
from pathlib import Path

# Find the MCP server wrapper script
# Check standard locations: ~/.local/bin or project bin/
server_script = os.environ.get("GAZEBO_MCP_SERVER",
                               os.path.expanduser("~/.local/bin/gazebo-mcp-server"))
if not Path(server_script).exists():
    print(f"Error: gazebo-mcp-server not found at {server_script}")
    print("Set GAZEBO_MCP_SERVER environment variable or install with install_mcp_global.sh")
    sys.exit(1)

# Start the MCP server
proc = subprocess.Popen(
    [server_script],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

# Send initialize request
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    }
}

print("Sending initialize request...")
proc.stdin.write(json.dumps(init_request) + '\n')
proc.stdin.flush()

# Read response
import select
if select.select([proc.stdout], [], [], 5.0)[0]:
    response = proc.stdout.readline()
    print(f"Response: {response}")
    
    # Send tools/list request
    list_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    print("\nSending tools/list request...")
    proc.stdin.write(json.dumps(list_request) + '\n')
    proc.stdin.flush()
    
    if select.select([proc.stdout], [], [], 5.0)[0]:
        response = proc.stdout.readline()
        print(f"Response: {response}")
else:
    print("Timeout waiting for response")

# Clean up
proc.terminate()
proc.wait()

# Gazebo MCP Server - Quick Installation

⚡ **Get up and running in 2 commands!**

## Installation

```bash
cd <path_to_gazebo_mcp_package>
./install_mcp_global.sh --with-ros2
```

**What this does:**
- Installs ROS2 Humble + Gazebo Harmonic
- Installs Python dependencies
- Registers MCP server globally with Claude Code
- Configures everything automatically

**Time:** ~5-10 minutes (depending on download speed)

## Verification

```bash
./verify_mcp_installation.sh
```

**Expected:** ✓ All checks passed!

## Start Using

1. **Restart your terminal**
   ```bash
   source ~/.bashrc
   ```

2. **Restart Claude Code** (completely exit and reopen)

3. **Check MCP status**
   - In Claude Code, type: `/mcp`
   - Should see "gazebo" server listed

4. **Start asking!**
   - "List all models in the Gazebo simulation"
   - "Spawn a box at position (1, 2, 0.5)"
   - "Get simulation status"

## Troubleshooting

### Not seeing "gazebo" in `/mcp`?

```bash
# Check if registered
claude mcp list

# Re-run installation
./install_mcp_global.sh --with-ros2

# Verify
./verify_mcp_installation.sh
```

### Want to uninstall?

```bash
./uninstall_mcp_global.sh
```

## Full Documentation

- **Complete Guide:** `INSTALL_MCP.md`
- **Setup Manual:** `MCP_SETUP_GUIDE.md`
- **Demos:** `demos/README.md`

## Available Scripts

| Script | Purpose |
|--------|---------|
| `install_mcp_global.sh` | Install MCP server globally |
| `verify_mcp_installation.sh` | Verify installation |
| `uninstall_mcp_global.sh` | Remove MCP server |

## That's It!

Once installed, just ask Claude to control Gazebo naturally. The MCP server handles all the technical details for you! 🤖✨

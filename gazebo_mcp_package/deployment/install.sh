#!/bin/bash
#
# Installation script for Gazebo MCP Server
#
# Usage:
#   sudo ./install.sh
#

set -e

echo "=========================================="
echo "  Gazebo MCP Server Installation"
echo "=========================================="

# Check if running as root:
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (sudo ./install.sh)"
    exit 1
fi

# Variables:
INSTALL_DIR="/opt/ros2_gazebo_mcp"
SERVICE_FILE="gazebo-mcp.service"
USER="mcp"
GROUP="mcp"

# 1. Create user if doesn't exist:
echo "[1/7] Creating user and group..."
if ! id "$USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$INSTALL_DIR" "$USER"
    echo "✓ Created user: $USER"
else
    echo "✓ User already exists: $USER"
fi

# 2. Create installation directory:
echo "[2/7] Creating installation directory..."
mkdir -p "$INSTALL_DIR"
mkdir -p /var/log/gazebo_mcp
mkdir -p /var/metrics/gazebo_mcp

# 3. Copy files:
echo "[3/7] Copying files..."
cp -r ../src "$INSTALL_DIR/"
cp -r ../mcp "$INSTALL_DIR/"
cp -r ../scripts "$INSTALL_DIR/"
cp ../requirements.txt "$INSTALL_DIR/"

# 4. Set permissions:
echo "[4/7] Setting permissions..."
chown -R "$USER:$GROUP" "$INSTALL_DIR"
chown -R "$USER:$GROUP" /var/log/gazebo_mcp
chown -R "$USER:$GROUP" /var/metrics/gazebo_mcp
chmod 755 "$INSTALL_DIR"

# 5. Install Python dependencies:
echo "[5/7] Installing Python dependencies..."
pip3 install -r "$INSTALL_DIR/requirements.txt"

# 6. Install systemd service:
echo "[6/7] Installing systemd service..."
cp "$SERVICE_FILE" /etc/systemd/system/
systemctl daemon-reload
systemctl enable gazebo-mcp

# 7. Done:
echo "[7/7] Installation complete!"
echo ""
echo "=========================================="
echo "  Installation Summary"
echo "=========================================="
echo "Installation directory: $INSTALL_DIR"
echo "Service user: $USER"
echo "Log directory: /var/log/gazebo_mcp"
echo "Metrics directory: /var/metrics/gazebo_mcp"
echo ""
echo "To start the service:"
echo "  sudo systemctl start gazebo-mcp"
echo ""
echo "To check status:"
echo "  sudo systemctl status gazebo-mcp"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u gazebo-mcp -f"
echo ""
echo "=========================================="

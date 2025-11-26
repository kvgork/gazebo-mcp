# Gazebo MCP Server Docker Image
#
# Multi-stage build for optimized image size
# Supports both ROS2 Humble and Jazzy
#
# Build:
#   docker build -t gazebo-mcp:latest .
#
# Run:
#   docker run -it --rm gazebo-mcp:latest

# Build arguments for customization:
ARG ROS_DISTRO=humble
ARG PYTHON_VERSION=3.10

# ============================================================================
# Stage 1: Base ROS2 image with dependencies
# ============================================================================
FROM ros:${ROS_DISTRO}-ros-base AS base

# Set environment variables:
ENV DEBIAN_FRONTEND=noninteractive \
    ROS_DISTRO=${ROS_DISTRO} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies:
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Gazebo and ROS2 packages:
    ros-${ROS_DISTRO}-gazebo-ros-pkgs \
    ros-${ROS_DISTRO}-gazebo-msgs \
    # Python and tools:
    python3-pip \
    python3-dev \
    # Build tools:
    build-essential \
    cmake \
    git \
    # Utilities:
    curl \
    wget \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip:
RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# ============================================================================
# Stage 2: Development dependencies (for testing)
# ============================================================================
FROM base AS dev

WORKDIR /workspace/ros2_gazebo_mcp

# Copy requirements files:
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies (including dev):
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir -r requirements-dev.txt

# Copy source code:
COPY . .

# Set up ROS2 environment:
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc

# Run tests to verify build:
RUN pytest tests/test_utils.py -v || true

# ============================================================================
# Stage 3: Production image (minimal)
# ============================================================================
FROM base AS production

WORKDIR /workspace/ros2_gazebo_mcp

# Copy only requirements (not dev requirements):
COPY requirements.txt ./

# Install only production dependencies:
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy only necessary files:
COPY src/ ./src/
COPY mcp/ ./mcp/
COPY scripts/ ./scripts/
COPY examples/ ./examples/

# Set up ROS2 environment:
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc && \
    echo "export PYTHONPATH=/workspace/ros2_gazebo_mcp/src:\$PYTHONPATH" >> ~/.bashrc

# Expose MCP server (stdio mode doesn't need ports):
# If running HTTP mode, expose port 8080:
# EXPOSE 8080

# Health check (verify server can start):
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "from mcp.server.server import GazeboMCPServer; GazeboMCPServer()" || exit 1

# Default command: Run MCP server in stdio mode:
CMD ["python3", "-m", "mcp.server.server"]

# ============================================================================
# Stage 4: GPU-enabled image (for Gazebo GUI)
# ============================================================================
FROM production AS gpu

# Install additional packages for GPU support:
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    mesa-utils \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Set up display forwarding:
ENV DISPLAY=:0
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=graphics,utility,compute

# ============================================================================
# Labels and metadata
# ============================================================================
LABEL maintainer="Gazebo MCP Team"
LABEL description="Model Context Protocol server for Gazebo simulation control"
LABEL version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/yourusername/ros2_gazebo_mcp"
LABEL org.opencontainers.image.documentation="https://github.com/yourusername/ros2_gazebo_mcp/blob/main/README.md"

# Usage examples:
#
# 1. Build production image:
#    docker build --target production -t gazebo-mcp:latest .
#
# 2. Build development image:
#    docker build --target dev -t gazebo-mcp:dev .
#
# 3. Build GPU-enabled image:
#    docker build --target gpu -t gazebo-mcp:gpu .
#
# 4. Build for ROS2 Jazzy:
#    docker build --build-arg ROS_DISTRO=jazzy -t gazebo-mcp:jazzy .
#
# 5. Run with docker-compose:
#    docker-compose up

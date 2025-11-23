"""
Configuration management for Gazebo MCP Server.

Provides centralized configuration with Pydantic validation,
environment variable support, and multiple environment profiles.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum

try:
    from pydantic import BaseModel, Field, validator
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseModel, Field, validator, BaseSettings

import yaml


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class ROS2Config(BaseModel):
    """ROS2-specific configuration."""

    domain_id: int = Field(
        default=0,
        ge=0,
        le=101,
        description="ROS2 domain ID (0-101)"
    )

    namespace: str = Field(
        default="",
        description="ROS2 namespace for nodes"
    )

    use_sim_time: bool = Field(
        default=True,
        description="Use simulation time instead of wall time"
    )

    qos_reliability: str = Field(
        default="reliable",
        description="QoS reliability policy (reliable/best_effort)"
    )

    qos_durability: str = Field(
        default="volatile",
        description="QoS durability policy (volatile/transient_local)"
    )

    @validator("qos_reliability")
    def validate_reliability(cls, v):
        """Validate QoS reliability policy."""
        valid = ["reliable", "best_effort"]
        if v not in valid:
            raise ValueError(f"qos_reliability must be one of {valid}")
        return v

    @validator("qos_durability")
    def validate_durability(cls, v):
        """Validate QoS durability policy."""
        valid = ["volatile", "transient_local", "transient", "persistent"]
        if v not in valid:
            raise ValueError(f"qos_durability must be one of {valid}")
        return v


class GazeboConfig(BaseModel):
    """Gazebo simulation configuration."""

    host: str = Field(
        default="localhost",
        description="Gazebo server host"
    )

    port: int = Field(
        default=11345,
        ge=1024,
        le=65535,
        description="Gazebo server port"
    )

    timeout: float = Field(
        default=5.0,
        gt=0,
        description="Service call timeout (seconds)"
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum connection retry attempts"
    )

    retry_delay: float = Field(
        default=1.0,
        gt=0,
        description="Delay between retries (seconds)"
    )

    physics_update_rate: float = Field(
        default=1000.0,
        gt=0,
        description="Physics update rate (Hz)"
    )

    real_time_factor: float = Field(
        default=1.0,
        gt=0,
        description="Simulation real-time factor"
    )


class MCPServerConfig(BaseModel):
    """MCP server configuration."""

    name: str = Field(
        default="gazebo-mcp-server",
        description="Server name"
    )

    version: str = Field(
        default="1.0.0",
        description="Server version"
    )

    protocol: str = Field(
        default="stdio",
        description="MCP protocol (stdio/http)"
    )

    http_host: Optional[str] = Field(
        default="127.0.0.1",
        description="HTTP server host (if protocol=http)"
    )

    http_port: Optional[int] = Field(
        default=8080,
        ge=1024,
        le=65535,
        description="HTTP server port (if protocol=http)"
    )

    max_concurrent_requests: int = Field(
        default=10,
        ge=1,
        description="Maximum concurrent MCP requests"
    )

    request_timeout: float = Field(
        default=30.0,
        gt=0,
        description="MCP request timeout (seconds)"
    )

    @validator("protocol")
    def validate_protocol(cls, v):
        """Validate MCP protocol."""
        valid = ["stdio", "http"]
        if v not in valid:
            raise ValueError(f"protocol must be one of {valid}")
        return v


class PerformanceConfig(BaseModel):
    """Performance and resource configuration."""

    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling"
    )

    enable_metrics: bool = Field(
        default=True,
        description="Enable metrics collection"
    )

    cache_size: int = Field(
        default=1000,
        ge=0,
        description="Cache size for sensor data"
    )

    cache_ttl: float = Field(
        default=1.0,
        gt=0,
        description="Cache TTL (seconds)"
    )

    max_memory_mb: Optional[int] = Field(
        default=None,
        ge=100,
        description="Maximum memory usage (MB)"
    )

    thread_pool_size: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Thread pool size for async operations"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level"
    )

    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )

    file: Optional[Path] = Field(
        default=None,
        description="Log file path (None for stdout only)"
    )

    max_file_size_mb: int = Field(
        default=10,
        ge=1,
        description="Maximum log file size (MB)"
    )

    backup_count: int = Field(
        default=5,
        ge=0,
        description="Number of log file backups"
    )

    log_ros2_messages: bool = Field(
        default=False,
        description="Log all ROS2 messages (verbose)"
    )


class GazeboMCPConfig(BaseSettings):
    """
    Main configuration for Gazebo MCP Server.

    Supports loading from:
    - YAML configuration files
    - Environment variables (prefixed with GAZEBO_MCP_)
    - Default values
    """

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment"
    )

    ros2: ROS2Config = Field(
        default_factory=ROS2Config,
        description="ROS2 configuration"
    )

    gazebo: GazeboConfig = Field(
        default_factory=GazeboConfig,
        description="Gazebo configuration"
    )

    server: MCPServerConfig = Field(
        default_factory=MCPServerConfig,
        description="MCP server configuration"
    )

    performance: PerformanceConfig = Field(
        default_factory=PerformanceConfig,
        description="Performance configuration"
    )

    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )

    class Config:
        """Pydantic configuration."""
        env_prefix = "GAZEBO_MCP_"
        env_nested_delimiter = "__"
        case_sensitive = False

    @classmethod
    def from_yaml(cls, path: Path) -> "GazeboMCPConfig":
        """
        Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            GazeboMCPConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return cls(**data)

    @classmethod
    def from_env(cls, env: Optional[Environment] = None) -> "GazeboMCPConfig":
        """
        Load configuration for specific environment.

        Searches for config files in order:
        1. config/{env}.yaml
        2. config/default.yaml
        3. Default values

        Args:
            env: Environment to load (defaults to GAZEBO_MCP_ENVIRONMENT)

        Returns:
            GazeboMCPConfig instance
        """
        # Get environment from parameter or environment variable
        if env is None:
            env_str = os.getenv("GAZEBO_MCP_ENVIRONMENT", "development")
            env = Environment(env_str)

        # Try environment-specific config
        config_dir = Path(__file__).parent.parent.parent / "config"
        env_config = config_dir / f"{env.value}.yaml"

        if env_config.exists():
            return cls.from_yaml(env_config)

        # Fall back to default config
        default_config = config_dir / "default.yaml"
        if default_config.exists():
            return cls.from_yaml(default_config)

        # Use defaults
        return cls(environment=env)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of config
        """
        return self.dict()

    def to_yaml(self, path: Path) -> None:
        """
        Save configuration to YAML file.

        Args:
            path: Output file path
        """
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)


# Global configuration instance
_config: Optional[GazeboMCPConfig] = None


def get_config() -> GazeboMCPConfig:
    """
    Get global configuration instance.

    Lazily loads configuration on first access.

    Returns:
        GazeboMCPConfig instance
    """
    global _config
    if _config is None:
        _config = GazeboMCPConfig.from_env()
    return _config


def set_config(config: GazeboMCPConfig) -> None:
    """
    Set global configuration instance.

    Useful for testing or programmatic configuration.

    Args:
        config: Configuration to use
    """
    global _config
    _config = config


def reload_config(env: Optional[Environment] = None) -> GazeboMCPConfig:
    """
    Reload configuration from files/environment.

    Args:
        env: Environment to load (optional)

    Returns:
        Reloaded configuration
    """
    global _config
    _config = GazeboMCPConfig.from_env(env)
    return _config

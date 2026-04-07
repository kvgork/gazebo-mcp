"""
Structured Logging for Gazebo MCP.

Provides consistent logging across the MCP server with context-aware
formatting, different log levels, and integration with ROS2 logging.

Features:
- Structured logging with context (operation, model, sensor, etc.)
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- JSON formatting for machine parsing
- Integration with ROS2 logging when available
- Performance tracking (timing operations)
"""

import logging
import sys
import json
import time
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager


# Configure root logger:
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)  # Log to stderr (stdout reserved for MCP protocol)
    ]
)


class GazeboMCPLogger:
    """
    Structured logger for Gazebo MCP operations.

    Provides context-aware logging with optional JSON formatting
    and ROS2 integration.

    Example:
        >>> logger = get_logger("model_management")
        >>> logger.info("Spawning model", model_name="turtlebot3", position={"x": 1, "y": 2})
        >>> # Output: 2024-11-16 12:00:00 - model_management - INFO - Spawning model [model_name=turtlebot3]
        >>>
        >>> with logger.operation("spawn_model"):
        ...     # Do work
        ...     pass
        >>> # Output: Operation 'spawn_model' completed in 0.123s
    """

    def __init__(
        self,
        name: str,
        log_level: int = logging.INFO,
        json_format: bool = False,
        log_file: Optional[str] = None
    ):
        """
        Initialize logger.

        Args:
            name: Logger name (e.g., "model_management", "sensor_tools")
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            json_format: Use JSON formatting for structured logs
            log_file: Optional file path for log output
        """
        self.name = name
        self.logger = logging.getLogger(f"gazebo_mcp.{name}")
        self.logger.setLevel(log_level)
        self.json_format = json_format

        # Add file handler if specified:
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)

            if json_format:
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))

            self.logger.addHandler(file_handler)

    def _format_context(self, **context) -> str:
        """Format context dictionary for logging."""
        if not context:
            return ""

        if self.json_format:
            return json.dumps(context)
        else:
            items = [f"{k}={v}" for k, v in context.items()]
            return f" [{', '.join(items)}]"

    def debug(self, message: str, **context):
        """Log debug message with context."""
        ctx = self._format_context(**context)
        self.logger.debug(f"{message}{ctx}")

    def info(self, message: str, **context):
        """Log info message with context."""
        ctx = self._format_context(**context)
        self.logger.info(f"{message}{ctx}")

    def warning(self, message: str, **context):
        """Log warning message with context."""
        ctx = self._format_context(**context)
        self.logger.warning(f"{message}{ctx}")

    def error(self, message: str, **context):
        """Log error message with context."""
        ctx = self._format_context(**context)
        self.logger.error(f"{message}{ctx}")

    def critical(self, message: str, **context):
        """Log critical message with context."""
        ctx = self._format_context(**context)
        self.logger.critical(f"{message}{ctx}")

    def exception(self, message: str, exc_info=True, **context):
        """Log exception with stack trace and context."""
        ctx = self._format_context(**context)
        self.logger.exception(f"{message}{ctx}", exc_info=exc_info)

    @contextmanager
    def operation(self, operation_name: str, **context):
        """
        Context manager for timing operations.

        Example:
            >>> with logger.operation("spawn_model", model="turtlebot3"):
            ...     # Do work
            ...     pass
            >>> # Logs: "Operation 'spawn_model' completed in 0.123s [model=turtlebot3]"
        """
        start_time = time.time()
        self.debug(f"Starting operation '{operation_name}'", **context)

        try:
            yield
            duration = time.time() - start_time
            self.info(
                f"Operation '{operation_name}' completed",
                duration_sec=f"{duration:.3f}",
                **context
            )

        except Exception as e:
            duration = time.time() - start_time
            self.error(
                f"Operation '{operation_name}' failed",
                error=str(e),
                duration_sec=f"{duration:.3f}",
                **context
            )
            raise

    def log_ros2_connection(self, status: str, **details):
        """Log ROS2 connection event."""
        if status == "connected":
            self.info("ROS2 connection established", **details)
        elif status == "disconnected":
            self.warning("ROS2 connection lost", **details)
        elif status == "reconnecting":
            self.info("Attempting ROS2 reconnection", **details)
        else:
            self.debug(f"ROS2 status: {status}", **details)

    def log_model_event(self, event: str, model_name: str, **details):
        """Log model-related event."""
        self.info(f"Model {event}", model_name=model_name, **details)

    def log_sensor_event(self, event: str, sensor_name: str, **details):
        """Log sensor-related event."""
        self.info(f"Sensor {event}", sensor_name=sensor_name, **details)

    def log_world_event(self, event: str, world_name: str, **details):
        """Log world-related event."""
        self.info(f"World {event}", world_name=world_name, **details)


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs log records as JSON for easy parsing by log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception info if present:
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra context if present:
        if hasattr(record, "context"):
            log_data["context"] = record.context

        return json.dumps(log_data)


# Global logger registry:
_loggers: Dict[str, GazeboMCPLogger] = {}


def get_logger(
    name: str,
    log_level: Optional[int] = None,
    json_format: bool = False,
    log_file: Optional[str] = None
) -> GazeboMCPLogger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name
        log_level: Optional log level (defaults to INFO)
        json_format: Use JSON formatting
        log_file: Optional log file path

    Returns:
        GazeboMCPLogger instance

    Example:
        >>> logger = get_logger("model_management")
        >>> logger.info("Model spawned", model_name="turtlebot3")
    """
    if name not in _loggers:
        _loggers[name] = GazeboMCPLogger(
            name=name,
            log_level=log_level or logging.INFO,
            json_format=json_format,
            log_file=log_file
        )

    return _loggers[name]


def set_global_log_level(level: int):
    """
    Set log level for all existing loggers.

    Args:
        level: Logging level (logging.DEBUG, logging.INFO, etc.)

    Example:
        >>> set_global_log_level(logging.DEBUG)  # Enable debug logging
    """
    for logger in _loggers.values():
        logger.logger.setLevel(level)


def configure_file_logging(log_dir: str, json_format: bool = False):
    """
    Configure file logging for all loggers.

    Args:
        log_dir: Directory for log files
        json_format: Use JSON formatting

    Example:
        >>> configure_file_logging("/var/log/gazebo_mcp", json_format=True)
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create log file with timestamp:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"gazebo_mcp_{timestamp}.log"

    # Update all existing loggers:
    for logger in _loggers.values():
        file_handler = logging.FileHandler(str(log_file))

        if json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))

        logger.logger.addHandler(file_handler)


# Convenience function for timing code blocks:
@contextmanager
def timed_operation(logger: GazeboMCPLogger, operation_name: str, **context):
    """
    Convenience context manager for timing operations.

    Args:
        logger: Logger instance
        operation_name: Name of the operation
        **context: Additional context to log

    Example:
        >>> logger = get_logger("model_management")
        >>> with timed_operation(logger, "spawn_model", model="turtlebot3"):
        ...     # Do work
        ...     pass
    """
    with logger.operation(operation_name, **context):
        yield


# Example usage:
if __name__ == "__main__":
    # Basic logging:
    logger = get_logger("example")
    logger.info("Server starting", port=8080, mode="stdio")

    # Operation timing:
    with logger.operation("test_operation", test_param="value"):
        time.sleep(0.1)

    # Model events:
    logger.log_model_event("spawned", "turtlebot3", position={"x": 1, "y": 2})

    # Error logging:
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.exception("Operation failed", operation="test")

    # JSON formatting:
    json_logger = get_logger("json_example", json_format=True)
    json_logger.info("Structured log", key="value", count=42)

"""
Performance Profiling Decorators for Gazebo MCP Tools.

Provides decorators for automatic performance profiling of MCP tools:
- Execution time tracking
- Memory usage monitoring
- Token efficiency calculation
- Automatic metrics recording

Example:
    >>> from gazebo_mcp.utils.profiler import profile_tool
    >>>
    >>> @profile_tool
    >>> def my_tool(arg1, arg2):
    ...     # Tool implementation
    ...     return result
"""

import time
import functools
import sys
from typing import Callable, Any
from .metrics import get_metrics_collector
from .logger import get_logger
from .result import OperationResult


_logger = get_logger("profiler")


def profile_tool(func: Callable) -> Callable:
    """
    Decorator to profile MCP tool execution.

    Automatically tracks:
    - Execution duration
    - Success/failure status
    - Token efficiency (if result contains token info)

    Args:
        func: Tool function to profile

    Returns:
        Wrapped function with profiling

    Example:
        >>> @profile_tool
        >>> def list_models(response_format="filtered"):
        ...     # Implementation
        ...     return success_result(data)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> OperationResult:
        # Get metrics collector:
        metrics = get_metrics_collector()

        # Start timing:
        start_time = time.time()
        start_memory = _get_memory_usage()

        # Execute function:
        try:
            result = func(*args, **kwargs)
            success = result.success if isinstance(result, OperationResult) else True
        except Exception as e:
            success = False
            _logger.error(f"Error in {func.__name__}: {e}")
            raise
        finally:
            # Calculate metrics:
            duration = time.time() - start_time
            end_memory = _get_memory_usage()
            memory_delta = end_memory - start_memory

            # Extract token info from result if available:
            tokens_sent = 0
            tokens_saved = 0

            if isinstance(result, OperationResult) and result.success:
                # Check if result has token efficiency data:
                if "tokens_saved" in result.data:
                    tokens_saved = result.data["tokens_saved"]
                if "tokens_sent" in result.data:
                    tokens_sent = result.data["tokens_sent"]

                # For list operations, estimate tokens:
                if "models" in result.data:
                    models = result.data["models"]
                    if isinstance(models, list):
                        # Estimate ~50 tokens per model if using filtered format:
                        tokens_sent = len(models) * 50

                        # Check if summary was used instead:
                        if result.data.get("response_format") == "summary":
                            tokens_sent = 100  # Much smaller
                            tokens_saved = (len(models) * 50) - tokens_sent

            # Record metrics:
            metrics.record_tool_call(
                tool_name=func.__name__,
                duration=duration,
                tokens_sent=tokens_sent,
                tokens_saved=tokens_saved,
                success=success
            )

            # Log if slow:
            if duration > 1.0:
                _logger.warning(
                    f"Slow tool execution: {func.__name__}",
                    duration=f"{duration:.3f}s",
                    memory_delta_mb=f"{memory_delta:.2f}"
                )

        return result

    return wrapper


def profile_async_tool(func: Callable) -> Callable:
    """
    Decorator to profile async MCP tool execution.

    Similar to profile_tool but for async functions.

    Args:
        func: Async tool function to profile

    Returns:
        Wrapped async function with profiling

    Example:
        >>> @profile_async_tool
        >>> async def async_tool():
        ...     result = await some_operation()
        ...     return result
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get metrics collector:
        metrics = get_metrics_collector()

        # Start timing:
        start_time = time.time()

        # Execute function:
        try:
            result = await func(*args, **kwargs)
            success = result.success if isinstance(result, OperationResult) else True
        except Exception as e:
            success = False
            _logger.error(f"Error in {func.__name__}: {e}")
            raise
        finally:
            # Calculate metrics:
            duration = time.time() - start_time

            # Record metrics:
            metrics.record_tool_call(
                tool_name=func.__name__,
                duration=duration,
                success=success
            )

        return result

    return wrapper


def _get_memory_usage() -> float:
    """
    Get current memory usage in MB.

    Returns:
        Memory usage in megabytes
    """
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert to MB
    except ImportError:
        # psutil not available, return 0:
        return 0.0
    except Exception:
        return 0.0


class ProfileContext:
    """
    Context manager for profiling code blocks.

    Example:
        >>> with ProfileContext("complex_operation") as prof:
        ...     # Do complex work
        ...     result = expensive_function()
        >>> print(f"Operation took {prof.duration:.3f}s")
    """

    def __init__(self, operation_name: str):
        """
        Initialize profiling context.

        Args:
            operation_name: Name of operation being profiled
        """
        self.operation_name = operation_name
        self.start_time = 0.0
        self.duration = 0.0
        self._logger = get_logger("profiler")

    def __enter__(self):
        """Start profiling."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop profiling and record metrics."""
        self.duration = time.time() - self.start_time

        # Get metrics collector:
        metrics = get_metrics_collector()

        # Record as a tool call:
        success = exc_type is None
        metrics.record_tool_call(
            tool_name=self.operation_name,
            duration=self.duration,
            success=success
        )

        # Log if slow:
        if self.duration > 1.0:
            self._logger.warning(
                f"Slow operation: {self.operation_name}",
                duration=f"{self.duration:.3f}s"
            )

        return False  # Don't suppress exceptions

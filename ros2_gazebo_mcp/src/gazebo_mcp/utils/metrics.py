"""
Performance Metrics Collection for Gazebo MCP Server.

Tracks tool execution metrics, response times, errors, and token efficiency.
Supports Prometheus export format for monitoring dashboards.

Example:
    >>> from gazebo_mcp.utils.metrics import get_metrics_collector
    >>> metrics = get_metrics_collector()
    >>> metrics.record_tool_call("gazebo_list_models", duration=0.15, tokens_sent=500, tokens_saved=49500)
    >>> summary = metrics.get_summary()
    >>> print(f"Total tool calls: {summary['total_calls']}")
"""

import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from .logger import get_logger


@dataclass
class ToolMetrics:
    """Metrics for a single tool."""
    name: str
    call_count: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    error_count: int = 0
    total_tokens_sent: int = 0
    total_tokens_saved: int = 0
    last_called: Optional[datetime] = None


@dataclass
class ErrorMetrics:
    """Metrics for errors."""
    error_type: str
    count: int = 0
    last_occurred: Optional[datetime] = None
    last_message: str = ""


class MetricsCollector:
    """
    Collect and report performance metrics for MCP tools.

    Thread-safe metrics collection with support for:
    - Tool call counts and response times
    - Error tracking by type
    - Token efficiency measurements
    - Prometheus export format

    Example:
        >>> metrics = MetricsCollector()
        >>> metrics.record_tool_call("my_tool", duration=0.5, tokens_sent=1000, tokens_saved=9000)
        >>> summary = metrics.get_summary()
        >>> print(summary)
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._logger = get_logger("metrics")
        self._lock = threading.Lock()

        # Tool metrics:
        self._tool_metrics: Dict[str, ToolMetrics] = {}

        # Error metrics:
        self._error_metrics: Dict[str, ErrorMetrics] = {}

        # Global counters:
        self._start_time = datetime.now()
        self._total_calls = 0
        self._total_errors = 0
        self._total_tokens_saved = 0

        self._logger.info("Initialized metrics collector")

    def record_tool_call(
        self,
        tool_name: str,
        duration: float,
        tokens_sent: int = 0,
        tokens_saved: int = 0,
        success: bool = True
    ) -> None:
        """
        Record metrics for a tool call.

        Args:
            tool_name: Name of the tool
            duration: Execution duration in seconds
            tokens_sent: Number of tokens sent in response
            tokens_saved: Number of tokens saved via optimization
            success: Whether the call succeeded
        """
        with self._lock:
            # Get or create tool metrics:
            if tool_name not in self._tool_metrics:
                self._tool_metrics[tool_name] = ToolMetrics(name=tool_name)

            metrics = self._tool_metrics[tool_name]

            # Update metrics:
            metrics.call_count += 1
            metrics.total_duration += duration
            metrics.min_duration = min(metrics.min_duration, duration)
            metrics.max_duration = max(metrics.max_duration, duration)
            metrics.total_tokens_sent += tokens_sent
            metrics.total_tokens_saved += tokens_saved
            metrics.last_called = datetime.now()

            if not success:
                metrics.error_count += 1
                self._total_errors += 1

            # Update global counters:
            self._total_calls += 1
            self._total_tokens_saved += tokens_saved

    def record_error(
        self,
        error_type: str,
        error_message: str = ""
    ) -> None:
        """
        Record an error occurrence.

        Args:
            error_type: Type/category of error
            error_message: Error message
        """
        with self._lock:
            # Get or create error metrics:
            if error_type not in self._error_metrics:
                self._error_metrics[error_type] = ErrorMetrics(error_type=error_type)

            error = self._error_metrics[error_type]
            error.count += 1
            error.last_occurred = datetime.now()
            error.last_message = error_message

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all metrics.

        Returns:
            Dictionary with metrics summary
        """
        with self._lock:
            uptime = (datetime.now() - self._start_time).total_seconds()

            # Calculate average response time:
            total_duration = sum(m.total_duration for m in self._tool_metrics.values())
            avg_response_time = total_duration / self._total_calls if self._total_calls > 0 else 0

            # Calculate token efficiency:
            total_tokens = sum(m.total_tokens_sent for m in self._tool_metrics.values())
            potential_tokens = total_tokens + self._total_tokens_saved
            efficiency = (self._total_tokens_saved / potential_tokens * 100) if potential_tokens > 0 else 0

            # Get top tools by call count:
            top_tools = sorted(
                self._tool_metrics.values(),
                key=lambda m: m.call_count,
                reverse=True
            )[:5]

            return {
                "uptime_seconds": uptime,
                "total_calls": self._total_calls,
                "total_errors": self._total_errors,
                "error_rate": (self._total_errors / self._total_calls * 100) if self._total_calls > 0 else 0,
                "avg_response_time": avg_response_time,
                "total_tokens_sent": total_tokens,
                "total_tokens_saved": self._total_tokens_saved,
                "token_efficiency_percent": efficiency,
                "tools_count": len(self._tool_metrics),
                "top_tools": [
                    {
                        "name": t.name,
                        "calls": t.call_count,
                        "avg_duration": t.total_duration / t.call_count if t.call_count > 0 else 0
                    }
                    for t in top_tools
                ],
                "error_types_count": len(self._error_metrics)
            }

    def get_tool_metrics(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool metrics dictionary or None if not found
        """
        with self._lock:
            if tool_name not in self._tool_metrics:
                return None

            metrics = self._tool_metrics[tool_name]
            avg_duration = metrics.total_duration / metrics.call_count if metrics.call_count > 0 else 0

            return {
                "name": metrics.name,
                "call_count": metrics.call_count,
                "error_count": metrics.error_count,
                "avg_duration": avg_duration,
                "min_duration": metrics.min_duration if metrics.min_duration != float('inf') else 0,
                "max_duration": metrics.max_duration,
                "total_tokens_sent": metrics.total_tokens_sent,
                "total_tokens_saved": metrics.total_tokens_saved,
                "last_called": metrics.last_called.isoformat() if metrics.last_called else None
            }

    def get_all_tool_metrics(self) -> List[Dict[str, Any]]:
        """
        Get metrics for all tools.

        Returns:
            List of tool metrics dictionaries
        """
        with self._lock:
            return [
                self.get_tool_metrics(name)
                for name in sorted(self._tool_metrics.keys())
            ]

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string

        Example:
            >>> metrics = collector.export_prometheus()
            >>> # Save to file for Prometheus scraping:
            >>> with open('/var/metrics/gazebo_mcp.prom', 'w') as f:
            ...     f.write(metrics)
        """
        with self._lock:
            lines = []

            # Header:
            lines.append("# HELP gazebo_mcp_tool_calls_total Total number of tool calls")
            lines.append("# TYPE gazebo_mcp_tool_calls_total counter")

            for tool_name, metrics in self._tool_metrics.items():
                lines.append(f'gazebo_mcp_tool_calls_total{{tool="{tool_name}"}} {metrics.call_count}')

            lines.append("")

            # Response times:
            lines.append("# HELP gazebo_mcp_tool_duration_seconds Tool execution duration")
            lines.append("# TYPE gazebo_mcp_tool_duration_seconds gauge")

            for tool_name, metrics in self._tool_metrics.items():
                avg = metrics.total_duration / metrics.call_count if metrics.call_count > 0 else 0
                lines.append(f'gazebo_mcp_tool_duration_seconds{{tool="{tool_name}",stat="avg"}} {avg:.6f}')
                lines.append(f'gazebo_mcp_tool_duration_seconds{{tool="{tool_name}",stat="min"}} {metrics.min_duration:.6f}')
                lines.append(f'gazebo_mcp_tool_duration_seconds{{tool="{tool_name}",stat="max"}} {metrics.max_duration:.6f}')

            lines.append("")

            # Errors:
            lines.append("# HELP gazebo_mcp_tool_errors_total Total number of tool errors")
            lines.append("# TYPE gazebo_mcp_tool_errors_total counter")

            for tool_name, metrics in self._tool_metrics.items():
                lines.append(f'gazebo_mcp_tool_errors_total{{tool="{tool_name}"}} {metrics.error_count}')

            lines.append("")

            # Token efficiency:
            lines.append("# HELP gazebo_mcp_tokens_saved_total Total tokens saved via optimization")
            lines.append("# TYPE gazebo_mcp_tokens_saved_total counter")
            lines.append(f"gazebo_mcp_tokens_saved_total {self._total_tokens_saved}")

            lines.append("")

            return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._tool_metrics.clear()
            self._error_metrics.clear()
            self._start_time = datetime.now()
            self._total_calls = 0
            self._total_errors = 0
            self._total_tokens_saved = 0
            self._logger.info("Metrics reset")


# Global metrics collector instance (singleton):
_metrics_collector: Optional[MetricsCollector] = None
_collector_lock = threading.Lock()


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance (singleton).

    Returns:
        MetricsCollector instance
    """
    global _metrics_collector

    if _metrics_collector is None:
        with _collector_lock:
            if _metrics_collector is None:
                _metrics_collector = MetricsCollector()

    return _metrics_collector


def reset_metrics() -> None:
    """Reset the global metrics collector."""
    collector = get_metrics_collector()
    collector.reset()

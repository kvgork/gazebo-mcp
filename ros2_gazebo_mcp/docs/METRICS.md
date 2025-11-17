# Performance Metrics and Monitoring

The Gazebo MCP Server includes built-in performance monitoring to track tool usage, response times, errors, and token efficiency.

## Overview

Metrics are automatically collected for:
- **Tool call counts** - How many times each tool is called
- **Response times** - Min, max, and average execution duration
- **Token efficiency** - Tokens sent vs. tokens saved via optimization
- **Error tracking** - Error counts by type and tool
- **Server uptime** - How long the server has been running

## Quick Start

### View Current Metrics

```bash
# Show summary
python scripts/show_metrics.py

# Show detailed metrics for all tools
python scripts/show_metrics.py --detailed

# Export to Prometheus format
python scripts/show_metrics.py --export metrics.prom --format prometheus

# Export to JSON
python scripts/show_metrics.py --export metrics.json --format json
```

### Example Output

```
======================================================================
  MCP Server Performance Summary
======================================================================

Uptime: 120.5 seconds

Total Tool Calls: 45
Total Errors: 2
Error Rate: 4.44%

Average Response Time: 125.3ms

Token Efficiency:
  Tokens Sent: 12,500
  Tokens Saved: 237,500
  Efficiency: 95.0%

Top 5 Most Used Tools:
  1. gazebo_list_models
     Calls: 15
     Avg Duration: 95.2ms
  2. gazebo_get_model_state
     Calls: 12
     Avg Duration: 50.1ms
  3. gazebo_spawn_model
     Calls: 8
     Avg Duration: 320.5ms
```

## Metrics Collection

### Automatic Collection

Metrics are automatically collected by the MCP server for every tool call. No configuration required!

```python
# Metrics are collected automatically when calling tools:
result = server.call_tool("gazebo_list_models", {"response_format": "summary"})
# Metrics recorded: duration, tokens, success/failure
```

### Manual Metrics Access

```python
from gazebo_mcp.utils.metrics import get_metrics_collector

# Get metrics collector instance:
metrics = get_metrics_collector()

# Get summary:
summary = metrics.get_summary()
print(f"Total calls: {summary['total_calls']}")
print(f"Token efficiency: {summary['token_efficiency_percent']:.1f}%")

# Get metrics for specific tool:
tool_metrics = metrics.get_tool_metrics("gazebo_list_models")
if tool_metrics:
    print(f"Average duration: {tool_metrics['avg_duration']:.3f}s")
    print(f"Tokens saved: {tool_metrics['total_tokens_saved']}")

# Get all tool metrics:
all_metrics = metrics.get_all_tool_metrics()
for tool in all_metrics:
    print(f"{tool['name']}: {tool['call_count']} calls")
```

## Profiling Decorator

For custom tools or functions, use the `@profile_tool` decorator:

```python
from gazebo_mcp.utils.profiler import profile_tool

@profile_tool
def my_custom_tool(arg1, arg2):
    """Custom tool with automatic profiling."""
    # Implementation
    return result

# Metrics automatically collected:
# - Execution time
# - Success/failure
# - Token usage (if result contains token info)
```

## Token Efficiency Tracking

The metrics system automatically tracks token efficiency for operations that use the ResultFilter pattern:

```python
# Using summary format (high efficiency):
result = server.call_tool("gazebo_list_models", {
    "response_format": "summary"
})
# Metrics: tokens_sent=110, tokens_saved=24,890 (99.5% efficiency)

# Using filtered format (full details):
result = server.call_tool("gazebo_list_models", {
    "response_format": "filtered"
})
# Metrics: tokens_sent=25,000, tokens_saved=0 (0% efficiency)
```

### How Token Estimation Works

The server estimates tokens based on:
1. **Explicit token info** in result data (if available)
2. **Response format** (summary vs. filtered)
3. **Data size** (number of models, sensors, etc.)
4. **JSON payload size** (rough estimate: 4 chars per token)

**Estimation formulas:**
- **Summary format**: ~100 tokens + (count × 2 tokens per item name)
- **Filtered format**: count × 50 tokens per full item
- **Simple operations**: JSON size ÷ 4

## Prometheus Export

Export metrics for Prometheus monitoring:

```bash
# Export to file:
python scripts/show_metrics.py --export /var/metrics/gazebo_mcp.prom --format prometheus

# Add to Prometheus configuration:
# prometheus.yml:
#   - job_name: 'gazebo_mcp'
#     static_configs:
#       - targets: ['localhost:9090']
#     file_sd_configs:
#       - files:
#         - /var/metrics/gazebo_mcp.prom
```

### Prometheus Metrics

Exported metrics include:

```prometheus
# Total tool calls
gazebo_mcp_tool_calls_total{tool="gazebo_list_models"} 45

# Response times (avg, min, max)
gazebo_mcp_tool_duration_seconds{tool="gazebo_list_models",stat="avg"} 0.095200
gazebo_mcp_tool_duration_seconds{tool="gazebo_list_models",stat="min"} 0.050100
gazebo_mcp_tool_duration_seconds{tool="gazebo_list_models",stat="max"} 0.250300

# Error counts
gazebo_mcp_tool_errors_total{tool="gazebo_list_models"} 2

# Token efficiency
gazebo_mcp_tokens_saved_total 237500
```

## Performance Monitoring Best Practices

### 1. Monitor Response Times

Watch for slow operations:

```python
from gazebo_mcp.utils.profiler import ProfileContext

with ProfileContext("complex_operation") as prof:
    # Do work
    result = expensive_function()

if prof.duration > 1.0:
    print(f"WARNING: Slow operation ({prof.duration:.2f}s)")
```

### 2. Track Error Rates

```python
summary = metrics.get_summary()
if summary['error_rate'] > 10.0:  # More than 10% errors
    print("HIGH ERROR RATE - investigate!")
```

### 3. Monitor Token Efficiency

```python
summary = metrics.get_summary()
efficiency = summary['token_efficiency_percent']

if efficiency < 80.0:
    print("LOW TOKEN EFFICIENCY - consider using summary format")
```

### 4. Reset Metrics

For testing or benchmarking:

```python
from gazebo_mcp.utils.metrics import reset_metrics

# Reset all metrics to zero:
reset_metrics()

# Now run your test
# Metrics will be collected fresh
```

## Production Monitoring

### Grafana Dashboard

Create a Grafana dashboard using Prometheus data source:

**Panels to include:**
1. **Tool Call Rate** - Calls per second
2. **Average Response Time** - By tool
3. **Error Rate** - Percentage over time
4. **Token Efficiency** - Savings percentage
5. **Top Tools** - Most frequently called

### Alerts

Set up alerts for:
- **High error rate** (>5%)
- **Slow response times** (>1s average)
- **Low token efficiency** (<70%)

```yaml
# Example Prometheus alert rule:
groups:
  - name: gazebo_mcp_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(gazebo_mcp_tool_errors_total[5m]) > 0.05
        annotations:
          summary: "MCP server error rate above 5%"

      - alert: SlowResponseTime
        expr: gazebo_mcp_tool_duration_seconds{stat="avg"} > 1.0
        annotations:
          summary: "MCP tool response time >1s"
```

## Metrics API Reference

### MetricsCollector Class

```python
class MetricsCollector:
    """Collect and report performance metrics."""

    def record_tool_call(
        tool_name: str,
        duration: float,
        tokens_sent: int = 0,
        tokens_saved: int = 0,
        success: bool = True
    ) -> None:
        """Record metrics for a tool call."""

    def record_error(
        error_type: str,
        error_message: str = ""
    ) -> None:
        """Record an error occurrence."""

    def get_summary() -> Dict[str, Any]:
        """Get summary of all metrics."""

    def get_tool_metrics(tool_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific tool."""

    def get_all_tool_metrics() -> List[Dict[str, Any]]:
        """Get metrics for all tools."""

    def export_prometheus() -> str:
        """Export in Prometheus format."""

    def reset() -> None:
        """Reset all metrics."""
```

### Summary Response Format

```python
{
    "uptime_seconds": 120.5,
    "total_calls": 45,
    "total_errors": 2,
    "error_rate": 4.44,
    "avg_response_time": 0.1253,
    "total_tokens_sent": 12500,
    "total_tokens_saved": 237500,
    "token_efficiency_percent": 95.0,
    "tools_count": 18,
    "top_tools": [
        {
            "name": "gazebo_list_models",
            "calls": 15,
            "avg_duration": 0.0952
        }
    ],
    "error_types_count": 2
}
```

### Tool Metrics Response Format

```python
{
    "name": "gazebo_list_models",
    "call_count": 15,
    "error_count": 0,
    "avg_duration": 0.0952,
    "min_duration": 0.0501,
    "max_duration": 0.2503,
    "total_tokens_sent": 2110,
    "total_tokens_saved": 47890,
    "last_called": "2025-11-16T18:30:45.123456"
}
```

## Troubleshooting

### No Metrics Collected

**Problem**: `show_metrics.py` shows "No metrics collected yet"

**Solutions:**
1. Ensure MCP server has been run and used
2. Check that metrics are being recorded in server logs
3. Verify metrics collector is initialized

### Inaccurate Token Estimates

**Problem**: Token counts seem wrong

**Explanation:** Tokens are estimated, not precisely measured. Estimates are based on:
- Known patterns for summary vs. filtered formats
- JSON payload size heuristics
- Typical token-to-character ratios

**To improve:**
- Use explicit token tracking in tool functions
- Calibrate estimates based on actual Claude usage
- Focus on relative efficiency (summary vs. filtered) rather than absolute numbers

### High Memory Usage

**Problem**: Metrics consuming too much memory

**Solution:** Reset metrics periodically:

```python
# Reset metrics after collecting/exporting:
metrics = get_metrics_collector()
metrics.export_prometheus("/var/metrics/gazebo_mcp.prom")
metrics.reset()  # Clear accumulated data
```

## See Also

- [MCP Server Guide](../mcp/README.md) - Complete MCP documentation
- [Examples](../examples/README.md) - Usage examples with metrics
- [Architecture](ARCHITECTURE.md) - System design

---

**Last Updated**: 2025-11-16

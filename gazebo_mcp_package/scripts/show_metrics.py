#!/usr/bin/env python3
"""
Show MCP Server Performance Metrics.

Displays metrics collected during MCP server operation:
- Tool usage statistics
- Response times
- Token efficiency
- Error rates

This script accesses the metrics from a running or recently run MCP server instance.

Usage:
    python scripts/show_metrics.py
    python scripts/show_metrics.py --format prometheus
    python scripts/show_metrics.py --export metrics.prom
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any

# Add project to path:
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.utils.metrics import get_metrics_collector


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def format_duration(seconds: float) -> str:
    """Format duration in a human-readable way."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.0f}µs"
    elif seconds < 1.0:
        return f"{seconds * 1000:.1f}ms"
    else:
        return f"{seconds:.3f}s"


def format_number(num: int) -> str:
    """Format large numbers with comma separators."""
    return f"{num:,}"


def show_summary(metrics):
    """Show metrics summary."""
    summary = metrics.get_summary()

    print_section("MCP Server Performance Summary")

    print(f"\nUptime: {summary['uptime_seconds']:.1f} seconds")
    print(f"\nTotal Tool Calls: {format_number(summary['total_calls'])}")
    print(f"Total Errors: {format_number(summary['total_errors'])}")
    print(f"Error Rate: {summary['error_rate']:.2f}%")
    print(f"\nAverage Response Time: {format_duration(summary['avg_response_time'])}")

    print(f"\nToken Efficiency:")
    print(f"  Tokens Sent: {format_number(summary['total_tokens_sent'])}")
    print(f"  Tokens Saved: {format_number(summary['total_tokens_saved'])}")
    print(f"  Efficiency: {summary['token_efficiency_percent']:.1f}%")

    if summary['top_tools']:
        print(f"\nTop {len(summary['top_tools'])} Most Used Tools:")
        for i, tool in enumerate(summary['top_tools'], 1):
            print(f"  {i}. {tool['name']}")
            print(f"     Calls: {format_number(tool['calls'])}")
            print(f"     Avg Duration: {format_duration(tool['avg_duration'])}")


def show_detailed_metrics(metrics):
    """Show detailed metrics for all tools."""
    all_metrics = metrics.get_all_tool_metrics()

    if not all_metrics:
        print("\nNo metrics collected yet.")
        return

    print_section(f"Detailed Tool Metrics ({len(all_metrics)} tools)")

    for tool_metrics in all_metrics:
        if tool_metrics is None:
            continue

        print(f"\n{tool_metrics['name']}:")
        print(f"  Calls: {format_number(tool_metrics['call_count'])}")

        if tool_metrics['error_count'] > 0:
            error_rate = (tool_metrics['error_count'] / tool_metrics['call_count']) * 100
            print(f"  Errors: {tool_metrics['error_count']} ({error_rate:.1f}%)")

        print(f"  Response Times:")
        print(f"    Average: {format_duration(tool_metrics['avg_duration'])}")
        print(f"    Min: {format_duration(tool_metrics['min_duration'])}")
        print(f"    Max: {format_duration(tool_metrics['max_duration'])}")

        if tool_metrics['total_tokens_sent'] > 0 or tool_metrics['total_tokens_saved'] > 0:
            print(f"  Token Usage:")
            print(f"    Sent: {format_number(tool_metrics['total_tokens_sent'])}")
            print(f"    Saved: {format_number(tool_metrics['total_tokens_saved'])}")

            if tool_metrics['total_tokens_saved'] > 0:
                total = tool_metrics['total_tokens_sent'] + tool_metrics['total_tokens_saved']
                efficiency = (tool_metrics['total_tokens_saved'] / total) * 100
                print(f"    Efficiency: {efficiency:.1f}%")

        if tool_metrics['last_called']:
            print(f"  Last Called: {tool_metrics['last_called']}")


def export_prometheus(metrics, output_file: str):
    """Export metrics in Prometheus format."""
    prom_data = metrics.export_prometheus()

    with open(output_file, 'w') as f:
        f.write(prom_data)

    print(f"Metrics exported to {output_file}")
    print(f"File size: {len(prom_data)} bytes")


def export_json(metrics, output_file: str):
    """Export metrics as JSON."""
    data = {
        "summary": metrics.get_summary(),
        "tools": metrics.get_all_tool_metrics()
    }

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Metrics exported to {output_file} (JSON format)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Show MCP Server performance metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show summary
  python scripts/show_metrics.py

  # Show detailed metrics
  python scripts/show_metrics.py --detailed

  # Export to Prometheus format
  python scripts/show_metrics.py --export metrics.prom --format prometheus

  # Export to JSON
  python scripts/show_metrics.py --export metrics.json --format json
        """
    )

    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed metrics for all tools'
    )

    parser.add_argument(
        '--format',
        choices=['summary', 'detailed', 'prometheus', 'json'],
        default='summary',
        help='Output format (default: summary)'
    )

    parser.add_argument(
        '--export',
        type=str,
        metavar='FILE',
        help='Export metrics to file'
    )

    args = parser.parse_args()

    # Get metrics collector:
    metrics = get_metrics_collector()

    # Check if any metrics collected:
    summary = metrics.get_summary()
    if summary['total_calls'] == 0:
        print("No metrics collected yet.")
        print("\nTo collect metrics:")
        print("  1. Run the MCP server: python -m mcp.server.server")
        print("  2. Make some tool calls")
        print("  3. Run this script again")
        return

    # Handle export:
    if args.export:
        if args.format == 'prometheus' or args.export.endswith('.prom'):
            export_prometheus(metrics, args.export)
        elif args.format == 'json' or args.export.endswith('.json'):
            export_json(metrics, args.export)
        else:
            print(f"Error: Unknown export format for {args.export}")
            print("Use .prom for Prometheus or .json for JSON")
            sys.exit(1)
        return

    # Show metrics:
    if args.format == 'detailed' or args.detailed:
        show_summary(metrics)
        show_detailed_metrics(metrics)
    elif args.format == 'prometheus':
        print(metrics.export_prometheus())
    elif args.format == 'json':
        data = {
            "summary": metrics.get_summary(),
            "tools": metrics.get_all_tool_metrics()
        }
        print(json.dumps(data, indent=2))
    else:
        show_summary(metrics)

    print("\n" + "=" * 70)
    print()


if __name__ == "__main__":
    main()

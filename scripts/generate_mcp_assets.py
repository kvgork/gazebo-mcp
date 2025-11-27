#!/usr/bin/env python3
"""
MCP Asset Generation Automation.

Automatically generates MCP adapters and schemas for all Gazebo tools.
Uses the mcp_adapter_creator and mcp_schema_generator skills from claude/.

Usage:
    python3 scripts/generate_mcp_assets.py
    python3 scripts/generate_mcp_assets.py --validate-security

This saves 1-2 days of manual adapter/schema creation!
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Dict

# Add claude project to path:
# Use environment variable or relative path from project root
CLAUDE_ROOT = Path(os.environ.get("CLAUDE_ROOT", Path(__file__).parents[1] / "claude"))
if CLAUDE_ROOT.exists():
    sys.path.insert(0, str(CLAUDE_ROOT))

try:
    from skills.mcp_adapter_creator import create_adapter
    from skills.mcp_schema_generator import generate_schema, validate_schema
    from skills.mcp_security_validator import validate_server_security
    from skills.common.filters import ResultFilter
except ImportError as e:
    print(f"Error: Could not import MCP skills from claude/")
    print(f"  {e}")
    print(f"\nMake sure the claude/ directory exists.")
    print(f"Set CLAUDE_ROOT environment variable or place claude/ at: {CLAUDE_ROOT}")
    sys.exit(1)


# All Gazebo MCP operations to generate assets for:
OPERATIONS = {
    "Simulation Control (Phase 3)": [
        "start_simulation",
        "pause_simulation",
        "unpause_simulation",
        "reset_simulation",
        "stop_simulation",
        "get_simulation_state"
    ],
    "Model Management (Phase 3)": [
        "spawn_model",
        "delete_model",
        "list_models",
        "get_model_state",
        "set_model_state"
    ],
    "Sensor Tools (Phase 3)": [
        "list_sensors",
        "get_sensor_data",
        "subscribe_sensor"
    ],
    "World Generation (Phase 4)": [
        "create_world",
        "load_world",
        "save_world",
        "list_worlds"
    ],
    "Lighting Tools (Phase 4)": [
        "set_ambient_light",
        "add_light",
        "modify_light",
        "delete_light",
        "list_lights"
    ],
    "Terrain Tools (Phase 4)": [
        "create_terrain",
        "modify_terrain",
        "add_heightmap"
    ]
}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate MCP assets for Gazebo tools")
    parser.add_argument(
        "--validate-security",
        action="store_true",
        help="Run security validation after generation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("  MCP Asset Generation for ROS2 Gazebo")
    print("=" * 70)
    print()

    # Calculate total operations:
    total_ops = sum(len(ops) for ops in OPERATIONS.values())
    print(f"Generating assets for {total_ops} operations...\n")

    # Create output directories:
    project_root = Path(__file__).parents[1]
    adapters_dir = project_root / "src" / "gazebo_mcp" / "adapters"
    schema_dir = project_root / "src" / "gazebo_mcp" / "schema"

    if not args.dry_run:
        adapters_dir.mkdir(parents=True, exist_ok=True)
        schema_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directories:")
        print(f"  Adapters: {adapters_dir}")
        print(f"  Schemas:  {schema_dir}\n")

    # Generate for each category:
    current = 0
    stats = {
        "adapters_created": 0,
        "adapters_failed": 0,
        "schemas_created": 0,
        "schemas_failed": 0
    }

    for category, operations in OPERATIONS.items():
        print(f"\n{category}:")
        print("-" * 70)

        for op in operations:
            current += 1
            print(f"[{current}/{total_ops}] {op}... ", end="", flush=True)

            if args.dry_run:
                print("✓ (dry-run)")
                continue

            try:
                # Generate adapter:
                adapter_result = create_adapter(
                    f"gazebo_mcp.tools.{op}",
                    response_format="concise"
                )

                if adapter_result.success:
                    adapter_code = adapter_result.data.get('adapter_code', '')
                    adapter_path = adapters_dir / f"{op}.py"

                    with open(adapter_path, "w") as f:
                        f.write(adapter_code)

                    stats["adapters_created"] += 1
                else:
                    print(f"⚠ adapter failed: {adapter_result.error}")
                    stats["adapters_failed"] += 1
                    continue

                # Generate schema:
                schema_result = generate_schema(f"gazebo_mcp.tools.{op}")

                if schema_result.success:
                    schema = schema_result.data.get('schema', {})

                    # Validate schema:
                    validation = validate_schema(schema)

                    if validation.data.get('valid', False):
                        schema_path = schema_dir / f"{op}.json"

                        with open(schema_path, "w") as f:
                            json.dump(schema, f, indent=2)

                        stats["schemas_created"] += 1
                        print("✓")
                    else:
                        errors = validation.data.get('errors', [])
                        print(f"⚠ schema validation failed: {errors}")
                        stats["schemas_failed"] += 1
                else:
                    print(f"⚠ schema generation failed")
                    stats["schemas_failed"] += 1

            except Exception as e:
                print(f"✗ {str(e)}")
                stats["adapters_failed"] += 1
                stats["schemas_failed"] += 1

    # Print summary:
    print("\n" + "=" * 70)
    print("  Generation Summary")
    print("=" * 70)
    print(f"✓ Adapters created: {stats['adapters_created']}")
    print(f"✗ Adapters failed:  {stats['adapters_failed']}")
    print(f"✓ Schemas created:  {stats['schemas_created']}")
    print(f"✗ Schemas failed:   {stats['schemas_failed']}")
    print()

    if not args.dry_run:
        print(f"Output locations:")
        print(f"  Adapters: {adapters_dir}/")
        print(f"  Schemas:  {schema_dir}/")
        print()

    # Security validation:
    if args.validate_security and not args.dry_run:
        print("=" * 70)
        print("  Security Validation")
        print("=" * 70)

        try:
            security_result = validate_server_security(str(project_root / "src" / "gazebo_mcp"))

            if security_result.success:
                score = security_result.data.get('security_score', 0)
                issues = security_result.data.get('issues', [])

                print(f"\nSecurity Score: {score}/100")

                if score >= 80:
                    print("✓ Security validation passed!")
                else:
                    print("\n⚠️  SECURITY ISSUES FOUND:")

                    # Filter critical issues:
                    critical = ResultFilter.filter_by_field(issues, "severity", "critical")

                    for issue in critical:
                        print(f"\n  CRITICAL: {issue.get('description')}")
                        print(f"  Fix: {issue.get('fix')}")

                    # Show high severity:
                    high = ResultFilter.filter_by_field(issues, "severity", "high")

                    if high:
                        print(f"\n  Also found {len(high)} high-severity issues.")
                        print("  Run with --validate-security for full report.")

            else:
                print(f"✗ Security validation failed: {security_result.error}")

        except Exception as e:
            print(f"✗ Security validation error: {e}")

    print("\n✅ MCP asset generation complete!")

    if args.dry_run:
        print("\n(Dry-run mode - no files were written)")
        print("Run without --dry-run to generate files.")


if __name__ == "__main__":
    main()

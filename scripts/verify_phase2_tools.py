#!/usr/bin/env python3
"""
Verify Phase 2 Tools Integration.

Checks that all Phase 2 tools are properly registered with the MCP server.
"""

import sys
from pathlib import Path

# Add src and project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from gazebo_mcp.mcp_protocol.server.server import GazeboMCPServer


def main():
    """Verify all Phase 2 tools are registered."""
    print("=" * 80)
    print("PHASE 2 TOOLS VERIFICATION")
    print("=" * 80)

    # Initialize server
    server = GazeboMCPServer()

    # Get all tools
    all_tools = server.list_tools()
    tool_names = [tool["name"] for tool in all_tools]

    # Expected Phase 2 tools
    phase2_tools = {
        "SLAM Integration (8 tools)": [
            "gazebo_start_slam",
            "gazebo_stop_slam",
            "gazebo_save_map",
            "gazebo_load_map",
            "gazebo_get_slam_status",
            "gazebo_detect_loop_closure",
            "gazebo_merge_maps",
            "gazebo_optimize_map",
        ],
        "Computer Vision (10 tools)": [
            "gazebo_detect_objects",
            "gazebo_segment_image",
            "gazebo_track_objects",
            "gazebo_detect_markers",
            "gazebo_estimate_pose_from_image",
            "gazebo_run_visual_slam",
            "gazebo_process_image",
            "gazebo_extract_features",
            "gazebo_compute_optical_flow",
            "gazebo_calibrate_camera",
        ],
        "AI/ML Integration (8 tools)": [
            "gazebo_train_rl_agent",
            "gazebo_load_rl_policy",
            "gazebo_run_imitation_learning",
            "gazebo_clone_behavior",
            "gazebo_run_ml_inference",
            "gazebo_train_model",
            "gazebo_deploy_model",
            "gazebo_evaluate_model",
        ],
        "Cloud Integration (6 tools)": [
            "gazebo_connect_cloud_platform",
            "gazebo_upload_data",
            "gazebo_download_config",
            "gazebo_remote_control",
            "gazebo_sync_fleet_data",
            "gazebo_cloud_storage_operation",
        ],
    }

    # Verify each category
    total_expected = 0
    total_found = 0
    all_passed = True

    for category, expected_tools in phase2_tools.items():
        print(f"\n{category}")
        print("-" * 80)

        category_found = 0
        for tool in expected_tools:
            if tool in tool_names:
                print(f"  ✅ {tool}")
                category_found += 1
            else:
                print(f"  ❌ {tool} - NOT FOUND")
                all_passed = False

        print(f"\n  Found: {category_found}/{len(expected_tools)}")
        total_expected += len(expected_tools)
        total_found += category_found

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tools registered: {len(all_tools)}")
    print(f"Phase 2 tools expected: {total_expected}")
    print(f"Phase 2 tools found: {total_found}")

    if all_passed:
        print("\n✅ ALL PHASE 2 TOOLS SUCCESSFULLY REGISTERED!")
    else:
        print(f"\n❌ MISSING {total_expected - total_found} TOOLS")
        return 1

    # Show all registered tools
    print("\n" + "=" * 80)
    print("ALL REGISTERED TOOLS")
    print("=" * 80)

    for i, tool in enumerate(sorted(tool_names), 1):
        print(f"{i:3d}. {tool}")

    print(f"\nTotal: {len(all_tools)} tools")

    return 0


if __name__ == "__main__":
    sys.exit(main())

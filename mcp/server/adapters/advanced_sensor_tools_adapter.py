"""
Advanced Sensor Tools MCP Adapter.

Exposes Gazebo advanced sensor capability tools as MCP tools:
- fuse_sensor_data: Fuse data from multiple sensors
- visualize_sensor_data: Generate RViz2 visualization markers for sensor data
- process_sensor_data: Apply filtering/processing operations to sensor data
- calibrate_sensor: Calibrate a sensor and store the calibration
- monitor_sensor_health: Monitor health metrics for one or all sensors
- record_sensor_stream: Record a stream of sensor data to disk
- detect_objects_in_view: Detect objects in a camera's field of view
- segment_camera_image: Segment a camera image (semantic or instance)
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path:
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gazebo_mcp.tools import advanced_sensor_tools
from mcp.server.mcp_tool import MCPTool


def get_tools() -> List[MCPTool]:
    """Get MCP tools for advanced sensor capability operations."""
    return [
        MCPTool(
            name="gazebo_fuse_sensor_data",
            description=(
                "Fuse data from multiple sensors into a combined representation.\n\n"
                "Supported fusion types: lidar_camera, multi_lidar, imu_gps, camera_depth.\n\n"
                "Args:\n"
                "  fusion_type: Type of fusion to perform (required)\n"
                "  sensors: Non-empty list of sensor names to fuse (required)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- LiDAR+camera: gazebo_fuse_sensor_data(fusion_type='lidar_camera', sensors=['lidar_front','camera_rgb'])\n"
                "- IMU+GPS: gazebo_fuse_sensor_data(fusion_type='imu_gps', sensors=['imu_sensor','gps_sensor'])"
            ),
            parameters={
                "properties": {
                    "fusion_type": {
                        "type": "string",
                        "description": "Type of sensor fusion to perform",
                        "enum": ["lidar_camera", "multi_lidar", "imu_gps", "camera_depth"],
                    },
                    "sensors": {
                        "type": "array",
                        "description": "Non-empty list of sensor names to fuse",
                        "items": {"type": "string"},
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["fusion_type", "sensors"],
            },
            handler=advanced_sensor_tools.fuse_sensor_data,
        ),
        MCPTool(
            name="gazebo_visualize_sensor_data",
            description=(
                "Generate RViz2 visualization markers for a sensor's data.\n\n"
                "Supported visualization types: point_cloud, camera_frustum, imu_arrows, gps_path, contact_forces.\n\n"
                "Args:\n"
                "  sensor: Name of the sensor to visualize (required)\n"
                "  visualization_type: Type of visualization (required)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Point cloud: gazebo_visualize_sensor_data(sensor='lidar_front', visualization_type='point_cloud')\n"
                "- GPS path: gazebo_visualize_sensor_data(sensor='gps_sensor', visualization_type='gps_path')"
            ),
            parameters={
                "properties": {
                    "sensor": {
                        "type": "string",
                        "description": "Name of the sensor to visualize",
                    },
                    "visualization_type": {
                        "type": "string",
                        "description": "Type of visualization to generate",
                        "enum": ["point_cloud", "camera_frustum", "imu_arrows", "gps_path", "contact_forces"],
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["sensor", "visualization_type"],
            },
            handler=advanced_sensor_tools.visualize_sensor_data,
        ),
        MCPTool(
            name="gazebo_process_sensor_data",
            description=(
                "Apply a processing operation to a sensor's data.\n\n"
                "Supported operations: voxel_filter, statistical_filter, image_blur, edge_detection, "
                "segmentation, imu_filter, ground_removal.\n\n"
                "Args:\n"
                "  sensor: Name of the sensor whose data to process (required)\n"
                "  processing: Processing operation to apply (required)\n"
                "  params: Optional processing parameters dict (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Voxel filter: gazebo_process_sensor_data(sensor='lidar_front', processing='voxel_filter', params={leaf_size:0.05})\n"
                "- Edge detection: gazebo_process_sensor_data(sensor='camera_rgb', processing='edge_detection')"
            ),
            parameters={
                "properties": {
                    "sensor": {
                        "type": "string",
                        "description": "Name of the sensor whose data to process",
                    },
                    "processing": {
                        "type": "string",
                        "description": "Processing operation to apply",
                        "enum": [
                            "voxel_filter",
                            "statistical_filter",
                            "image_blur",
                            "edge_detection",
                            "segmentation",
                            "imu_filter",
                            "ground_removal",
                        ],
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional processing parameters dict",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["sensor", "processing"],
            },
            handler=advanced_sensor_tools.process_sensor_data,
        ),
        MCPTool(
            name="gazebo_calibrate_sensor",
            description=(
                "Calibrate a sensor and store the resulting calibration.\n\n"
                "Supported calibration types: camera_intrinsics, camera_extrinsics, lidar_offset, imu_bias, time_sync.\n\n"
                "Args:\n"
                "  sensor: Name of the sensor to calibrate (required)\n"
                "  calibration_type: Type of calibration to perform (required)\n"
                "  params: Optional calibration override parameters dict (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Camera intrinsics: gazebo_calibrate_sensor(sensor='camera_rgb', calibration_type='camera_intrinsics')\n"
                "- IMU bias: gazebo_calibrate_sensor(sensor='imu_sensor', calibration_type='imu_bias')"
            ),
            parameters={
                "properties": {
                    "sensor": {
                        "type": "string",
                        "description": "Name of the sensor to calibrate",
                    },
                    "calibration_type": {
                        "type": "string",
                        "description": "Type of calibration to perform",
                        "enum": ["camera_intrinsics", "camera_extrinsics", "lidar_offset", "imu_bias", "time_sync"],
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional calibration override parameters dict",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["sensor", "calibration_type"],
            },
            handler=advanced_sensor_tools.calibrate_sensor,
        ),
        MCPTool(
            name="gazebo_monitor_sensor_health",
            description=(
                "Monitor the health of one or all sensors.\n\n"
                "If sensor is provided, monitors only that sensor; otherwise monitors all known sensors.\n"
                "Returns per-sensor data rate, latency, dropout detection, and quality score, plus any alerts.\n\n"
                "Args:\n"
                "  sensor: Optional sensor name; omit to monitor all (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- All sensors: gazebo_monitor_sensor_health()\n"
                "- Single sensor: gazebo_monitor_sensor_health(sensor='lidar_front')"
            ),
            parameters={
                "properties": {
                    "sensor": {
                        "type": "string",
                        "description": "Optional sensor name; omit to monitor all known sensors",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": [],
            },
            handler=advanced_sensor_tools.monitor_sensor_health,
        ),
        MCPTool(
            name="gazebo_record_sensor_stream",
            description=(
                "Record a stream of sensor data to an output file.\n\n"
                "Supported compression: none, lz4, zstd.\n\n"
                "Args:\n"
                "  sensors: Non-empty list of sensor names to record (required)\n"
                "  output_path: Output path/prefix for the recording (required)\n"
                "  compression: Compression mode (default: 'none')\n"
                "  tags: Optional list of metadata tags (optional)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Basic: gazebo_record_sensor_stream(sensors=['lidar_front','camera_rgb'], output_path='/tmp/run1')\n"
                "- Compressed: gazebo_record_sensor_stream(sensors=['lidar_front'], output_path='/tmp/run2', compression='lz4')"
            ),
            parameters={
                "properties": {
                    "sensors": {
                        "type": "array",
                        "description": "Non-empty list of sensor names to record",
                        "items": {"type": "string"},
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path or prefix for the recording",
                    },
                    "compression": {
                        "type": "string",
                        "description": "Compression mode (default: 'none')",
                        "enum": ["none", "lz4", "zstd"],
                        "default": "none",
                    },
                    "tags": {
                        "type": "array",
                        "description": "Optional list of metadata tags",
                        "items": {"type": "string"},
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["sensors", "output_path"],
            },
            handler=advanced_sensor_tools.record_sensor_stream,
        ),
        MCPTool(
            name="gazebo_detect_objects_in_view",
            description=(
                "Detect objects in a camera's field of view.\n\n"
                "Returns detected objects with labels, confidence scores, 2D bounding boxes, and 3D positions.\n\n"
                "Args:\n"
                "  camera: Name of the camera sensor (required)\n"
                "  model: Detection model name (default: 'default')\n"
                "  confidence: Minimum confidence threshold in [0, 1] (default: 0.5)\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Basic: gazebo_detect_objects_in_view(camera='camera_rgb')\n"
                "- High confidence: gazebo_detect_objects_in_view(camera='camera_rgb', confidence=0.8)"
            ),
            parameters={
                "properties": {
                    "camera": {
                        "type": "string",
                        "description": "Name of the camera sensor",
                    },
                    "model": {
                        "type": "string",
                        "description": "Detection model name (default: 'default')",
                        "default": "default",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Minimum confidence threshold in [0, 1] (default: 0.5)",
                        "default": 0.5,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["camera"],
            },
            handler=advanced_sensor_tools.detect_objects_in_view,
        ),
        MCPTool(
            name="gazebo_segment_camera_image",
            description=(
                "Segment a camera image into classes or instances.\n\n"
                "Supported modes: semantic, instance.\n\n"
                "Args:\n"
                "  camera: Name of the camera sensor (required)\n"
                "  mode: Segmentation mode (default: 'semantic')\n"
                "  response_format: 'concise' or 'detailed' (optional)\n\n"
                "Examples:\n"
                "- Semantic: gazebo_segment_camera_image(camera='camera_rgb', mode='semantic')\n"
                "- Instance: gazebo_segment_camera_image(camera='camera_rgb', mode='instance')"
            ),
            parameters={
                "properties": {
                    "camera": {
                        "type": "string",
                        "description": "Name of the camera sensor",
                    },
                    "mode": {
                        "type": "string",
                        "description": "Segmentation mode (default: 'semantic')",
                        "enum": ["semantic", "instance"],
                        "default": "semantic",
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Response verbosity: 'concise' or 'detailed'",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                    },
                },
                "required": ["camera"],
            },
            handler=advanced_sensor_tools.segment_camera_image,
        ),
    ]

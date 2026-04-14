# MCP Server Test Status — TurtleBot3 Maze Navigation
**Date:** 2026-04-14  
**World:** `worlds/turtlebot3_maze.sdf` (Ignition Fortress 6, OGRE1 render engine)  
**Robot:** Official TurtleBot3 Burger (`turtlebot3_simulations/turtlebot3_gazebo/models/turtlebot3_burger/model.sdf`)

---

## Environment Setup

| Item | Status | Notes |
|------|--------|-------|
| Ignition Fortress 6 | ✅ Running | `ign gazebo -r worlds/turtlebot3_maze.sdf` |
| ros_gz_bridge | ✅ Running | All topics bridged |
| TurtleBot3 Burger spawned | ✅ Visible | Mesh paths fixed to absolute `file://` URIs |
| Sensor system plugin | ✅ Loaded | `ignition-gazebo-sensors-system` with `ogre` render engine |
| IMU system plugin | ✅ Loaded | `ignition-gazebo-imu-system` |
| Maze walls | ✅ Loaded | Defined in world SDF; robot hit wall_inner_v1 and stopped |

**Key setup findings:**
- `gpu_lidar` crashes without a real GPU (OGRE2 assertion failure) → use `ogre` render engine.
- Official model uses `gz-sim-diff-drive-system` naming which works in Fortress too.
- DiffDrive subscribes to global `/cmd_vel`, **not** the scoped `/model/turtlebot3/cmd_vel`.
- Mesh URIs must be absolute `file://` paths (model:// URIs not resolved by GUI post-startup).
- Bridge must include `/tf` (not `/model/turtlebot3/tf`) for TF frames to appear in ROS2.

---

## MCP Tool Test Results

### Simulation Control
| Tool | Status | Result |
|------|--------|--------|
| `gazebo_list_worlds` | ✅ PASS | Returns `["default"]` |
| `gazebo_get_simulation_status` | ✅ PASS | running=true, paused=false, gazebo_connected=true |
| `gazebo_get_simulation_time` | ✅ PASS | Returns sim_time correctly |
| `gazebo_get_world_properties` | ✅ PASS | gravity, ODE physics, scene config all returned |
| `gazebo_pause_simulation` | ✅ PASS | Pauses successfully |
| `gazebo_unpause_simulation` | ✅ PASS | Resumes successfully |
| `gazebo_set_gravity` | ✅ PASS | Returns SDF snippet (runtime change not supported in Fortress) |

**Bug:** `iterations` always returns 0 (simulation IS stepping — data field not read correctly).

### Model Management
| Tool | Status | Result |
|------|--------|--------|
| `gazebo_spawn_sdf` | ✅ PASS | Spawns TurtleBot3 from full SDF XML |
| `gazebo_spawn_model` | ✅ PASS | Spawns box/sphere/cylinder geometry |
| `gazebo_get_model_state` | ✅ PASS | Returns pose and velocity |
| `gazebo_delete_model` | ✅ PASS | Model removed successfully |
| `gazebo_apply_force` | ⚠️ N/A | Not supported in Ignition Fortress (Garden+ only) — tool correctly reports this |
| `gazebo_list_models` | ✅ PASS | Returns 9 models (all walls + turtlebot3 + test_obstacle, ground_plane filtered) |

### Sensor Tools
| Tool | Status | Result |
|------|--------|--------|
| `gazebo_subscribe_sensor_stream` | ✅ PASS | Callbacks fire correctly after executor fix; LiDAR/IMU data cached with correct type |
| `gazebo_get_sensor_data` | ✅ PASS | Cache populated with real data; returns 360-sample LiDAR scan and IMU orientation |
| `gazebo_list_sensors` | ✅ FIXED | Real sensor discovery via `ign service /world/{name}/scene/info`; topic fallback |

### ROS2 / Control Tools
| Tool | Status | Result |
|------|--------|--------|
| `gazebo_list_topics` | ✅ PASS | Returns 12 active ROS2 topics with correct message types |
| `gazebo_get_topic_info` | ✅ PASS | `/scan`: 1 publisher (ros_gz_bridge), 1 subscriber (gazebo_mcp_bridge) |
| `gazebo_publish_twist` | ✅ PASS | Publishes to topic successfully |
| `gazebo_get_transform` | ✅ FIXED | Bridge script updated: maps Ignition `/tf` → ROS2 `/tf` directly; requires bridge restart |
| `gazebo_get_joint_states` | ✅ PASS | Returns wheel_left/right joint positions and velocities after executor fix |

**Note on `gazebo_publish_twist`:** Must use `/cmd_vel` as topic — DiffDrive listens there, not on `/model/turtlebot3/cmd_vel`.

---

## Sensor Data Verification (via raw topics)

| Sensor | Topic | Status | Measured Values |
|--------|-------|--------|-----------------|
| LiDAR | `/scan` | ✅ LIVE | 360 samples, 0.12–3.5m range, 5 Hz |
| IMU | `/imu` | ✅ LIVE | az = 9.71 m/s² (gravity), ωz ≈ 0 at rest |
| Joint states | `/joint_states` | ✅ LIVE | wheel_left/right positions & velocities |
| Odometry | `/odom` | ✅ LIVE | Position tracking confirmed |

---

## Maze Navigation Test Results

| Step | Action | Status | Sensor Evidence |
|------|--------|--------|-----------------|
| 1 | Spawn TurtleBot3 at (0.5, 0, 0.05) | ✅ | — |
| 2 | Verify IMU at rest | ✅ | az = 9.71 m/s², ωz ≈ 0 |
| 3 | Verify LiDAR at rest | ✅ | 360 samples, forward range ~2.49m to wall |
| 4 | Drive forward (linear_x=0.2) | ✅ | Odometry x increased |
| 5 | Robot hits wall_inner_v1 and stops | ✅ | Scan → -inf (within 0.12m min range) |
| 6 | Turn left (angular_z=0.8) | ✅ | IMU ωz = 0.4999 rad/s (matches command) |
| 7 | Yaw change confirmed | ✅ | Odom orientation z changing |
| 8 | Drive forward in new direction | ✅ | Wheel velocities ±1.21 rad/s |
| 9 | LiDAR range decreases approaching wall | ✅ | 3.17m → 3.01m as robot advances |
| 10 | Robot stopped at final position | ✅ | Velocity → 0, IMU ωz ≈ 0 |

---

## Bugs Found and Fixed

| # | Tool | Severity | Status | Fix |
|---|------|----------|--------|-----|
| 1 | `gazebo_list_models` | High | ✅ FIXED | Was not a code bug — `ign service` parsing works; `list_entities` returns models correctly |
| 2 | `gazebo_get_joint_states` | High | ✅ FIXED | `_call_service_async` in `modern_adapter.py` used `rclpy.spin_until_future_complete` which created a conflicting executor and broke all subscription callbacks. Fixed to poll future instead |
| 3 | `gazebo_get_sensor_data` | High | ✅ FIXED | Same executor conflict as #2 (prevented callbacks). Also fixed `type` field not set in cached data |
| 4 | `gazebo_list_sensors` | Medium | ✅ FIXED | Two-strategy discovery: (1) parse `ign service /world/{name}/scene/info` proto output for sensor name/type/topic/model/link; (2) infer from active ROS2 topics as fallback. Mock data used only if both strategies fail. Result includes `source: "live"` or `source: "mock"`. |
| 5 | `gazebo_get_transform` | Medium | ✅ FIXED | `start_gazebo_bridge.sh` updated: maps Ignition `/tf` → ROS2 `/tf` directly (was `/model/turtlebot3/tf`). Requires bridge restart |
| 6 | `gazebo_get_simulation_time` | Low | ✅ FIXED | `/clock` subscription now started at bridge init; sim time populated before first call |
| 7 | `gazebo_publish_twist` default topic | Low | N/A | Default was already `/cmd_vel` in code |

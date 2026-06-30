# gazebo-mcp Architecture Evolution Plan

> **Status:** Execution-ready plan (P-1 → P5). Approved for implementation.
> **Date:** 2026-06-28 (revised)
> **Owner:** Koen van Gorkom
> **Branch context:** `feature/planned-capabilities`
> **Source research:** `/home/koen/Documents/Vaults/Local/05-Wiki/research/2026-06-28-gazebo-mcp-capability-analysis.md`
>
> **Locked user decisions (do not re-litigate):**
> 1. **TOOL SURFACE — CONSOLIDATE.** Collapse the current 69 `gazebo_*` adapter tools into the research's lean ~24 namespaced set (`world_*` / `scene_*` / `actuate_*` / `sensor_*` / `param_*` / `sim_*`) + sensor **resources**. Re-namespace/merge survivors; **deprecate** redundant and instruction-style tools (RViz-launch / rosbag-command emitters that only return CLI strings, plus the external-stack SLAM/Nav2 tools).
> 2. **HORIZON — FULL P0–P5** evolution (research §8), now prefixed by a mandatory **P-1** prerequisite.

---

## 0. Ground-truth corrections baked into this revision

This revision was produced after running commands against the repo. The previous draft contained several factual errors that have all been corrected here. The corrections themselves are load-bearing, so they are stated once, up front:

1. **There is a top-level `mcp/` package** (`/mnt/data/workspaces/gazebo-mcp/mcp/__init__.py`). `import mcp` resolves to it and **shadows the installed MCP SDK**. This is the *real* reason `mcp.server.fastmcp` appears "missing" — the shadow hides it. Renaming this package is now **P-1**, the first deliverable, and everything depends on it.
2. **FastMCP is already installed.** The SDK is `mcp` **1.27.1** (conda-forge) and it bundles FastMCP at `.../site-packages/mcp/server/fastmcp/__init__.py`. Once the local `mcp/` package is renamed, `from mcp.server.fastmcp import FastMCP` works with **zero new dependency**. The standalone `fastmcp` 2.x PyPI package is **not** needed, **not** resolvable on RoboStack/conda-forge, and is dropped from this plan entirely.
3. **Everything is async.** `GazeboInterface` and its bridge methods (`spawn_entity`, `delete_entity`, `get_entity_state`, `set_entity_state`, `apply_wrench`, …) are all `async def`. FastMCP runs `@mcp.tool` coroutines natively. So tools are `async def` that `await bridge.x()`. There is **no** sync `_run`/executor offload and **no** `contextvars` sync-shim. New bridge methods must also be `async def`.
4. **The world is Fortress, not Harmonic.** `worlds/empty_ros2.sdf` uses Fortress plugin names (`ignition-gazebo-*`, `libros_gz_sim`), not Harmonic (`gz-sim-*`). The Fortress-vs-Harmonic decision is now an explicit P-1 pre-flight item, not a silent assumption.
5. **No SO-101 asset exists** anywhere in the repo. P1 now has a named deliverable to source/author it, with a substitute fallback.
6. **`ros_gz` lives in `[feature.sim]`** → envs `sim` and `full`, not `dev`. Every real (`-m gazebo`) test runs under `-e full` (or `-e sim`); `-e dev` has no `ros_gz`.
7. **Test counts:** **500 tests collected**, **410 of them under `tests/unit/`** (rest in `tests/test_integration.py`, `tests/test_utils.py`, `tests/integration/`). They assert against the current 69 `gazebo_*` adapter surface + inline mocks + the hand-rolled adapter signatures. Retargeting them is budgeted real work in each phase.
8. **Two-layer reality.** Business logic lives under `src/gazebo_mcp/{bridge,tools,utils}/`. The MCP layer is a *separate* top-level package `mcp/server/{server.py,mcp_tool.py,adapters/*}` that wraps `src/gazebo_mcp/tools/*` via `sys.path.insert(0, src)`. The current "69 tools" are **adapter wrappers** over the underlying `tools/*.py` module functions. Consolidation retargets **both** layers.

---

## 1. Header / scope

This plan turns three verified assessments — (A) a tool consolidation map, (B) a FastMCP + Streamable-HTTP framework/transport migration design, and (C) an own-the-SDF bridge + actuation design — into one sequenced, test-gated roadmap, gated behind a namespace-collision fix.

**What changes:** the namespace collision (local `mcp/` → renamed package), the MCP protocol layer (hand-rolled JSON-RPC → SDK-bundled FastMCP), the transport (stdio → Streamable HTTP with per-session state, behind a dual-transport window), the tool surface (69 adapter wrappers → ~24 namespaced tools + resources at both the MCP and `tools/*` layers), and the bridge (fills four real gaps: step/physics, correct wrench transport, real pose readback, joint commanding; adds a mock adapter and an owned launch SDF).

**What does NOT change:** `OperationResult`, `utils/{validators,metrics,logger}.py`, the `bridge/` architecture (Pattern 4 — thin MCP → bridge node → `ros_gz` → Gazebo), the modern/classic adapter split, the mock-mode contract, and the **async** signatures of the underlying `tools/*.py` functions (they are re-namespaced/merged at the decorator layer; bodies move, signatures stay async).

**Honest constraints stated up front:**
- **Notify-then-poll, not streaming.** Sensor "subscription" is MCP `resources/subscribe` → `notifications/resources/updated` (a **bare URI ping carrying no data**) → client `resources/read` of the cached latest sample. There is no server-push data stream. Enforced in code and stated in docs (P5).
- **CPU-only physics.** Gazebo physics runs on CPU (DART). RTF is bounded by host CPU; large worlds run sub-real-time. Exposed honestly via `world_set_physics` / `world_get_stats`.
- **GUI-only gaps are genuinely unreachable.** Interactive viz (debug markers, model highlight, RViz panels, network viz) has no Gazebo Transport surface and is deprecated, not re-homed.
- **Actuation is gated on owning the SDF.** `actuate_*` only does real work once the launch SDF provisions `ApplyLinkWrench` / `JointController` / `gz_ros2_control` / `PosePublisher`. Until then it is mock-only.
- **`ros_gz` is `sim`/`full` only.** Real-backend acceptance never runs under `-e dev`.

---

## 2. Executive summary + current→target gap table

The repo today has a **namespace landmine**: a top-level `mcp/` package shadows the installed MCP SDK, so FastMCP looks missing even though it ships in `mcp` 1.27.1. Behind that, it is a **hand-rolled JSON-RPC stdio server** (`mcp/server/server.py` with `MCPTool` + `*_adapter.py`) exposing **69 adapter-wrapped tools** over a **real `ros_gz` bridge** (`src/gazebo_mcp/bridge/`) with inline per-tool mock fallback. Four tool families (SLAM, Nav2, advanced-sensor inference, developer/RViz/rosbag) are external-stack orchestration or instruction-string emitters with **no Gazebo Transport home**. The bridge has **four functional holes**: no step/physics control, a wrong-transport `apply_wrench` (service instead of `EntityWrench` topic), a **broken pose readback** (wrong message type → zeros), and **no joint commanding** — plus there is **no real mock adapter**, so CI cannot honestly assert "spawn → pose → step → remove".

The plan **first resolves the namespace collision (P-1)** so FastMCP is importable at all, then fixes the bridge gaps and lands the mock adapter (P0, so acceptance is real and CI deterministic), migrates the protocol to SDK-bundled FastMCP on stdio behavior-preservingly (within P-1/Step 0), lands the lean tool surface, then flips transport to Streamable HTTP behind a dual-transport window with per-session bridges and sensor resources (P3), and finishes with the optional Jetty `sim_*` path and hardening (P4/P5).

### Four separately-shippable migration tracks

The work decomposes into **four independent tracks**, each with its own revert point. They are interleaved across phases but must never be collapsed into one PR:

| Track | What it swaps | Revert point |
|---|---|---|
| **T1 Framework** | hand-rolled JSON-RPC → SDK-bundled FastMCP | old `server.py`/`MCPTool`/adapters retained behind a flag until new path is green |
| **T2 Transport** | stdio → Streamable HTTP | stdio remains the default and CI transport through a dual-transport window |
| **T3 Tool consolidation** | 69 `gazebo_*` wrappers → ~24 namespaced tools + resources | legacy aliases (survivors) + stub tools (deprecated) behind `GAZEBO_LEGACY_TOOLS` |
| **T4 Bridge** | bridge gap fixes + own-SDF + actuation + mock adapter | new bridge methods are additive; old methods kept until callers move |

### Gap table

| Dimension | Current (verified) | Target (P-1 → P5) |
|---|---|---|
| Namespace | local top-level `mcp/` **shadows** installed SDK | local pkg renamed; `import mcp` → site-packages SDK 1.27.1 |
| FastMCP availability | hidden by shadow (looks missing) | `from mcp.server.fastmcp import FastMCP` (SDK-bundled, no new dep) |
| Protocol layer | `GazeboMCPServer.handle_message`, `MCPTool` dataclass, 11 `*_adapter.py` | FastMCP `@mcp.tool` / `@mcp.resource`; old layer retained behind flag, deleted after T1 green |
| Transport | stdio only | stdio (CI/dev default) + Streamable HTTP with `Mcp-Session-Id`; HTTP opt-in then default after dual-window |
| Concurrency model | **async** bridge; sync hand-rolled dispatch | **async throughout** — `@mcp.tool` coroutines `await bridge.x()`; no executor/contextvars shim |
| Bridge access | process-global singleton `_bridge_helper.get_bridge()` | per-session `GazeboSession` held in FastMCP `lifespan`/`Context` (async connection) |
| Tool surface | 69 broad `gazebo_*` adapter wrappers | ~24 namespaced tools + `gz://sensor/<name>` resource family (both layers retargeted) |
| Sensors | sync-shaped tools incl. fake `subscribe_sensor_stream` | one-shot `sensor_snapshot`/`sensor_camera_image` + resources (notify-then-poll) |
| Step / physics / seed | **absent** | `world_step{n}` / `world_set_physics{step,rtf}` / `world_seed` (`async def`) |
| Pose readback | **broken** (wrong msg type → zeros) | real `Pose_V` parse from `PosePublisher` `/pose/info` |
| Wrench | **wrong transport** (service `ApplyLinkWrench`) | `EntityWrench` **topic** `/world/<w>/wrench` (+ `/wrench/clear`) |
| Joint commanding | **absent** | `actuate_joint` / `actuate_joint_trajectory` via provisioned controllers |
| Parameters | `param_*` orphaned in inventory | `param_list` / `param_get` / `param_set` over gz parameter services (P2) |
| Mock backend | inline per-tool mock data, no adapter | real `MockGazeboAdapter` (in-memory ECM, deterministic step) |
| Backend version | **Fortress** `ignition-*` world | explicit Fortress-stay vs Fortress→Harmonic decision (P-1 pre-flight) tied to RoboStack Jazzy `ros_gz` |
| Owned world | `worlds/empty_ros2.sdf` (Fortress, no actuation systems) | `worlds/provisioned.sdf.jinja` (decided backend, ApplyLinkWrench + PosePublisher) |
| Safety/bounds | none | `src/gazebo_mcp/utils/actuation_bounds.py` (magnitude/duration/joint-limit/rate caps) |
| Tests | **500 collected / 410 unit**, stdio, assert 69-tool surface | retargeted per-phase to new tools + mock adapter; green at every gate (a line item, not a side effect) |

---

## 3. Target architecture

SDK-bundled FastMCP front end (mcp 1.27.1), Streamable HTTP transport with per-session bridge connections (opt-in, then default after a dual-transport window), sensor data exposed as MCP resources, and a bridge that **owns its launch SDF** so the documented `CAN` capabilities are reachable. **Everything is async**: FastMCP runs `@mcp.tool` coroutines that `await` the async bridge directly. Pattern 4 (thin MCP → bridge node imports `ros_gz` → Gazebo) is preserved; `gz.transport` python bindings are deliberately **not** added to the core (kept as an optional P4+ feature for sensor latency only).

```
                          ┌───────────────────────────────────────────────────────┐
   MCP clients            │        gazebo-mcp  (SDK-bundled FastMCP app)            │
  (LLMs, agents)          │        mcp 1.27.1  ->  mcp.server.fastmcp.FastMCP        │
        │                 │                                                         │
        │                 │   mcp = FastMCP("gazebo-mcp", lifespan=lifespan)        │
        │  Streamable HTTP │                                                         │
        │  Mcp-Session-Id  │   @mcp.tool  async def world_* scene_* actuate_*        │
        ├─────────────────►│              sensor_* param_* sim_*                     │
        │   (stdio is the  │   @mcp.resource  gz://sensor/{name}                     │
        │    default until │                                                         │
        │    dual-window   │   each tool body:  async def f(..., ctx: Context):      │
        │    closes)       │       result = await get_session(ctx).bridge.x(...)     │
        │ resources/        │       metrics.record_tool_call(...)                    │
        │  subscribe        │       return result.to_dict()   (ToolError on fail)    │
        │   ───►            │                                                         │
        │ notifications/    │   ┌──────────── per session (lifespan/Context) ─────┐  │
        │  resources/       │   │ GazeboSession: bridge (async), connection_mgr,   │  │
        │  updated (PING,   │   │   subscriptions{uri: latest-sample cache}, real  │  │
        │   no data)        │   └──────────────────────────────────────────────────┘  │
        │   ◄───            │                          │                              │
        │ resources/read    │       get_session(ctx).bridge  (NO contextvars shim)    │
        │   ───► latest     └──────────────────────────┼──────────────────────────────┘
        │        cached                                 │
        │        sample                                 ▼
                                       ┌───────────────────────────────────────────┐
                                       │  src/gazebo_mcp/bridge/  (Pattern 4)        │
                                       │  GazeboBridgeNode (rclpy, one executor)     │
                                       │  async GazeboInterface                      │
                                       │  factory -> ModernAdapter | ClassicAdapter  │
                                       │                          | MockAdapter (new)│
                                       │  WorldProvisioner: OWN (launch) | ATTACH    │
                                       │  utils/actuation_bounds.py (clamp/reject)   │
                                       └───────────────────────────────────────────┘
                                                          │ ros_gz services + topics
                                                          ▼  (envs: sim / full only)
                                       ┌───────────────────────────────────────────┐
                                       │  Gazebo (Fortress OR Harmonic — decided in  │
                                       │  P-1, pinned to RoboStack Jazzy ros_gz)     │
                                       │  worlds/provisioned.sdf.jinja:              │
                                       │   Physics, UserCommands, SceneBroadcaster,  │
                                       │   Contact, ApplyLinkWrench, PosePublisher,  │
                                       │   per-model JointController/gz_ros2_control │
                                       └───────────────────────────────────────────┘
```

**Three research upgrades, mapped to this diagram:**
1. **Streamable HTTP + sessions** — `GazeboSession` keyed by `Mcp-Session-Id`, stored in the FastMCP `lifespan` context and reached via `get_session(ctx)`; per-session async bridge + subscriptions so concurrent clients don't leak state. No sync shim.
2. **Sensors as resources** — `gz://sensor/{name}` template; `subscribe → updated (ping) → read latest cached`. Honest notify-then-poll.
3. **Own the launch SDF** — `WorldProvisioner` renders + launches a world (Fortress *or* Harmonic per the P-1 decision) declaring the systems that turn `CAN*` → `CAN`. Provision-at-load only; never `/entity/system/add` at runtime (fragile, §9).

---

## 4. Tool consolidation appendix

### 4.A Full current→target mapping (all 69 `gazebo_*` tools)

Each row retargets **both** the MCP adapter wrapper (`mcp/server/adapters/*_adapter.py` → renamed pkg) **and** the underlying `src/gazebo_mcp/tools/*.py` function.

| # | Current tool | Disposition | Target / note |
|---|---|---|---|
| **model_management (6)** ||||
| 1 | `list_models` | rename | `scene_list_models` (`/scene/info`) |
| 2 | `spawn_model` | rename+merge | `scene_spawn` (unify file/uri/sdf variants → `/create`) |
| 3 | `delete_model` | rename | `scene_remove` (`/remove`) |
| 4 | `get_model_state` | rename | `scene_get_state` (`/state`, PosePublisher) |
| 5 | `set_model_state` | merge | `scene_set_pose` — pose only; **drop velocity-set** (gz #3284) |
| 6 | `apply_force` | rename+re-type | `actuate_wrench` — re-typed to `EntityWrench` **topic** `/wrench`; needs ApplyLinkWrench (P1) |
| **simulation_tools (7)** ||||
| 7 | `pause_simulation` | rename | `world_pause` (`/control`) |
| 8 | `unpause_simulation` | rename | `world_play` (`/control`) |
| 9 | `reset_simulation` | rename | `world_reset{mode}` (all/time/model) |
| 10 | `set_simulation_speed` | merge | `world_set_physics{rtf}` (`/set_physics`) |
| 11 | `get_simulation_time` | merge | `world_get_stats` (`/stats`,`/clock`) |
| 12 | `get_simulation_status` | merge | `world_get_stats` (WorldStatistics) |
| 13 | `list_worlds` | merge | `scene_info` (single provisioned world) |
| **world_tools (5)** ||||
| 14 | `load_world` | **DEPRECATE** | server owns launch SDF; not a Transport capability |
| 15 | `save_world` | **DEPRECATE** | use `scene_get_state`/`scene_info` snapshot; authoring is offline |
| 16 | `get_world_properties` | merge | physics→`world_get_stats`, scene→`scene_info` |
| 17 | `set_world_property` | merge/deprecate | physics subset→`world_set_physics`; generic set DEPRECATED |
| 18 | `set_gravity` | **DEPRECATE** | load-time SDF param; provision in launch SDF |
| **ros2_tools (6)** ||||
| 19 | `list_topics` | rename+merge | `sensor_list` (+ discovery) |
| 20 | `get_topic_info` | merge | `sensor_list` detail / `sensor_snapshot` |
| 21 | `publish_twist` | merge | `actuate_joint{mode:cmd_vel}` (DiffDrive; needs system) |
| 22 | `get_transform` | merge | `scene_get_state` (tf backend) |
| 23 | `spawn_sdf` | merge | `scene_spawn` (unify ROS path) |
| 24 | `get_joint_states` | merge | `scene_get_state` (`/joint_states`) |
| **sensor_tools (3)** ||||
| 25 | `list_sensors` | merge | `sensor_list` |
| 26 | `get_sensor_data` | rename+split | `sensor_snapshot{topic}` + `sensor_camera_image{...}` |
| 27 | `subscribe_sensor_stream` | **→ RESOURCE** | `gz://sensor/<name>` (notify-then-poll); reuse latest-sample cache |
| **advanced_sensor_tools (8)** ||||
| 28 | `fuse_sensor_data` | **DEPRECATE** | client/LLM logic over snapshots |
| 29 | `visualize_sensor_data` | **DEPRECATE** | GUI/RViz-only |
| 30 | `process_sensor_data` | **DEPRECATE** | client-side processing |
| 31 | `calibrate_sensor` | **DEPRECATE** | offline SDF noise params |
| 32 | `monitor_sensor_health` | merge | field in `sensor_list` |
| 33 | `record_sensor_stream` | **DEPRECATE** | `ros2 bag`/`gz log` CLI |
| 34 | `detect_objects_in_view` | **DEPRECATE** | client/LLM inference |
| 35 | `segment_camera_image` | **DEPRECATE** | use Gazebo segmentation sensor + snapshot |
| **developer_tools (12)** ||||
| 36 | `add_debug_marker` | **DEPRECATE** | GUI-only |
| 37 | `clear_debug_markers` | **DEPRECATE** | GUI-only |
| 38 | `highlight_model` | **DEPRECATE** | GUI-only |
| 39 | `launch_rviz` | **DEPRECATE** | instruction-only CLI emitter |
| 40 | `add_rviz_visualization` | **DEPRECATE** | instruction-only emitter |
| 41 | `start_recording` | **DEPRECATE** | `ros2 bag record` emitter |
| 42 | `stop_recording` | **DEPRECATE** | rosbag CLI emitter |
| 43 | `playback_recording` | **DEPRECATE** | `ros2 bag play` emitter |
| 44 | `save_snapshot` | merge | `scene_get_state` (client persists) |
| 45 | `restore_snapshot` | **DEPRECATE** | expressible via `scene_set_pose`/`scene_spawn` |
| 46 | `profile_simulation` | merge | `world_get_stats` (reuse `metrics.py`/`profiler.py`) |
| 47 | `identify_bottlenecks` | **DEPRECATE** | analysis over stats |
| **multi_robot_tools (6)** ||||
| 48 | `spawn_robot_fleet` | merge | `scene_spawn_many` (reuse `_compute_formation_poses`) |
| 49 | `get_fleet_status` | merge | `scene_get_state` (name filter) |
| 50 | `send_fleet_command` | merge | client fan-out over `actuate_*` |
| 51 | `apply_swarm_behavior` | **DEPRECATE** | behavior/controller logic |
| 52 | `visualize_robot_network` | **DEPRECATE** | GUI-only |
| 53 | `enable_multi_robot_collision_avoidance` | **DEPRECATE** | behavior; collision is load-time SDF |
| **slam_tools (6)** ||||
| 54–59 | `start_slam`, `save_slam_map`, `load_slam_map`, `localize_robot`, `get_localization_quality`, `detect_loop_closure` | **DEPRECATE (deferred)** | external ROS2 nodes (slam_toolbox/AMCL); separate server if ever needed |
| **nav2_tools (10)** ||||
| 60–69 | `initialize_nav2`, `send_nav_goal`, `cancel_nav_goal`, `get_nav_status`, `plan_path`, `visualize_path`, `create_occupancy_map`, `update_costmap`, `follow_waypoints`, `plan_coverage_path` | **DEPRECATE (deferred)** | external Nav2 stack; separate nav2-mcp if needed |

**Tally:** 69 → ~24 tools + 1 resource family. Direct rename/keep ≈ 9; merge-into ≈ 14; deprecate ≈ 46.

### 4.B Final lean inventory (~24 core tools + optional sim_* + resources)

**`world_*` (7)** → `/control`, `/set_physics`, `/stats`
`world_pause` · `world_play` · `world_step{n}` · `world_reset{mode}` · `world_seed` · `world_set_physics{step,rtf}` · `world_get_stats`

**`scene_*` (7)** → `/create*`, `/remove`, `/set_pose*`, `/state`, `/scene/info`
`scene_spawn{sdf|uri,name,pose}` · `scene_spawn_many` · `scene_remove{name}` · `scene_set_pose{name,pose}` · `scene_list_models` · `scene_get_state` · `scene_info`

**`actuate_*` (4)** *(P1; needs provisioned systems)* → `/wrench*`, `cmd_*`, `joint_trajectory`
`actuate_wrench{link,force,torque,duration,persistent}` · `actuate_wrench_clear` · `actuate_joint{model,joint,mode,value}` · `actuate_joint_trajectory`

**`sensor_*` (3)** *(P2)* → sensor topics, `gz topic -n 1`
`sensor_list` · `sensor_snapshot{topic}` · `sensor_camera_image{topic,resolution,quality}` (base64-capped)

**`param_*` (3)** *(P2; gz parameter services)* → `/world/<w>/.../parameters`
`param_list` · `param_get{name}` · `param_set{name,value}`

**`sim_*` (5, optional P4)** → Jetty `simulation_interfaces` (REP-2018)
`sim_spawn` · `sim_delete` · `sim_reset` · `sim_step` · `sim_get_features`

**Resources:** `gz://sensor/<name>` — `resources/subscribe` → `updated` ping → `read` latest cached sample (capped).

Total: 7 + 7 + 4 + 3 + 3 = **24 core** (+ 5 optional sim_*) + 1 resource family.

---

## 5. Phased roadmap P-1 → P5

Each phase lists Objective, Files, Key signatures, Dependencies, **Test migration**, **Rollback**, Acceptance (runnable), Risks. Phases P0–P5 map directly to research §8; **P-1 is a new prerequisite** added in this revision.

**Naming note.** The renamed local package below is referred to as `gz_mcp_server/` (the recommended name; folding into `src/gazebo_mcp/mcpserver/` is the alternative — pick one in P-1 and use it consistently). All later "MCP layer" file paths assume the chosen name.

---

### P-1 — Resolve the `mcp/` namespace collision *(NEW — first deliverable, blocks everything)*

**Objective.** Rename the local top-level `mcp/` package so `import mcp` resolves to the installed SDK and `from mcp.server.fastmcp import FastMCP` works. Decide the backend version (Fortress-stay vs Harmonic-migrate) against RoboStack Jazzy `ros_gz`. This is a pure refactor + decision PR with **no behavior change**.

**Files.**
- Rename: `mcp/` → `gz_mcp_server/` (package dir, `__init__.py`, `README.md`, `server/`, `server/adapters/`, `server/mcp_tool.py`, `server/server.py`).
- Edit every import that reads `from mcp.server...` / `from mcp.server.adapters import (...)` inside the renamed package (notably `gz_mcp_server/server/server.py` lines ~34–37 and `gz_mcp_server/server/__init__.py`).
- Edit the file formerly at `mcp/server/server.py` (now `gz_mcp_server/server/server.py`): keep its `sys.path.insert(0, str(PROJECT_ROOT / "src"))` block, but repoint the local self-imports to `gz_mcp_server.server.*`.
- Edit entry points: `pyproject.toml` `[project.scripts] gazebo-mcp-server = "gazebo_mcp.server:main"` (confirm it still routes; if it imported the old `mcp.server`, repoint), `pixi.toml` `[tasks] serve = "python -m gazebo_mcp.server"` and `server = "gazebo-mcp-server"`. Inspect `src/gazebo_mcp/server.py` and `src/gazebo_mcp/mcp_protocol/server/` for any `mcp.server` references and repoint them.
- Add a pre-flight note file or README section recording the **backend decision** (see sub-task below).

**Backend version pre-flight (sub-task, decide explicitly).**
- Pin the `gz` version compatible with **RoboStack Jazzy `ros-jazzy-ros-gz`** (`pixi.toml [feature.sim]`). State the `ros_gz`↔`gz` compatibility constraint in the decision note.
- Decide **Fortress-stay** vs **Fortress→Harmonic migration**. The existing `worlds/empty_ros2.sdf` is **Fortress** (`ignition-gazebo-*`, `libros_gz_sim`). Whichever is chosen, P0's `worlds/provisioned.sdf.jinja` must use the matching plugin filenames (`ignition-gazebo-*` for Fortress, `gz-sim-*` for Harmonic). Do **not** assume Harmonic. Record the decision; all later phases inherit it.

> **DECISION (recorded in P-1 — 2026-06-28): target Harmonic; migrate the Fortress world in P0.**
> Rationale: ROS 2 Jazzy's official Gazebo pairing is **gz Harmonic** (REP-2000), and RoboStack's `ros-jazzy-ros-gz` (`[feature.sim]`) is built against Harmonic. The current `worlds/empty_ros2.sdf` (Fortress `ignition-gazebo-*` plugin names) is therefore mismatched with the Jazzy default and will be re-authored with `gz-sim-*` / `libgz-sim-*` plugin names as `worlds/provisioned.sdf.jinja` in P0.
> **VERIFIED 2026-06-28:** the system `gz` binary (`/usr/bin/gz`) is **Gazebo Sim 8.14.0 = Harmonic** — confirms the Harmonic target and gives a real backend to test against without installing `-e sim`'s gz. (Aside: the `~/workspaces/jetank/` workspace is a *separate* stack — ROS **Humble** + `ros-gz-sim` + `empty_fortress.sdf` = **Fortress** — so its pixi env is **not** reusable for gazebo-mcp/Jazzy; only its system gz (Harmonic) and its robot assets are.)

**Test migration.** None functionally — the 500 collected / 410 unit tests must pass unchanged after the rename. Any test that does `from mcp.server...` (for the local package) is updated to `from gz_mcp_server.server...`. This is a mechanical sed-style edit and is the entire test work for P-1.

**Rollback.** Single rename commit; revert restores the shadowing package. Low risk — no logic changes.

**Dependencies.** None. This is the root of the tree.

**Acceptance.**
```bash
# the shadow is gone — import resolves to the installed SDK:
pixi run -e dev python -c "import mcp; print(mcp.__file__)"
#   -> .../.pixi/envs/dev/.../site-packages/mcp/__init__.py   (NOT repo-local)
pixi run -e dev python -c "from mcp.server.fastmcp import FastMCP; print('ok')"   # -> ok
# old server still importable + runnable under the new package name:
pixi run -e dev python -c "import gz_mcp_server.server.server"
pixi run -e dev pytest -q            # 500 collected, all green (410 unit)
```

**Risks.** Stray hard-coded `mcp.server` strings (in launch files, scripts, docs) — grep the whole tree (`grep -rn "from mcp\.\|import mcp\.server\|mcp/server"`) and fix all. The `pyproject` console-script must keep resolving.

---

### Step 0 — SDK server scaffold on stdio (parity) *(T1 framework swap, flag-gated)* — ✅ IMPLEMENTED 2026-06-28

> **DECISION (execution-time amendment): use the SDK low-level `Server`, NOT `FastMCP`, for the parity port.**
> Empirically verified during execution: `FastMCP.add_tool` *infers* a tool's input schema from the Python
> function signature. The 69 legacy tools are adapter-wrapped handlers with hand-curated JSON schemas
> (enums, defaults) and `**kwargs` call surfaces, so FastMCP inference corrupts them (`{kwargs: string}`).
> Since the 69 are consolidated/retired in P0–P2, retyping them all for FastMCP is throwaway work.
> `mcp.server.lowlevel.Server` lets `list_tools` return the curated `Tool` objects verbatim (proven
> byte-identical to the legacy server) and `call_tool` dispatch to the existing handlers — exact parity,
> SDK-compliant lifecycle, zero throwaway. New lean tools (P0+) are authored on **FastMCP** `@mcp.tool`;
> the app shell adopts FastMCP when its resources/Context/Streamable-HTTP features land (P3).

**Objective.** Stand up an SDK low-level `Server` on the SDK's compliant stdio transport while keeping the existing 69 `gazebo_*` tools 1:1, proving protocol parity before any consolidation. **The old hand-rolled server stays runnable behind a second entry point** until the new path's acceptance is green.

**As-built.** `gz_mcp_server/server/sdk_app.py` (`build_server()` → low-level `Server`, reuses adapter schemas + handlers, `validate_input=False` to preserve handlers' structured errors), `src/gazebo_mcp/sdk_server.py` (`main()` shim → `stdio_server()` + `server.run`), `gazebo-mcp-sdk` console script + `serve-sdk` pixi task (both **parallel** to the retained `gazebo-mcp-server`). Parity test `tests/unit/test_sdk_server_parity.py`: registry count, **exact schema parity vs the legacy server**, in-memory-client `initialize→tools/list→call_tool`, and a real stdio-subprocess smoke. Acceptance met: 69 tools, full suite 493 passed (410 unit), 0 regressions.

**Files.**
- New: `gz_mcp_server/server/app.py` (`mcp = FastMCP("gazebo-mcp", lifespan=lifespan)`; `lifespan` opens/closes the async bridge connection and stores the `GazeboSession`), `gz_mcp_server/server/fastmcp_main.py` (thin `main()` calling `mcp.run(transport="stdio")`).
- Edit: `pyproject.toml` — add a **second** console script `gazebo-mcp-fastmcp = "gz_mcp_server.server.fastmcp_main:main"`; keep `gazebo-mcp-server` pointing at the old path. `pixi.toml` — add `serve-fastmcp` task; keep `serve` on the old server.
- **No dependency change** — FastMCP is in the already-installed `mcp` 1.27.1.
- Delete **only after parity green and in a later PR** (not this one): old `mcp_tool.py`, `*_adapter.py`, `handle_message`/`_format_*`/`run`/`call_tool`.

**Key signatures.**
```python
# gz_mcp_server/server/app.py
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP, Context

@asynccontextmanager
async def lifespan(server):
    session = await GazeboSession.create(config)   # async bridge connect
    try:
        yield {"session": session}
    finally:
        await session.aclose()

mcp = FastMCP("gazebo-mcp", lifespan=lifespan)

@mcp.tool()
async def spawn_model(name: str, ..., ctx: Context) -> dict:
    session = ctx.request_context.lifespan_context["session"]
    result = await session.bridge.spawn_entity(...)   # bridge is async; await it directly
    metrics.record_tool_call("spawn_model", result.success)
    return result.to_dict()
```
No `_run` executor wrapper, no `contextvars` shim — tools are coroutines that `await` the async bridge. A tiny shared helper (`_call(ctx, name, coro)`) may wrap metrics + `OperationResult.to_dict()` + `ToolError`, but it is itself `async` and awaits.

> **Step-0 no-backend tolerance (required).** The real `MockGazeboAdapter` + `detection.py` mock-fallback only land in **P0**, which runs *after* Step 0. So Step 0's `lifespan`/`GazeboSession.create` MUST degrade gracefully to a lazy/no-backend session when run in `-e dev` (no `ros_gz`, no live Gazebo) — mirroring the current `_bridge_helper.get_bridge()` try/except + `backend_is_mock()` graceful-degradation contract. Tool listing is static registration metadata and must never hard-fail on a missing backend: Step 0 acceptance (69 tools loadable via the in-memory client) must pass in `-e dev` with no Gazebo present. Concretely, `GazeboSession.create` connects lazily (defer the bridge connect to first tool call, or catch the connect failure and yield a session whose `bridge` is None until P0 supplies the mock).

**Test migration.** Add a parity snapshot test: dump FastMCP's generated `inputSchema` for a sample of tools and diff against the old hand-written schema. The 410 unit tests still target the underlying `tools/*.py` async functions (unchanged), so they stay green. Budget: ~0.5 d to write the parity/snapshot harness.

**Rollback.** The FastMCP app is purely additive (new files, new entry point). Revert = drop the new files; the old server is untouched and remains the default.

**Dependencies.** P-1 (FastMCP must be importable).

**Acceptance.**
```bash
pixi run -e dev pytest tests/unit/ -q                       # 410 still green
pixi run -e dev python -c "from gz_mcp_server.server.app import mcp; import anyio; \
  print(len(anyio.run(mcp.list_tools)))"                    # == 69
# stdio lifecycle parity via the SDK in-memory client (NOT a one-shot heredoc):
pixi run -e dev python - <<'PY'
import anyio
from mcp.shared.memory import create_connected_server_and_client_session as connect
from gz_mcp_server.server.app import mcp
async def main():
    async with connect(mcp._mcp_server) as client:
        await client.initialize()                           # initialize -> initialized
        tools = await client.list_tools()                   # tools/list
        assert len(tools.tools) == 69, len(tools.tools)
        print("parity ok")
anyio.run(main)
PY
```
*(If the in-memory helper path differs in 1.27.1, the equivalent is a full `initialize → notifications/initialized → tools/list` exchange over a spawned stdio client — never a `<<<` one-shot heredoc, which skips the handshake.)*

**Risks.** FastMCP schema inference differs from hand-written JSON schema → the snapshot test above catches drift. Async tool bodies must not block the event loop (the bridge is already async, so this holds).

---

### P0 — Bridge gap fixes + own-SDF skeleton; lean `world_*` + `scene_*` *(T4 bridge + T3 consolidation; maps §8 P0)*

> **STATUS — P0-A ✅ DONE 2026-06-28; P0-B MOCK SIDE ✅ DONE & VERIFIED 2026-06-29 (real ros_gz code written, live-verify DEFERRED — see the detailed STATUS block after Acceptance below).**
> Done & verified in `-e dev`: `MockGazeboAdapter` (honest in-memory backend, correct pose readback), `GazeboInterface` extended with async `step`/`set_physics`/`seed` (non-abstract defaults), `GazeboBackend.MOCK` + node-optional factory wiring, and the headline acceptance "spawn cube → query pose → step → remove" as `tests/unit/test_mock_adapter.py` (7 tests, full suite 500 passed). **Still pending (P0-B, needs `-e sim`/`-e full` + the FastMCP-coexistence decision):** real `ModernGazeboAdapter` pose-readback fix + `step`/`set_physics`/`seed` impls (`/control` multi_step, `/set_physics`), the `WorldProvisioner` + owned launch SDF, and the lean `world_*`/`scene_*` tools authored as FastMCP `@mcp.tool`.

**Objective.** Make "spawn cube → query pose → step → remove" **actually pass** against a mock with no real Gazebo. Fix the broken pose readback, add `async` step/physics/seed, land the mock adapter + detection fallback, provision the owned world (matching the P-1 backend decision), and ship lean `world_*`/`scene_*` over stdio.

**Files.**
- Bridge (all new methods `async def`): extend `src/gazebo_mcp/bridge/gazebo_interface.py` (`async step`, `async set_physics`, `async seed`); fix `src/gazebo_mcp/bridge/adapters/modern_adapter.py` (`get_entity_state`/`_ensure_pose_info_subscriber` → real `Pose_V` parse; add async step/physics/seed); new `src/gazebo_mcp/bridge/adapters/mock_adapter.py`; new `src/gazebo_mcp/bridge/world_provisioner.py`; edit `src/gazebo_mcp/bridge/factory.py` (MOCK branch), `src/gazebo_mcp/bridge/detection.py` (mock fallback instead of `RuntimeError`), `src/gazebo_mcp/bridge/config.py` (MOCK backend + `own_world`/`step_size`/`rtf`/`model_manifest`), `src/gazebo_mcp/bridge/gazebo_bridge_node.py` (construct `WorldProvisioner`; async step/physics/seed wrappers).
- World/launch: new `worlds/provisioned.sdf.jinja` (plugin filenames per P-1 backend decision; replaces `worlds/empty_ros2.sdf` as the launch target); new `launch/provisioned_world.launch.py`.
- Tools (both layers): new underlying `src/gazebo_mcp/tools/world.py` + `src/gazebo_mcp/tools/scene.py` (async functions); new MCP layer `gz_mcp_server/server/tools/world.py` + `.../scene.py` (`@mcp.tool` async wrappers). Deprecate `world_tools.load_world`/`save_world`.
- Helper: refactor `src/gazebo_mcp/tools/_bridge_helper.py` → `get_bridge()` (mock-safe) + `backend_is_mock()`; bridge resolution now reads the session from `Context`, not a global.
- Tests: new `tests/fixtures/p0_world.json`, `tests/integration/test_p0_acceptance.py`.

**Key signatures.**
```python
# gazebo_interface.py (new ABSTRACT methods — all async)
async def step(self, n: int, world: str) -> bool: ...
async def set_physics(self, step_size: float | None, rtf: float | None, world: str) -> bool: ...
async def seed(self, value: int, world: str) -> bool: ...
# world_provisioner.py
class WorldProvisioner:
    def __init__(self, config: GazeboConfig): ...
    async def provision(self) -> str | None: ...   # OWN: render+launch, return world name; ATTACH: no-op
    async def destroy(self) -> None: ...
```
`step(n)` → `ControlWorld` with `WorldControl.multi_step = n`. Mock `step(n)` advances `sim_time += n*step_size` and integrates any recorded wrench (Δpose = ½·(F/m)·(n·dt)²) for CI-observable effects.

**Test migration.** Rename/retarget `tests/unit/test_simulation_tools.py` + `test_model_management.py` (and `test_sensor_world_tools.py`'s world portions) from the 69-tool names to `world_*`/`scene_*`. Replace inline per-tool mock fixtures with assertions against `MockGazeboAdapter`. Keep deprecated names covered by stub/alias tests (see Rollback). Budget: ~1.5 d (this is the bulk of P0 test work and is a line item, not incidental).

**Rollback (T4 + T3).** New bridge methods are additive; the wrong-transport `apply_wrench` is *kept* (untouched) in P0 — its replacement is P1. `world_*`/`scene_*` ship alongside the legacy tools behind `GAZEBO_LEGACY_TOOLS=1` (default ON). Revert = drop the new tool modules + provisioner; the bridge gap-fixes (pose readback, step) are independently revertible commits.

**Dependencies.** P-1 + Step 0. The mock path needs no Gazebo; the opt-in real variant needs the P-1-decided backend.

**Acceptance.**
```bash
# mock backend, no Gazebo/ROS graph — runs in -e dev.
# NOTE: pixi [activation.env] pins GAZEBO_BACKEND=modern, which OVERRIDES a shell
# `GAZEBO_BACKEND=mock pixi run ...`. The acceptance test therefore forces mock
# IN-PROCESS (monkeypatch.setenv in an autouse fixture) — do NOT rely on the shell var.
pixi run -e dev pytest tests/integration/test_p0_acceptance.py tests/unit/test_lean_tools.py -q
#   asserts: scene_spawn test_cube@(1,2,0.5); scene_get_state == (1,2,0.5)  (impossible before the readback fix);
#            world_step(100) => sim_time == 100*step_size (0.1); scene_remove => not in scene_list_models()
pixi run -e dev pytest -q                                   # full suite green (2 pre-existing failures unrelated to P0-B)
# opt-in REAL hardware — needs ros_gz, so -e full (NOT -e dev):  *** DEFERRED — env not installed ***
pixi run -e full pytest -m gazebo tests/integration/test_p0_acceptance.py
```

**Risks.** `/world/<w>/pose/info` typing (`gz.msgs.Pose_V` → `tf2_msgs/TFMessage`) must be exact or readback stays broken — covered by the acceptance assert. World-template plugin filenames must match the P-1 backend (Fortress `ignition-gazebo-*` vs Harmonic `gz-sim-*`) or systems silently don't load.

> **STATUS — P0-B MOCK SIDE ✅ DONE & VERIFIED 2026-06-29** (`-e dev`, commits `8407748` bridge, `3a78749` tools+FastMCP, `b63837b` tests, `065e556` review-fixes). Mock acceptance green (11 new tests; headline spawn→state(1,2,0.5)→step(100)=0.1→remove). FastMCP app introduced now (user decision) — lean tools as `@mcp.tool`; **legacy 69 stay on the retained low-level `sdk_app` entry point** (FastMCP validates args against inferred `FuncMetadata`, not an overridden curated `.parameters`, so clean single-server mount is not viable on mcp 1.27.1 → unification deferred to **P3**). Real ros_gz/Harmonic code is **written but NOT live-verified** (no `-e full`/`ros_gz` here).
>
> **P0-B-real — DEFERRED follow-ups (adversarial grill 2026-06-29; all require live ros_gz/Harmonic to fix+verify, none block the mock-side merge):**
> 1. **`modern_adapter` pose cache keyed only by `child_frame_id`** — SceneBroadcaster `Pose_V`/`TFMessage` carries *every* entity (links/visuals/nested), so cross-model link-name collisions (e.g. `base_link`) shadow model entries; ignores `header.frame_id`. Fix: filter to world-scoped top-level models / key by `(parent, child)`. Add an integration assert that the bridged `child_frame_id` == spawn name. *(high once real)*
> 2. **`set_physics` claims `applied=True` while silently no-op** — Harmonic physics is a **gz-transport** service (`gz.msgs.Physics`), not a ROS srv; `ros_gz_interfaces.srv.SetPhysics` ImportErrors → both branches `return True`. Fix: shell out to `gz service` (like `list_entities`) or report `applied=False`/`unsupported`. Same honesty bug in **`seed`** (#11) and partially **`step`** sim_time fabricated as 0.0 (#6).
> 3. **`get_entity_state` cache never invalidated** — returns first-ever pose forever (stale for moving models); deleted entities still report a pose; `ModelNotFoundError` only for never-seen. Fix: always refresh-spin or timestamp+stale-evict; clear cache in `delete_entity`.
> 4. **`PosePublisher` placed at `<world>` scope** in `provisioned.sdf.jinja` — attaches to no model, may publish nothing on `/world/<w>/pose/info`; verify per-model placement when assets land (P1).
> 5. **`spin_once` executor-conflict risk** in `get_entity_state` if the node is concurrently spun elsewhere; **bridge-mapping payload syntax** `@...[gz.msgs.Pose_V` in the launch needs the registered `Pose_V↔TFMessage` mapping confirmed on the installed `ros_gz_bridge`.
> 6. **`detection` AUTO→MOCK silent fallback** (#4) can mask a "Gazebo not started yet" prod condition — by-design per plan, but loud-WARN it and consider gating to opt-in. **`get_bridge` singleton not backend-keyed / no thread guard** (#12) — fine for single-backend-per-process; revisit if runtime backend switching is ever needed.

---

### P1 — Actuation (`actuate_*`) + SO-101 asset *(T4 bridge; maps §8 P1)*

**Objective.** Real force/torque and joint commanding once the launch SDF provisions the controllers, and a **concrete arm asset** to test against.

**Arm asset deliverable (NEW — named, blocking P1 real acceptance).** No SO-101 exists in the repo. Preferred path uses a **real robot the user already owns — JETANK**:
- (a) **JETANK (recommended).** Reuse `~/workspaces/jetank/src/jetank_description/urdf/` (`jetank.xacro` → arm + gripper + wheels, `jetank_ros2_control.urdf.xacro`, `config/ros2_control.xacro`). Convert the **Humble/Fortress-targeted xacro to a Harmonic-loadable SDF** (`xacro → urdf → gz sdf`, swap `ignition-*` ros2_control plugin → `gz-sim`/`gz_ros2_control`), add under `models/jetank/`, register in `config.model_manifest` with joint `<limit>`s. P1 acceptance commands `command_joint('jetank','<arm_joint>','pos',θ)`.
- (b) **Fallback** — a simple 2-DOF SDF authored inline, if the JETANK conversion slips. P1 acceptance **must** reference whichever asset actually ships.

The chosen asset is fixed before P1 real acceptance is written.

**Files.**
- Bridge (all new methods `async def`): extend `gazebo_interface.py` (`async apply_wrench_topic`, `async clear_wrench`, `async command_joint`, `async command_joint_trajectory`); `modern_adapter.py` — **replace** the service-based `apply_wrench` with `EntityWrench` **topic** publish to `/world/<w>/wrench` (+ `/wrench/clear`); add joint publishers (`/model/<m>/joint/<j>/cmd_{pos|vel|force}`, `/model/<m>/joint_trajectory`). `classic_adapter.py` — new methods raise `NotImplementedError`. `mock_adapter.py` — record wrench/joint, integrate in `step`.
- World/asset: `worlds/provisioned.sdf.jinja` injects per-model `JointController`/`JointPositionController`/`gz_ros2_control` blocks (from `model_manifest`); `launch/provisioned_world.launch.py` adds `gz_ros2_control` spawners + wrench/joint bridge lines; new `models/so101/` (or substitute) + manifest entry.
- Tools (both layers): new `src/gazebo_mcp/tools/actuate.py` + MCP `gz_mcp_server/server/tools/actuate.py`.

**Key signatures.**
```python
async def apply_wrench_topic(self, entity, link, force, torque, duration, persistent, world) -> bool: ...
async def clear_wrench(self, entity, world) -> bool: ...
async def command_joint(self, model, joint, mode, value, world) -> bool: ...    # mode in {pos,vel,force,cmd_vel}
async def command_joint_trajectory(self, model, traj, world) -> bool: ...        # trajectory_msgs/JointTrajectory
```

**Test migration.** Retarget `tests/unit/test_model_management.py::apply_force` and `test_multi_robot_tools.py` (fleet→`scene_spawn_many` + `actuate_*` fan-out) to the new tools. New `tests/integration/test_p1_actuation.py`. Budget: ~1 d.

**Rollback.** The wrench-transport swap is one commit (old service path deleted, topic path added) — revertible alone. Joint commanding is additive. The asset deliverable is a self-contained directory + manifest line.

**Dependencies.** P0 (provisioner OWN mode, mock integration). Real check needs the P-1-decided backend + `gz_ros2_control` + the shipped arm asset.

**Acceptance.**
```bash
GAZEBO_BACKEND=mock pixi run -e dev pytest tests/integration/test_p1_actuation.py -q
#   mock: actuate_wrench(F) then world_step(n) => entity pose moved ~½(F/m)(n·dt)²; actuate_joint(pos) => stored target
# REAL — needs ros_gz + gz_ros2_control + the shipped arm asset, so -e full:
pixi run -e full pytest -m gazebo tests/integration/test_p1_actuation.py
#   real: actuate_joint('<ARM>','<joint>','pos',0.5) => /joint_states reports <joint>->0.5±tol within T
#         where <ARM> is the SO-101 (if authored) OR the substitute model that actually exists
```

**Risks.** Wrench-as-topic must round-trip ROS→gz correctly. Joint controller only works if provisioned per-model at load (never runtime-injected). Persistent wrench can diverge sim — bounds land in P5, but track persistent wrenches from day one. If the SO-101 asset slips, the substitute keeps P1 acceptance runnable.

> **STATUS — P1 MOCK SIDE ✅ DONE & VERIFIED 2026-06-30** (`-e dev`, commits `772a2a2` bridge, `0fa55c3` tools+manifest+world/launch, `f08ef55` tests, `a2cfb88` review-fixes). Mock acceptance green (14+8 tests; `actuate_wrench(fx=10)`→`world_step(100)`→x≈0.05; joint-limit/INVALID_MODE/UNKNOWN_JOINT/INVALID_TRAJECTORY rejections; 13 tools listed). Full suite 533 passed, 10 skipped, 2 pre-existing failures. JETANK joint manifest (arm + gripper joints, faithful limits from the xacro) wheel-packaged at `src/gazebo_mcp/data/jetank_manifest.json`. Real ros_gz/Harmonic code **written but NOT live-verified** (no `-e full`/`ros_gz`/`gz_ros2_control`; arm asset SDF not yet converted).
>
> **Adversarial grill 2026-06-30: 25 raw → 24 confirmed → 0 blockers. FIXED now (a2cfb88):** INVALID_MODE + INVALID_TRAJECTORY validation on the verified path; wheel-safe manifest packaging; gripper joints; **ApplyLinkWrench system added to the world** (topic `/world/<w>/wrench` is serviced by `gz-sim-apply-link-wrench-system`/`gz::sim::systems::ApplyLinkWrench`, NOT UserCommands — corrected the false comment); honesty docstrings (mock kinematic linear-only approximation; topic-wrench persistent-until-cleared).
>
> **P1-real — DEFERRED follow-ups (need live ros_gz/Harmonic or the arm asset; none block the mock-side merge):**
> 1. **No spawnable JETANK SDF exists** — the manifest references `jetank` but `models/jetank/*.sdf` is unconverted (needs `xacro→urdf→gz sdf` + `ignition-*`→`gz-sim`/`gz_ros2_control` plugin swap; xacro tool not installed here). **Blocks real P1 acceptance** — author before live-verify. *(#8)*
> 2. **`duration`/`persistent` not implemented on the real wrench path** — `EntityWrench` topic is persistent-until-cleared; non-persistent must be implemented as a scheduled `clear_wrench` (currently only doc'd). *(#2,#20)*
> 3. **`command_joint` `vel`/`force` modes have no consumer** — only `cmd_pos` is bridged + only `JointPositionController` injected; vel/force topics are silent no-ops on the real path. Add `gz-sim-joint-controller-system` + bridge lines, or reject vel/force until provisioned. *(#3,#13-real)*
> 4. **No controller-spawner / `gz_ros2_control` config wired** in the launch — `actuate_joint_trajectory` has no consumer even once assets land. *(#21,#9)*
> 5. **PosePublisher `child_frame_id` vs `frame_id`** ambiguity for `/world/<w>/pose/info`→TFMessage joint/model naming (relates to the P0-B-real pose-cache finding). *(#10)*
> 6. **Publisher cache keyed by topic only (ignores msg type); QoS depth 10 volatile** may drop commands to late-joining gz subscribers. *(#11)*
> 7. **vel/force joints unbounded** (only `pos` is limit-checked) — safety clamps land in **P5** (`actuation_bounds`). *(#16)*
> 8. **Trajectory `time_from_start` monotonicity / negative-time not validated** on the real path; **wrench frame (world vs body) + units unspecified** at the tool boundary and `link` target not exposed to MCP callers. *(#22,#24)*
> 9. **Two divergent force paths coexist** — legacy service-based `apply_wrench`/`apply_force` vs new topic-based `actuate_wrench`; reconcile/deprecate the legacy one when the real path is verified. *(#23)*
> 10. **Mock fidelity caps (documented, by-design):** constant mass m=1.0, torque/twist not integrated, last-write-wins single wrench per entity, FastMCP `points` bare-list schema. *(#5,#12,#14,#15,#18)*

---

### P2 — Sensors one-shot (`sensor_*`) + parameters (`param_*`) *(T3 consolidation; maps §8 P2)*

**Objective.** Discovery + one-shot sensor reads (bridge caches latest sample), capped camera image, and the previously-orphaned `param_*` parameter tools. Deprecate redundant advanced-sensor tools.

**Files.**
- Tools (both layers): new `src/gazebo_mcp/tools/sensor.py` (`sensor_list`, `sensor_snapshot`, `sensor_camera_image` — async) + MCP `gz_mcp_server/server/tools/sensor.py`; new `src/gazebo_mcp/tools/param.py` (`param_list`, `param_get`, `param_set` — async over gz parameter services) + MCP `gz_mcp_server/server/tools/param.py`; merge `monitor_sensor_health` into `sensor_list`.
- Bridge (async): sensor sub-module of `modern_adapter.py` for latest-sample cache + one-shot read (`gz topic -n 1` path); parameter-service calls (`/world/<w>/.../{list,get,set}_parameters`); mock returns deterministic fixture samples/params.
- Deprecate: all `advanced_sensor_tools` except merged health.

**Key signatures.**
```python
@mcp.tool()
async def sensor_snapshot(topic: str, ctx: Context) -> dict: ...               # latest cached sample, typed
@mcp.tool()
async def sensor_camera_image(topic: str, resolution: str = "640x480",
                              quality: int = 60, ctx: Context = None) -> Image: ...  # base64-capped
@mcp.tool()
async def param_get(name: str, ctx: Context) -> dict: ...                      # gz parameter service
@mcp.tool()
async def param_set(name: str, value, ctx: Context) -> dict: ...
```

**Test migration.** Retarget `tests/unit/test_sensor_world_tools.py` (sensor portions) + `test_advanced_sensor_tools.py` → mostly stub/deprecation-coverage tests (assert deprecated tools return `OperationResult(success=False)` with a replacement hint). New `tests/integration/test_p2_sensors.py` + `test_p2_params.py`. Budget: ~1 d.

**Rollback.** New tool modules are additive; deprecated advanced-sensor tools become stubs behind `GAZEBO_LEGACY_TOOLS`. `param_*` is fully additive.

**Dependencies.** P0 bridge. Camera-bearing model in fixture/world for the real camera check.

**Acceptance.**
```bash
GAZEBO_BACKEND=mock pixi run -e dev pytest tests/integration/test_p2_sensors.py tests/integration/test_p2_params.py -q
#   sensor_list returns camera topic; sensor_snapshot(topic) returns typed sample;
#   sensor_camera_image enforces resolution/quality cap (asserts base64 byte ceiling);
#   param_list/get/set round-trip against the mock parameter store
# REAL camera/params need ros_gz, so -e full:
pixi run -e full pytest -m gazebo tests/integration/test_p2_sensors.py
```

**Risks.** Image token cost (the scaling wall, §9) — caps enforced **before** constructing the `Image`. `gz topic -n 1` CLI latency; if unacceptable, defer to optional `gz.transport` feature (P4+), not core. `param_*` service names differ Fortress vs Harmonic — verify against the P-1-decided backend.

> **STATUS — P2 MOCK SIDE ✅ DONE & VERIFIED 2026-06-30** (`-e dev`, commits `1598b6a` bridge+mock, `c4bd347` tools+FastMCP+deprecation, `bf9897d` tests, `8b95458` review-fixes). 27+10 tests; full suite **570 passed, 10 skipped, 2 pre-existing failures**. `sensor_list`/`sensor_snapshot`/`sensor_camera_image` (returns FastMCP `Image`, byte-capped) + `param_list`/`get`/`set`; **19 tools total**. Advanced-sensor tools (7) + the fake `subscribe_sensor_stream` are deprecated (flag-gated hard-stub under `GAZEBO_LEGACY_TOOLS=0`; always-on deprecation **warning**); `monitor_sensor_health` kept, its status folded into `sensor_list.health`. Mock camera frames marked `synthetic:true,backend:mock`; mock snapshots marked `typed:true`. Real ros_gz/gz paths **written but NOT live-verified** (no `-e full`/live camera/gz param services).
>
> **Adversarial grill 2026-06-30: 23 raw → 21 confirmed → 0 blockers. FIXED now (8b95458):** synthetic-frame marker (+text content block); honest `health` (reflects `active`); `param_set` scalar validation (`INVALID_PARAM_VALUE`); camera `INVALID_RESOLUTION` on ≤0 dims; visible deprecation warnings + fake-streamer guard; honest `typed` flag + corrected "typed sample" docstrings; dim-cap/b64-guard comments.
>
> **P2-real — DEFERRED follow-ups (need live ros_gz/gz; none block the mock-side merge):**
> 1. **Param transport likely wrong** — modern `param_*` calls `rcl_interfaces` services at a **guessed** node path `/world/<w>/gz_parameters`; Harmonic params are **gz-transport** (`gz.msgs.ParameterValue`), not auto-bridged to ROS. Verify against a live graph; route via `gz service`/`gz param` CLI or gate with a clear `PARAM_BACKEND_UNAVAILABLE` (currently `param_get` masks unavailability as `UNKNOWN_PARAM`). *(#2,#18)*
> 2. **Modern `sensor_snapshot` returns raw `gz-text`**, not the typed dict the mock provides — parse the `gz topic -e` echo into typed per-sensor shapes (now honestly marked `typed:false` + TODO). *(#1,#5)*
> 3. **`list_sensors` type-classification is topic-name substring guessing** (false positives / missed sensors) and real health is hardcoded `"unknown"` — use scene/topic-type info once live. *(#6,#21)*
> 4. **`gz topic -e` uses `text=True` for binary msg types** — may mangle binary samples (UnicodeDecodeError handled, but masks real captures). *(#7)*
> 5. **Param-service clients lazily created, never destroyed** (minor leak on the real path). *(#8)*
> 6. **Legacy 69-tool `sdk_app` surface still advertises the 7 deprecated tools + `subscribe_sensor_stream` regardless of the flag** — filter them from `_build_registry` when `GAZEBO_LEGACY_TOOLS=0` (ties into the P3 single-server unification). *(#17)*
> 7. **Completeness:** lean `sensor_list` dropped the legacy `response_format` token-budget control; camera output fixed to PNG with no requestable `format`/`quality` honoring; `param_set` has no allowlist/namespace check (arbitrary param creation). *(#19,#20,#15)*

---

### P3 — Streamable HTTP + sessions + resources *(T2 transport; the breaking change; maps §8 P3)*

**Objective.** Add Streamable HTTP with per-session bridges and subscriptions; expose `gz://sensor/<name>` resources (subscribe→updated→read). **stdio stays the default throughout a dual-transport window** — HTTP is opt-in here and only becomes default after its acceptance is green and the window closes. Validate progress-over-HTTP and the subscribe round-trip. Multi-client safe.

**python-sdk #953 spike (sub-task).** The pin is `mcp` **1.27.1** (SDK-bundled FastMCP). Before depending on progress-over-Streamable-HTTP, run an **empirical spike** on 1.27.1: emit ≥3 `report_progress` calls over HTTP and assert every `notifications/progress` arrives in order. Decide push-vs-poll by the spike result, not by faith. There is **no separate `fastmcp` upgrade** to chase.

**Files.**
- New: `gz_mcp_server/server/session.py` (`GazeboSession`), `gz_mcp_server/server/resources/sensors.py` (`gz://sensor/{name}` template + subscribe/updated wiring).
- Edit: `gz_mcp_server/server/app.py` (per-session lifecycle keyed by `Mcp-Session-Id`, stored in lifespan context), `gz_mcp_server/server/fastmcp_main.py` (`--http`/`--stdio` switch, **default `--stdio`**), `src/gazebo_mcp/tools/_bridge_helper.py` (`get_bridge()` reads session from `Context`), `pixi.toml` (`serve-http` task, additive).

**Key signatures.**
```python
@dataclass
class GazeboSession:
    bridge: GazeboBridgeNode          # async interface
    connection_manager: ConnectionManager
    subscriptions: dict[str, SensorSub]   # uri -> latest-sample cache + sub handle
    real: bool
    @classmethod
    async def create(cls, config) -> "GazeboSession": ...
    async def aclose(self) -> None: ...

@mcp.resource("gz://sensor/{name}")
async def sensor_resource(name: str, ctx: Context) -> dict:
    return get_session(ctx).subscriptions[f"gz://sensor/{name}"].latest   # capped
```
One rclpy executor/spin thread process-wide; one `Node` per session. Session torn down (`await aclose()`, unsubscribe all) on close.

**Test migration.** New `tests/integration/test_p3_http.py`. The existing 410 unit tests + P0–P2 integration tests must stay green over the **stdio** path (still default). Add a test asserting `--stdio` remains the default. Budget: ~1 d.

**Rollback.** HTTP is additive and opt-in (`--http`); stdio is untouched and default. Revert = drop the HTTP/session/resource files; stdio server keeps working. The dual-transport window is the escape hatch — no removal date for stdio-as-CI-transport.

**Dependencies.** P0–P2.

**Acceptance.**
```bash
# stdio path (still default) stays green:
pixi run -e dev pytest tests/unit/ -q
# HTTP path, opt-in:
pixi run serve-http &                          # mcp.run(transport="streamable-http", port=8931)
pixi run -e dev pytest tests/integration/test_p3_http.py -q
#   asserts: two Mcp-Session-Id sessions have isolated bridges/subscriptions;
#            resources/subscribe(gz://sensor/cam) => notifications/resources/updated (bare ping, NO data)
#            => resources/read returns cached sample;
#            #953 SPIKE: a >=3-update report_progress op delivers EVERY notifications/progress in order on 1.27.1
```

**Risks.** **python-sdk #953** (progress lost over HTTP) — gated by the spike above; fallback is op-id + `world_get_op_status(op_id)` poll (same notify-then-poll honesty). Session leakage if teardown misses a subscription — assert isolation explicitly. rclpy is sync internally — keep one executor, per-session nodes.

---

### P4 — Jetty `sim_*` (cross-sim portability, optional) *(maps §8 P4)*

**Objective.** Add the REP-2018 `simulation_interfaces` path as an alternate adapter behind the same async `GazeboInterface`, for cross-simulator portability.

**Files.**
- New: `src/gazebo_mcp/tools/sim.py` + MCP `gz_mcp_server/server/tools/sim.py` (`sim_spawn`/`sim_delete`/`sim_reset`/`sim_step`/`sim_get_features` — thin async over `scene_*`/`world_*` + `get_simulator_features`); optional `src/gazebo_mcp/bridge/adapters/sim_interfaces_adapter.py`.
- Optional: `pixi` feature `gz-transport` (sensor latency only, contained to the sensor sub-module).

**Test migration.** New `tests/integration/test_p4_sim.py`. No retargeting of existing tests (purely additive surface). Budget: ~0.5 d.

**Rollback.** Entirely additive and non-default; revert = drop the `sim_*` modules.

**Dependencies.** P0–P3. Jetty/`simulation_interfaces` available for the P-1-decided backend.

**Acceptance.**
```bash
pixi run -e full pytest -m gazebo tests/integration/test_p4_sim.py -q
#   sim_get_features reports supported ops; sim_spawn/sim_step parity with scene_spawn/world_step on same backend
GAZEBO_BACKEND=mock pixi run -e dev pytest tests/integration/test_p4_sim.py -q   # mock parity
```

**Risks.** `simulation_interfaces` maturity on the target Gazebo release; keep `sim_*` strictly optional and non-default.

---

### P5 — Hardening *(maps §8 P5)*

**Objective.** Actuation bounds/safety, op-id + progress (or poll fallback from the P3 spike) for long ops, image token-cost caps, and docs stating the notify-then-poll truth.

**Files.**
- New: `src/gazebo_mcp/utils/actuation_bounds.py` (called from `gazebo_bridge_node.py` **before** the adapter, so mock/modern/classic enforce identically).
- Edit: `src/gazebo_mcp/bridge/gazebo_bridge_node.py` (op-id/progress registry; long async methods accept `progress_cb`); `src/gazebo_mcp/tools/sensor.py` (finalize image ceiling); README/docs (notify-then-poll, CPU-only, GUI-only, `-e full` for real tests, the chosen backend).

**Key signatures.**
```python
# utils/actuation_bounds.py
def enforce_wrench(force, torque, duration, persistent, cfg) -> Wrench: ...   # clamp or raise on strict
def enforce_joint(model, joint, mode, value, limits, cfg) -> float: ...        # clamp to [lower,upper]/limits
```
Bounds: magnitude caps (`max_force_n=1000`, `max_torque_nm=500`, per-joint effort/velocity); persistent-wrench registry + `max_persistent_wrenches` + require explicit `actuate_wrench_clear`; joint limits from provisioned URDF/SDF (ATTACH mode warns "unverified"); per-entity rate cap (default 50 Hz); image base64 ceiling.

**Test migration.** New `tests/integration/test_p5_bounds.py`. Retarget any actuation unit tests to assert clamping. Budget: ~0.5 d.

**Rollback.** Bounds are enforced at a single chokepoint (`gazebo_bridge_node` pre-adapter); revert = make `enforce_*` pass-through. Progress registry is additive.

**Dependencies.** P1 (actuation), P2 (images), P3 (#953 spike result decides push vs poll).

**Acceptance.**
```bash
GAZEBO_BACKEND=mock pixi run -e dev pytest tests/integration/test_p5_bounds.py -q
#   over-limit wrench => clamped (or rejected under strict_bounds); persistent wrench requires clear;
#   rate flood => throttled; image over-ceiling => downscaled/rejected
pixi run -e dev pytest tests/unit/ -q
```

**Risks.** Bounds defaults too tight/loose for a given robot — make them `GazeboConfig`-overridable, document defaults. Long-op progress depends on the P3 #953 spike (push vs poll).

---

## 6. Backward-compatibility & deprecation plan

**Principle.** The underlying `tools/*.py` async function signatures and `OperationResult` stay stable; the per-session bridge is reached via FastMCP `Context`, not a global, so consolidation is the only churn at the tool layer. Only **P3 changes the wire protocol**, and it ships with a dual-transport window (stdio stays default).

**Tool-surface retirement (69 → 24):**
1. **Aliases for survivors (one minor release).** Each renamed/merged tool keeps a deprecated `gazebo_*` alias forwarding to the new namespaced tool, emitting a deprecation warning in description + `metadata`. Aliases register behind `GAZEBO_LEGACY_TOOLS=1` (default ON during the window, OFF after).
2. **Hard deprecations (instruction-emitters / GUI-only / external-stack — the ~46).** No Transport home; removed at the consolidation PRs but, for the window, replaced by **stub tools** returning `OperationResult(success=False)` whose `error`/`suggestions`/`example_fix` explain the replacement (e.g. "RViz launch is out of scope; run `rviz2` externally" or "use `sensor_camera_image` instead of `segment_camera_image` + client-side inference"). Prevents existing agent prompts from hard-failing with unknown-tool errors.
3. **Version bump.** Consolidation lands as a **minor** bump while aliases/stubs exist; removing them is the **major** bump. Document the 4.A mapping in `CHANGELOG`/README so callers migrate names mechanically.
4. **Transport dual-window (P3).** stdio stays the **default** and CI transport after `streamable-http` becomes opt-in/default; announce a removal date for *stdio-as-default* only, never for stdio-in-CI.
5. **Framework dual-window (Step 0).** The old hand-rolled server (`gz_mcp_server/server/server.py` + `mcp_tool.py` + adapters + `handle_message`) stays runnable via the `gazebo-mcp-server` entry point until the FastMCP path (`gazebo-mcp-fastmcp`) is green across P0–P2. Deletion of the old layer is a **separate later PR**, never bundled with the PR that introduces FastMCP.

**Keep mock-mode + tests green throughout.** Every phase's mock acceptance runs under `GAZEBO_BACKEND=mock` in `-e dev`; every **real** acceptance runs `-m gazebo` under `-e full`/`-e sim`. The 500-collected / 410-unit suite is a gate at P-1, Step 0, P0, and each subsequent phase. The mock adapter (P0) replaces scattered inline per-tool mock data, so deprecating tools removes their inline mocks without losing CI coverage.

---

## 7. Cross-cutting risks + mitigations

| Risk | Where it bites | Mitigation |
|---|---|---|
| **`mcp/` namespace shadow** — local pkg hides the installed SDK; FastMCP "missing" | everything | **P-1 first.** Rename to `gz_mcp_server/`; acceptance asserts `import mcp` resolves to site-packages and `mcp.server.fastmcp` imports. |
| **Wrong dependency hunt** — chasing standalone `fastmcp` 2.x (unresolvable on conda-forge) | Step 0 | FastMCP is **already** in `mcp` 1.27.1. No new dependency. Use `mcp.server.fastmcp.FastMCP`. |
| **Sync/async mismatch** — building an executor/contextvars shim for an already-async bridge | Step 0–P5 | Tools are `async def` awaiting the async bridge directly. No `_run` offload, no contextvars. |
| **Backend assumption** — assuming Harmonic while the world is Fortress | P-1/P0/P1 | P-1 decides Fortress-stay vs Harmonic-migrate against RoboStack Jazzy `ros_gz`; world template + service names follow that decision. |
| **Missing SO-101 asset** — acceptance references a model that doesn't exist | P1 | Named P1 deliverable to author SO-101, OR a substitute model that exists at run time; acceptance names whichever shipped. |
| **Running real tests in `-e dev`** — no `ros_gz` there | P0–P4 real checks | All `-m gazebo` real acceptance runs `-e full`/`-e sim`; only mock runs in `-e dev`. |
| **python-sdk #953** — `report_progress` lost/out-of-order over Streamable HTTP on 1.27.1 | P3 long ops | Empirical P3 spike on 1.27.1 asserts ordered delivery. Fallback: op-id + `world_get_op_status(op_id)` poll. Decide by spike, not faith. No separate fastmcp upgrade. |
| **Image token cost** — base64 frames blow the context budget | P2/P5 `sensor_camera_image` | Enforce `resolution`/`quality` caps + base64 byte ceiling **before** constructing the `Image`; return FastMCP `Image`. |
| **`/entity/system/add` fragility** — runtime system injection crashes gz | P0/P1 own-SDF | **Provision at load only.** `WorldProvisioner` renders SDF + launches; never injects into a live world. Robots carry their controller `<plugin>` blocks at spawn time. |
| **GUI-only gaps genuinely unreachable** | consolidation | Deprecate, do not re-home. Substitute where possible (camera sensor + `sensor_camera_image`). State plainly in docs. |
| **CPU-only physics** — RTF < 1 on large worlds | all phases | Expose RTF/step honestly via `world_set_physics`/`world_get_stats`; no GPU/real-time guarantees. |
| **Broken pose readback regressing** — wrong `/pose/info` msg type | P0 | Exact `Pose_V → TFMessage` typing; acceptance asserts non-zero pose equals spawn pose. |
| **Deleting the old server too early** | Step 0 | Old layer retained behind a second entry point/flag through P0–P2; deleted only in a later PR after FastMCP acceptance is green. |
| **Session state leakage** between concurrent clients | P3 | Per-session `GazeboSession` (async bridge + subscriptions) in lifespan; teardown unsubscribes all; isolation asserted. |
| **Test migration treated as free** | every phase | Per-phase test-migration line items with day budgets (§8); "green throughout" is work, not a side effect. |

---

## 8. Effort/sequencing estimate + recommended first PRs

Estimates revised **up** to reflect the namespace rename, backend decision, SO-101 asset, and explicit per-phase test migration. The four tracks (T1 framework / T2 transport / T3 consolidation / T4 bridge) are separately shippable; the table notes which track each phase advances.

| Phase | Track(s) | Scope | Rough effort | Gating dependency |
|---|---|---|---|---|
| **P-1** | (prereq) | rename `mcp/`→`gz_mcp_server/`, fix all imports/entry points, backend (Fortress vs Harmonic) decision pinned to RoboStack `ros_gz` | **1–2 d** | — |
| Step 0 | T1 | SDK-bundled FastMCP scaffold (flag-gated, **old server retained**), 69-tool parity, in-memory-client lifecycle test | **3–4 d** | P-1 |
| P0 | T4 + T3 | mock adapter, fix pose readback, async step/physics/seed, provisioner, world+launch (decided backend), `world_*`/`scene_*`, **+ test migration ~1.5 d** | **6–9 d** | Step 0 |
| P1 | T4 | `actuate_*` (wrench topic + joint), controller provisioning, **SO-101 asset (or substitute)**, **+ test migration ~1 d** | **5–8 d** | P0 + backend + gz_ros2_control + asset |
| P2 | T3 | `sensor_*` one-shot + caps, **`param_*`**, deprecate advanced sensors, **+ test migration ~1 d** | **4–6 d** | P0 |
| P3 | T2 | Streamable HTTP (opt-in, **stdio stays default**), sessions, sensor resources, **#953 spike on 1.27.1**, **+ test migration ~1 d** | **6–8 d** | P0–P2 |
| P4 | (additive) | `sim_*` (optional) | **2–3 d** | P0–P3 + Jetty |
| P5 | (cross) | `actuation_bounds`, op-id/progress (per #953 spike), image caps, docs, **+ test migration ~0.5 d** | **3–5 d** | P1/P2/P3 |

**Sequencing notes.**
- **P-1 is the root.** Nothing imports FastMCP until the shadow is gone. It also fixes the backend decision every later world template depends on.
- **Bridge fixes (P0) precede transport value** — without a real mock adapter and a working pose readback, no phase has an honest acceptance test.
- **The four tracks ship independently.** T1 (Step 0) and T4 (P0) can proceed in parallel after P-1 since the bridge work is in `src/gazebo_mcp/bridge/` and the framework work is in `gz_mcp_server/`. T2 (P3) is the only breaking wire change and is the last to flip default.

**Recommended first PR — "P-1: resolve the `mcp/` namespace collision + backend decision."**
- Rename `mcp/` → `gz_mcp_server/`; fix every `from mcp.server...` import, `adapters/__init__`, `server.py`, the `pyproject`/`pixi` entry points and run scripts.
- Record the Fortress-stay-vs-Harmonic decision pinned to RoboStack Jazzy `ros_gz`.
- **Gate:** `import mcp` resolves to site-packages; `from mcp.server.fastmcp import FastMCP` succeeds; `pytest -q` stays at 500 collected / 410 unit green.

**Recommended second PR — "Step 0: FastMCP scaffold on stdio (flag-gated, old server retained)."**
- Add `gz_mcp_server/server/app.py` + `fastmcp_main.py` (SDK-bundled FastMCP, `lifespan` holds the async `GazeboSession`); port the 69 tools 1:1 as `async @mcp.tool` for parity; add the `gazebo-mcp-fastmcp` entry point **alongside** the retained `gazebo-mcp-server`.
- **Do NOT** delete `mcp_tool.py`/adapters/`handle_message` in this PR.
- **Gate:** `pytest tests/unit/ -q` stays at 410 green; the in-memory-client `initialize → tools/list` parity test confirms 69 tools and schema shape.

Both PRs are self-contained and reversible, touch no bridge behavior, and unblock every subsequent track to author tools directly as async `@mcp.tool`.

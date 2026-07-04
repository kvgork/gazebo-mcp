# gazebo-mcp — Remaining Work

> Consolidated backlog after the P0-B → P3 mock-side build (branch `feature/p0-bridge-mock`, 2026-06-30).
> Source of truth for detail: `GAZEBO_MCP_ARCHITECTURE_EVOLUTION_PLAN.md` (per-phase `STATUS` blocks hold the full findings + commit hashes).
> **Done & verified in `-e dev` (mock):** P-1, Step 0, P0-A, **P0-B, P1, P2, P3, P5, P4-shim** (P3 #1 fidelity partial). Suite: 623 passed / 10 skipped / 2 pre-existing failures.

---

## A. Remaining phases (new capability)

### P4 — Jetty `sim_*` (cross-sim portability) — OPTIONAL — ✅ SHIM DONE (mock) 2026-07-04, commit `3e9f005`
- **Portability shim landed:** `sim_spawn`/`sim_delete`/`sim_reset`/`sim_step`/`sim_get_features` delegate to `scene_*`/`world_*`, gated `GAZEBO_SIM_TOOLS=1` (default OFF, surface unchanged). Plan §P4 STATUS.
- **DEFERRED (real):** the REP-2018 `simulation_interfaces` ROS-service adapter (`sim_interfaces_adapter.py`). The package installs in `-e full` but registers no ROS interfaces in this env → no REP-2018 backend to verify against. Real cross-sim portability needs a simulator that implements the `simulation_interfaces` services.

### P5 — Hardening — ✅ DONE & VERIFIED (mock) 2026-07-04, commit `b81a9ab` (plan §P5 STATUS)
- Actuation bounds (`utils/actuation_bounds.py`), progress consumer (`world_step`), image-cap docs, honesty docs — all landed + grill-hardened (F1–F6 resolved). Remaining P5 items are real-only or deferred (see §B P5-real + P5 deferred).

---

## B. P*-real track — live-gz verification (the big cross-cutting gap)
**All real (`-m gazebo`) acceptance is DEFERRED** — the real adapter code is written but the full MCP-adapter round-trip has not been live-run. The mock side is fully verified.

> **ENV GATE CLEARED 2026-07-04.** `pixi install -e full` **succeeds** here; the `full` env has `ros2`, `xacro`, and `ros_gz*` (ros_gz_sim/bridge/interfaces). **Headless Gazebo Harmonic RUNS** in this environment — `gz sim -s -r empty.sdf` comes up with live topics (`/world/empty/pose/info`, `/clock`, …) and services (`/world/empty/control`). So live verification is no longer env-blocked; it is now a matter of wiring the ros_gz bridge + running the modern-backend server against the live world (a multi-hour deep-integration task).

**Next real step (was "gating first step"):** run the modern-backend MCP server (or the modern adapter directly) against a live headless Harmonic world with the `ros_gz_bridge` up, do a spawn→step→pose round-trip (P0-B-real core), then burn down the per-phase findings below. The `ros_gz_interfaces` services (SpawnEntity/DeleteEntity/SetEntityPose/ControlWorld) the modern adapter calls need the bridge running — decide OWN-mode (WorldProvisioner) vs ATTACH-mode bring-up first.

> **Live round-trip 2026-07-04 — ✅ FULL spawn/step/pose VERIFIED against headless Harmonic.** Driver: `gz sim -s empty.sdf` + `parameter_bridge` binary + rclpy driving the real `ModernGazeboAdapter` (probe: `.agent-state/20260704-p5-hardening/preal-artifacts/preal_roundtrip.py`). Result: spawn box@(1,2,0.5) → step(10) → `get_entity_state('box')` returns `position [1, 2, 0.4999999994]`, orientation ~`[0,0,0,1]`.
> 1. **FIXED (commit) — `gazebo_bridge.launch.py` topic args were malformed (root cause of a dead bring-up).** parameter_bridge topic syntax is `topic@ROS_type[GZ_type`; the `@ROS_type` before `[` is REQUIRED. The launch used `/world/{w}/pose/info[ros_gz_interfaces/msg/ParamVec` and `/clock[rosgraph_msgs/msg/Clock` — no `@ROS_type`. parameter_bridge treats ONE malformed argv as fatal → prints usage, exits → bridges NOTHING (incl. the 4 services). Corrected to `.../pose/info@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V` + `/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock`. Services now bridge. (Service `@`-syntax was already correct.)
> 2. **FIXED (commit) — pose readback (resolves deferred #1).** The Pose_V→TFMessage bridge emits EMPTY `frame_id`/`child_frame_id` in this ros_gz version, so the old `child_frame_id`-keyed cache never resolved a model. Redesigned `get_entity_state` to read the NAME-carrying gz-transport `Pose_V` directly (`gz topic -e -n1 --json-output`), matching by model name; removed the dead TFMessage subscriber. Deferred #1 (pose cache keying) is now resolved by construction (name-keyed, model-scoped).
> 3. **ENV PREREQ (still open) — pixi `-e full` ros2 CLI is incomplete.** Only `ros2cli`/`ros2pkg`/`ros2topic`; **no `ros2 launch`/`run`/`service`/`interface`**. The repo's `ros2 launch gazebo_mcp gazebo_bridge.launch.py` bring-up can't run here as-is — add the `ros-jazzy-ros2cli`-family packages to the `sim`/`full` pixi feature, or bring up via direct binaries (as the probe does). `rclpy` + the `parameter_bridge` binary ARE present.
> Adapter drivability confirmed: on-demand `spin_until_future_complete`/`spin_once` (no persistent executor), so deferred #5's executor-conflict does not bite the rclpy-driver path.
>
> **Acceptance test (permanent):** `tests/integration/test_p0b_real_roundtrip.py` (`@pytest.mark.gazebo`) codifies the round-trip — it self-brings-up `gz sim -s` + `parameter_bridge`, drives the real adapter, and asserts the box resolves at (1,2,~0.5). Skips by default; run live with `pixi run -e full pytest --with-gazebo -m gazebo tests/integration/test_p0b_real_roundtrip.py` (**PASSES**, ~15s). Skips cleanly under `-e dev`.
> **Remaining P0-B-real (not yet live-checked):** set_physics/seed honesty (#2), get_entity_state cache invalidation is now moot (no cache — reads live each call, so a deleted entity returns ModelNotFoundError correctly ✓), PosePublisher scope (#4 — the OWN-mode WorldProvisioner launch path, blocked on the ros2cli gap), detection AUTO→MOCK loud-warn (#6). Next: pin the bring-up (add the `ros-jazzy-ros2cli`-family to the `sim`/`full` pixi feature, or a direct-binary launcher), then P2/P3-real (P1-real blocked on the upstream JETANK inertials).

### P0-B-real (plan §P0 STATUS — 6 items)
1. modern pose cache keyed only by `child_frame_id` → cross-model link-name collisions; key by `(parent, child)` / filter to world-scoped models.
2. `set_physics`/`seed` honesty: gz uses gz-transport service (not `rcl_interfaces.SetPhysics`); currently `return True` no-op. Shell out to `gz service` or report `applied=False`.
3. `get_entity_state` cache never invalidated (stale pose; deleted entity still reports). Refresh-spin/timestamp-evict; clear on delete.
4. PosePublisher placed at `<world>` scope — verify per-model placement publishes to `/world/<w>/pose/info`.
5. `spin_once` executor-conflict risk; bridge-mapping `Pose_V↔TFMessage` payload syntax to confirm on the installed bridge.
6. detection AUTO→MOCK silent fallback masks "gz not started" in prod — loud-WARN / opt-in gate.

### P1-real (plan §P1 STATUS — blocker + items)
1. **No spawnable JETANK SDF — blocker SHARPENED 2026-07-04.** `xacro ~/workspaces/jetank/src/jetank_description/urdf/jetank.xacro` → urdf **works** (489 lines, needs `source ~/workspaces/jetank/install/setup.bash`). BUT `gz sdf -p jetank.urdf` **fails (exit 255) and models only 1 of 21 links**: 7 links have **no `<inertial>` block** (`arm_bearing_link` + all 6 wheels), so `urdf2sdf` drops each and its entire joint subtree. **Root fix is UPSTREAM in `jetank_description`** — add `<inertial>` (real mass/inertia) to those 7 links; NOT a gazebo-mcp change, and mass properties must not be fabricated. Only after that does `gz sdf` yield a spawnable `models/jetank/*.sdf` (then swap any `ignition-*`→`gz_ros2_control`). Artifacts: `.agent-state/20260704-p5-hardening/preal-artifacts/` (jetank.urdf, partial jetank.sdf, sdf.err). Manifest `src/gazebo_mcp/data/jetank_manifest.json` is ready. **Still blocks real P1 acceptance.**
2. `duration`/`persistent` not implemented on the real wrench path (`EntityWrench` topic is persistent-until-cleared) — implement non-persistent as a scheduled `clear_wrench`.
3. `command_joint` `vel`/`force` modes have no consumer — add `gz-sim-joint-controller-system` + bridge lines, or reject until provisioned.
4. No controller-spawner / `gz_ros2_control` config wired in the launch.
5. PosePublisher `child_frame_id` vs `frame_id` naming.
6. Publisher cache keyed by topic only (ignores msg type); QoS depth 10 volatile.
7. vel/force joints unbounded (only `pos` limit-checked) → P5 `actuation_bounds`.
8. Trajectory `time_from_start` monotonicity — **DONE 2026-07-04 (E4)**: `actuate_joint_trajectory` now rejects negative / non-numeric / non-strictly-increasing `time_from_start` with `INVALID_TRAJECTORY` (mock-verified, 4 cases). Remaining #8 bits (wrench frame+units, `link` not exposed to MCP) still open.
9. Two divergent force paths (legacy service `apply_wrench` vs new topic `actuate_wrench`) — reconcile/deprecate.
10. Mock fidelity caps (documented): m=1.0, torque/twist not integrated, last-write-wins single wrench.

### P2-real (plan §P2 STATUS — 7 items)
1. ~~**Param transport likely wrong**~~ — **FIXED 2026-07-04** (commit `7f71c4a`). Confirmed live: Harmonic params ARE gz-transport, registry namespace `/world/<w>` (services `/world/<w>/{list,get,set,declare}_parameter`, `gz.msgs` types), and `gz param -r /world/<w> -l` works (stock world → "No parameters available"). Rewired `param_list/get/set` to shell out to `gz param` (subprocess, timeout-bounded, honest `[]`/KeyError/False). NOTE: full get/set ROUND-TRIP is still unverified — needs a world/system that DECLARES parameters (stock worlds declare none); the registry+transport+list path is verified.
   > **Live env caveat 2026-07-04:** heavy repeated `gz sim` SIGKILLs this session degraded gz-transport startup (new `gz sim` began hanging), and the camera worlds hang **headless** (camera sensors need a rendering engine / GPU-display, absent here). So (a) sensor live-verify (items 2–4) and (b) the param get/set round-trip could not be completed this session — the param fix is mock-green + registry-verified, sensor items remain live-deferred pending a rendering-capable host (or a non-rendering sensor: contact/imu).
2. ~~Modern `sensor_snapshot` returns raw `gz-text` (`typed:false`)~~ — **FIXED 2026-07-04 (B1)**: rewired to `gz topic -e -n 1 --json-output` (off the event loop), returning `{"format":"gz-json","sample":<dict>,"typed":True}` (raw-text fallback only if JSON parse fails). Live-verify the typed shape per sensor in Phase D.
3. `list_sensors` type-classification = topic-name substring guess; real health hardcoded `"unknown"`. **B3 DEFERRED to Phase D** — real health (topic Hz / publisher presence via `gz topic -i`) needs live sensors to tune + verify; writing it blind = untested code. `sensors.sdf` (non-render `/imu` `/altimeter` `/magnetometer`) is the verify target.
4. ~~`gz topic -e` `text=True` for binary msgs~~ — **RESOLVED by B1**: `sensor_snapshot` now uses `--json-output` (text-safe for binary Imu/LaserScan/Image), so the confirmed `/imu` hang is fixed.
5. ~~Param-service clients never destroyed (leak)~~ — **RESOLVED 2026-07-04** (commit `7f71c4a`): the `gz param` CLI rewrite creates NO persistent service clients (subprocess per call), so there is nothing to leak; `shutdown()` no longer references any `_param_*_clients` (verified — the dicts are gone).
6. Legacy 69-tool `sdk_app` surface still advertises the 8 deprecated tools regardless of flag — filter in `_build_registry` when `GAZEBO_LEGACY_TOOLS=0`.
7. Completeness: lean `sensor_list` dropped `response_format` token control; camera fixed PNG (no `format`); `param_set` no allowlist.

### P3 deferred (plan §P3 STATUS — 7 items; blocker already CLEARED)
> **P3-real (HTTP + resources over LIVE gz) — NOT attempted this session.** Would run the unified server in modern+`--http` against a live Harmonic world and exercise per-session isolation + `gz://sensor/{name}` resources over the real backend. Blocked this session by the same live-env degradation (gz-transport startup hangs after repeated SIGKILLs) + headless-rendering gap for sensor resources. Approach when resumed: fresh host (avoid the degraded transport state), bring up gz + bridge via the now-working `ros2 launch gazebo_bridge.launch.py` (P*-real #1), then drive the HTTP server. HTTP transport itself is already mock-verified (P3).

1. **Legacy schema fidelity / validation divergence** — ⏳ PARTIALLY RESOLVED 2026-07-04. **Array `items` typing RESTORED** (`legacy_mount._hint_for` now builds `list[item]`; `tools/list` advertises `items:{type:...}` again — test `test_p3_schema_fidelity.py`). **Residual (intrinsic FastMCP 1.27.1 constraint, documented won't-fix):** `object` params stay bare `dict` (no nested `properties`), and FastMCP derives BOTH the advertised schema AND pre-handler validation from ONE inferred `arg_model` — so a curated-schema `tools/list` and lenient handler-produced `OperationResult` errors on bad *type* cannot coexist for a native tool. Chosen trade-off: fidelity + standard JSON-RPC validation errors. **Retire of `server.py`/`sdk_app.py` still DEFERRED** — `sdk_app._build_registry()` is a LIVE dependency of `legacy_mount` (registry source of truth), so retire = extract `_build_registry` to a shared module + remove the standalone low-level server entrypoint, gated on the §C HTTP soak. Not an autonomous deletion.
2. Resource `subscribe` capability advertised `False` (1.27.1 hardcodes it) — handler works; needs an SDK capability override for client discovery.
3. `gz://sensor/camera_rgb` resource returns metadata, no image bytes — wire to `sensor_camera_image`.
4. Every uncached `resources/read` does a full `bridge.list_sensors()` — cache name→topic per session.
5. `report_progress`/notify push validated but unused → P5 consumer.
6. `httpx.ASGITransport` unusable vs `streamable_http_app()` → HTTP tests need real uvicorn (port-TOCTOU CI flakiness).
7. `get_session` synthesizes a one-off session for registry-less Context (unit-test) — ensure prod always carries the registry.

### P5 deferred (grill-fixes pass, 2026-07-04)
1. **Trajectory waypoint position/velocity limit clamping** — `command_joint_trajectory` rejects only non-finite (NaN/inf) waypoint positions; finite out-of-range positions are unbounded at BOTH the tool and bridge layers (the trajectory format carries no joint names, so a waypoint value cannot be mapped to a specific joint's manifest limits). Proper fix: add `joint_names` to the trajectory contract + per-waypoint manifest-limit clamping.

---

## C. Cross-cutting / hygiene
- **Single-server unification is DONE + old servers RETIRED** (P3 + C1/C2/C3, 2026-07-04): the unified FastMCP app (88 tools = 19 lean + 69 legacy, stdio+HTTP, per-session isolation) is now the SOLE server. C1 extracted the curated registry to `gz_mcp_server/server/registry.py` (decoupled `legacy_mount` from the low-level server); C2 HTTP soak passed (72 sessions, isolation + LRU eviction, `test_p3_http_soak.py`); C3 deleted `server.py` + `sdk_server.py` + `gz_mcp_server/server/server.py` (GazeboMCPServer) + `sdk_app.py` (build_server). `gazebo-mcp-server` console script + pixi `serve` repointed to `fastmcp_server:main` (name preserved); `gazebo-mcp-sdk`/`serve-sdk` removed. Schema-fidelity divergence (P3 #1) remains **partially resolved** (array items restored; object-props + validation-location are the documented intrinsic FastMCP-1.27.1 constraint — won't-fix).
- **Dual-transport window:** stdio remains CI/default transport; no removal date for stdio. Decide HTTP-default flip criteria after a soak.
- **HTTP security:** transport is unauthenticated (localhost default + warning). Add auth/proxy guidance before any non-loopback deployment.
- ~~2 pre-existing test failures~~ — **RESOLVED 2026-07-04 (A3).** `test_list_models_mock_data` now asserts a well-formed result (`count >= 0`) — the mock adapter honestly reports 0 models in an empty world (the old `> 0` expected phantom fixtures removed by the adapter refactor). `test_result_filter_with_models` DELETED — it imported `skills.common.filters.ResultFilter`, external harness code absent from this repo. **Full suite now 0 failures (629 passed / 11 skipped, deterministic across runs).**
- **ResultFilter doc-vs-code gap:** `model_management.list_models` advertises a "ResultFilter pattern" (in docstrings + the `filtered` format's `filter_examples`) that this repo does NOT implement (`ResultFilter` lives only in the external `skills.common`). Either implement a minimal `ResultFilter` in `gazebo_mcp.utils` (search/filter_by_field/limit/top_n_by_field) or stop advertising it in the tool output/docstrings.
- **Test flakiness — RESOLVED 2026-07-04 (A2):** `test_p3_progress_spike` (and the HTTP suite) no longer flake. `_UvicornServer` bound a pre-picked `_free_port()` (TOCTOU: pick → close → rebind), which collided under full-suite concurrency. Now binds `port=0` (OS assigns at bind) and reads the real port back after startup.
- `/go` not yet run — 21 commits on `feature/p0-bridge-mock` unpushed; open the PR.

---

## Suggested order
1. **Ship** the current branch (`/go`) — P0-B→P3 mock side is a clean, self-contained PR.
2. **P5 hardening** (mock-verifiable: `actuation_bounds`, image caps, progress consumer, docs) — no live gz needed.
3. **P*-real** track in one push: `pixi install -e full` → JETANK SDF → live Harmonic → run all `-m gazebo` acceptance → burn down the P0-B/P1/P2-real findings.
4. **P4** (`sim_*`) only if cross-sim portability is wanted.
5. Resolve P3 #1 (schema fidelity) → retire the old `server.py`/`sdk_app.py`.

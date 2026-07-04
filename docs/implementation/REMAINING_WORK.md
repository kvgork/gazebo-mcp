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

> **Live-attempt findings 2026-07-04 (bring-up probed, round-trip not completed):**
> 1. **FIXED — `gazebo_bridge.launch.py` pose/info mapping was wrong.** gz `/world/{w}/pose/info` publishes `gz.msgs.Pose_V` (confirmed via `gz topic -i`); the adapter subscribes as `tf2_msgs/msg/TFMessage` — but the launch bridged it as `ros_gz_interfaces/msg/ParamVec`, so pose readback silently got nothing. Changed to `tf2_msgs/msg/TFMessage` (commit below). Addresses P0-B-real #4/#5.
> 2. **ENV PREREQ — pixi `-e full` ros2 CLI is incomplete.** Only `ros2cli`/`ros2pkg`/`ros2topic` extensions install; **no `ros2 launch`/`run`/`service`/`interface`**. So the repo's documented `ros2 launch gazebo_mcp gazebo_bridge.launch.py` bring-up CANNOT run in this env as-is. Either add the missing `ros-jazzy-ros2cli`-family packages to the `sim`/`full` pixi feature, or bring up via the direct binaries (`gz sim -s`, `.pixi/envs/full/lib/ros_gz_bridge/parameter_bridge`) + a rclpy driver. `rclpy` and the `parameter_bridge` binary ARE present.
> 3. **VERIFY NEXT — service bridging syntax.** The launch bridges the 4 services with topic-`@`-syntax (`/world/{w}/create@ros_gz_interfaces/srv/SpawnEntity`); `parameter_bridge` service-bridging via CLI args is unconfirmed here (couldn't `ros2 service list` — missing CLI). Confirm the 4 services actually appear on the ROS side (via `rclpy` `get_service_names_and_types()`) before trusting the round-trip; may need a YAML `--bridge-service` config instead.
> A full round-trip additionally needs an executor-spinning driver (mirroring the bridge node's background executor + `_run_async`), since the adapter's service-call futures require a spinning `self.node`.

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
8. Trajectory `time_from_start` monotonicity / wrench frame+units / `link` not exposed to MCP.
9. Two divergent force paths (legacy service `apply_wrench` vs new topic `actuate_wrench`) — reconcile/deprecate.
10. Mock fidelity caps (documented): m=1.0, torque/twist not integrated, last-write-wins single wrench.

### P2-real (plan §P2 STATUS — 7 items)
1. **Param transport likely wrong** — Harmonic params are gz-transport (`gz.msgs.ParameterValue`), not the guessed `rcl_interfaces` node `/world/<w>/gz_parameters`. Route via `gz service`/`gz param` or gate with `PARAM_BACKEND_UNAVAILABLE` (currently masks as `UNKNOWN_PARAM`).
2. Modern `sensor_snapshot` returns raw `gz-text` (marked `typed:false`) — parse `gz topic -e` echo into typed per-sensor shapes.
3. `list_sensors` type-classification = topic-name substring guess; real health hardcoded `"unknown"`.
4. `gz topic -e` `text=True` for binary msgs.
5. Param-service clients never destroyed (leak).
6. Legacy 69-tool `sdk_app` surface still advertises the 8 deprecated tools regardless of flag — filter in `_build_registry` when `GAZEBO_LEGACY_TOOLS=0`.
7. Completeness: lean `sensor_list` dropped `response_format` token control; camera fixed PNG (no `format`); `param_set` no allowlist.

### P3 deferred (plan §P3 STATUS — 7 items; blocker already CLEARED)
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
- **Single-server unification is DONE** (P3): FastMCP app serves 88 tools (19 lean + 69 legacy), stdio+HTTP, per-session isolation. Old `server.py` (hand-rolled) + `sdk_app.py` (low-level) retained as rollback. Schema-fidelity divergence (P3 #1) now **partially resolved** (array items restored; object-props + validation-location are a documented FastMCP-1.27.1 constraint). **Removal still blocked on:** (a) extracting `sdk_app._build_registry()` (a live `legacy_mount` dependency) to a shared module, and (b) an HTTP soak test. Removal is a gated refactor, not a deletion.
- **Dual-transport window:** stdio remains CI/default transport; no removal date for stdio. Decide HTTP-default flip criteria after a soak.
- **HTTP security:** transport is unauthenticated (localhost default + warning). Add auth/proxy guidance before any non-loopback deployment.
- 2 pre-existing test failures unrelated to this work: `test_list_models_mock_data` (needs live gz), `test_result_filter_with_models` (`ModuleNotFoundError: skills`). Triage separately.
- `/go` not yet run — 21 commits on `feature/p0-bridge-mock` unpushed; open the PR.

---

## Suggested order
1. **Ship** the current branch (`/go`) — P0-B→P3 mock side is a clean, self-contained PR.
2. **P5 hardening** (mock-verifiable: `actuation_bounds`, image caps, progress consumer, docs) — no live gz needed.
3. **P*-real** track in one push: `pixi install -e full` → JETANK SDF → live Harmonic → run all `-m gazebo` acceptance → burn down the P0-B/P1/P2-real findings.
4. **P4** (`sim_*`) only if cross-sim portability is wanted.
5. Resolve P3 #1 (schema fidelity) → retire the old `server.py`/`sdk_app.py`.

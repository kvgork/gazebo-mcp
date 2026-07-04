# gazebo-mcp — Remaining Work

> Consolidated backlog after the P0-B → P3 mock-side build (branch `feature/p0-bridge-mock`, 2026-06-30).
> Source of truth for detail: `GAZEBO_MCP_ARCHITECTURE_EVOLUTION_PLAN.md` (per-phase `STATUS` blocks hold the full findings + commit hashes).
> **Done & verified in `-e dev` (mock):** P-1, Step 0, P0-A, **P0-B, P1, P2, P3**. Suite: 581 passed / 10 skipped / 2 pre-existing failures.

---

## A. Remaining phases (new capability)

### P4 — Jetty `sim_*` (cross-sim portability) — OPTIONAL
- `sim_get_features`, `sim_spawn`/`sim_step` parity with `scene_spawn`/`world_step` over `simulation_interfaces`.
- Effort ~2-3 d. Deps: P0–P3 + Jetty/`simulation_interfaces` on the P-1 backend. Keep `sim_*` strictly optional + non-default.
- Plan §P4.

### P5 — Hardening
- `src/gazebo_mcp/utils/actuation_bounds.py` — magnitude/duration/joint-limit/rate caps (over-limit wrench clamped or rejected under `strict_bounds`; persistent wrench requires clear; rate flood throttled).
- Image caps (already partly enforced at the tool layer — finalize + document).
- **Progress consumer:** #953 spike PASSED (streamed progress works over HTTP on 1.27.1) → wire `report_progress` into a long-running tool (e.g. `world_step(N)`, fleet ops). No op-id+poll fallback needed.
- Docs (notify-then-poll honesty, CPU-only physics, GUI-gap deprecations).
- Effort ~3-5 d. Plan §P5.

---

## B. P*-real track — live-gz verification (the big cross-cutting gap)
**All real (`-m gazebo`) acceptance is DEFERRED** — needs `pixi install -e full` (`ros-jazzy-ros-gz`) + a running **Gazebo Harmonic** process + (for P1) `gz_ros2_control` + the **JETANK SDF**. System `gz` = Harmonic 8.14.0 is present; the `sim`/`full` pixi envs are NOT installed. The mock side is fully verified; the real adapter code is written but never live-run.

**Gating first step:** `pixi install -e full`, bring up the provisioned Harmonic world, then run the per-phase `-m gazebo` acceptance and fix the deferred findings below.

### P0-B-real (plan §P0 STATUS — 6 items)
1. modern pose cache keyed only by `child_frame_id` → cross-model link-name collisions; key by `(parent, child)` / filter to world-scoped models.
2. `set_physics`/`seed` honesty: gz uses gz-transport service (not `rcl_interfaces.SetPhysics`); currently `return True` no-op. Shell out to `gz service` or report `applied=False`.
3. `get_entity_state` cache never invalidated (stale pose; deleted entity still reports). Refresh-spin/timestamp-evict; clear on delete.
4. PosePublisher placed at `<world>` scope — verify per-model placement publishes to `/world/<w>/pose/info`.
5. `spin_once` executor-conflict risk; bridge-mapping `Pose_V↔TFMessage` payload syntax to confirm on the installed bridge.
6. detection AUTO→MOCK silent fallback masks "gz not started" in prod — loud-WARN / opt-in gate.

### P1-real (plan §P1 STATUS — blocker + items)
1. **No spawnable JETANK SDF** — convert `~/workspaces/jetank/.../urdf/*.xacro` → urdf → `gz sdf`, swap `ignition-*`→`gz_ros2_control`, add `models/jetank/*.sdf`. **Blocks real P1 acceptance.** (Manifest at `src/gazebo_mcp/data/jetank_manifest.json` is ready.)
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
1. **Legacy schema fidelity / validation divergence** — unified FastMCP legacy uses inferred schemas (nested array/object lose item typing) + FastMCP validates before the handler → generic errors instead of rich `OperationResult`. `sdk_app` retained keeps exact curated schemas. *(highest-value P3 follow-up)*
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
- **Single-server unification is DONE** (P3): FastMCP app serves 88 tools (19 lean + 69 legacy), stdio+HTTP, per-session isolation. Old `server.py` (hand-rolled) + `sdk_app.py` (low-level) retained as rollback — **schedule their removal** once the schema-fidelity divergence (P3 #1) is resolved and HTTP soak-tested.
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

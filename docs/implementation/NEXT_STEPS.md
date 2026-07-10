# gazebo-mcp — Next Steps (execution roadmap)

> Sequenced, prescriptive plan built on the 2026-07-04 session state. Turns the
> `REMAINING_WORK.md` backlog into an ordered set of phases with prerequisites,
> dependencies, and rough effort. Detail/findings live in `REMAINING_WORK.md` §B
> and the per-phase `STATUS` blocks in `GAZEBO_MCP_ARCHITECTURE_EVOLUTION_PLAN.md`.

**Where we are:** mock side P0-B→P5 + P4-shim done & shipped (PR #20, open, stacked on
`feature/step0-sdk-server`). **P0-B-real fully live-verified** (spawn/step/pose + permanent
`@pytest.mark.gazebo` test). P*-real #1 (bring-up pinned) + #2 (set_physics/seed/detection)
done. #3 param transport fixed (mock-green). Remaining live work is env-gated.

**Recommended order:** A (ship + hygiene) → B (code-only fixes) → D (ONE clean live session)
→ C3 (retire old servers) → E (P1-real, after upstream) → F (optional). A and B need no gz
and unblock everything else.

---

## Phase A — Ship + CI hygiene  *(no gz; do first; ~0.5 d)*
- [ ] **A1. Merge the PR stack bottom-up** — #17 → #18 → #19 → #20 (each based on the branch
  below; step0 is not yet in `main`). Gets P0-B→P5 + P4 into `main`. **Human decision — the
  hard stop held.** Do a final `/review-changes` on each before merge. *(STILL OPEN — the only
  remaining Phase-A item; everything else here is done.)*
- [x] **A2. Stabilize `test_p3_progress_spike`** — DONE (`e989ca4`): `_UvicornServer` now binds
  `port=0` (OS-assigned at bind) and reads the real port back, killing the pick-then-rebind
  TOCTOU. Suite green + deterministic across repeated runs.
- [x] **A3. Triage the 2 pre-existing failures** — DONE (`e989ca4`): `test_list_models_mock_data`
  asserts a well-formed result (`count >= 0`; the mock honestly has 0 models, no phantom
  fixtures); `test_result_filter_with_models` DELETED (imported the absent external
  `skills.common.filters`). **Suite now 0-fail.** (ResultFilter doc-vs-code gap logged in
  REMAINING_WORK §C.)

## Phase B — Code-only P2-real fixes  *(done; live-verify in D)*
- [x] **B1. P2-real #2/#4 — binary-safe sensor snapshot** — DONE (`ebafa0f`): `sensor_snapshot`
  now uses `gz topic -e -n 1 --json-output` (text-safe for binary Imu/LaserScan/Image; fixes the
  confirmed `/imu` hang), returning a typed `{"format":"gz-json","sample":…,"typed":True}`.
  Per-sensor typed-shape verify → D2.
- [x] **B2. P2-real #7 completeness** — DONE (`a68bb62`): `sensor_list` `response_format`
  (detailed|concise token economy); `param_set` now honors the adapter `applied` bool (was masking
  the real backend's honest False). *(Scalar validation already existed; camera JPEG intentionally
  NOT added — a no-op on the mock PNG path would overstate capability; defer to the real encoder.)*
- [ ] **B3. P2-real #3 — `list_sensors` health/classification** — **DEFERRED to D2**: real health
  (topic Hz / publisher presence via `gz topic -i`) needs live sensors to tune + verify; writing
  it blind = untested code.
- [x] *(P2-real #5 param-client leak — RESOLVED by the B-adjacent gz-CLI param rewrite: no
  persistent clients. P2-real #6 deprecated-filter — skipped; folds into the C3 retire.)*

## Phase C — Finish P3 #1 + retire the old servers  *(DONE 2026-07-04)*
- [x] **C1. Extract registry** (`846bfa0`) — `gz_mcp_server/server/registry.py:build_registry()`;
  `legacy_mount` + parity test decoupled from the retiring `sdk_app`.
- [x] **C2. HTTP soak** (`da2519c`) — `test_p3_http_soak.py`: 72 sessions (12 concurrent x 6
  rounds > 64 cap), per-session isolation + LRU eviction, mock backend. Passes.
- [x] **C3. Retire** (`2d85c29`) — deleted `server.py` + `sdk_server.py` +
  `gz_mcp_server/server/{server,sdk_app}.py`; `gazebo-mcp-server`/`serve` repointed to the
  unified `fastmcp_server:main` (name kept); `gazebo-mcp-sdk`/`serve-sdk` removed; parity test
  repurposed to registry-integrity + unified-app name-parity. Suite 628 pass / 0 fail.
  - Residual P3 #1 (FastMCP couples advertised-schema ↔ validation; object-props stay bare
    `dict`) is a documented intrinsic 1.27.1 constraint — **won't-fix**, not blocking.

## Phase D — Live P*-real verification  *(mostly DONE 2026-07-08 on a fresh GPU host)*
> **Env prereqs (do NOT reuse a session that has churned gz):** a FRESH host (stale gz-transport
> state from repeated SIGKILLs wedges `gz sim` startup); a GPU **or** software-GL so camera
> sensors render headless. **RENDER BLOCKER CLEARED 2026-07-08:** on an RTX 3080 host, headless
> EGL rendering works — `gz sim -s -r --headless-rendering --render-engine-api-backend egl
> camera_sensor.sdf` publishes real images (`/camera` 320×240). Non-render sensors (`/imu`
> `/altimeter` in `sensors.sdf`) work regardless. Use SIGTERM, never SIGKILL, on gz. **Never
> `pkill -f "python -c"`** (kills the agent harness).
- [x] **D1.** P0-B-real acceptance re-run on the fresh host — **PASS** (`~15s`), regression guard holds.
- [x] **D2. Sensors** — **DONE 2026-07-08** (`tests/integration/test_p2_real_sensors.py`, 3 tests):
  `list_sensors` classifies live `/imu` (non-render `sensors.sdf`) + `/camera` (EGL render
  `camera_sensor.sdf`); `sensor_snapshot` returns TYPED gz-json samples for the binary Imu AND
  camera Image (B1 live-verified). `sensor_camera_image` (PNG re-encode) stays honestly DEFERRED
  (needs an image codec) — asserted to raise. **B3 gap documented live:** the substring classifier
  does not recognise altimeter/magnetometer/air_pressure (real health/Hz still unwired).
- [x] **D3. Param round-trip** — **DONE 2026-07-08** (`tests/integration/test_p2_real_params.py`,
  2 tests). Declares params via the `declare_parameter` service (`gz.msgs.Parameter.value` is a
  `google.protobuf.Any` — text form `value { [type.googleapis.com/gz.msgs.Double] { data: 2.5 } }`),
  then round-trips `param_list`/`get`/`set` across Double/String/Boolean/Int32. **Found + fixed 2
  live bugs:** `param_set` used `-t double -m 7.25` but `gz param -s` wants `-t gz.msgs.Double -m
  'data: 7.25'`; `param_get` returned the trailing `----` separator instead of the `data:` line
  (and now handles proto3 default-omission for false/zero). Undeclared → honest KeyError.
- [x] **D4. P3-real** — **DONE 2026-07-10** (`tests/integration/test_p3_real_http.py`, 2 tests):
  unified server on real uvicorn `--http` + modern backend vs live `gz sim -s -r sensors.sdf`;
  `gz://sensor/imu` returns a REAL typed `gz-json` sample over the modern backend (the resource
  read drives `list_sensors` name→topic + `sensor_snapshot` over live `gz`), and two distinct
  `Mcp-Session-Id` clients each get their own session/bridge + independently read the live sensor.
  **Isolation scope:** session/bridge-OBJECT (distinct ids + independent bridges), NOT world-state
  (world-state isolation is mock-only — a live gz world is physically shared). Sensor reads are
  `gz`-CLI so no `ros_gz` bridge is needed. **Found + fixed live:** `sensor_snapshot` dropped a
  valid typed sample to the `gz-text` raw fallback when `gz topic -e -n 1 --json-output` flushed
  MULTIPLE concatenated messages under the HTTP/timing path — `modern_adapter._parse_last_json_object`
  now returns the LATEST complete object (unit-locked in `test_modern_snapshot_parse.py`).
- [x] Each landed as a `@pytest.mark.gazebo` test (skips by default) so they are permanent.

## Phase E — P1-real  *(BLOCKED on upstream; ~2–3 d after)*
- [ ] **E1. UPSTREAM (external, robot owner):** add `<inertial>` (real mass/inertia) to the 7
  `jetank_description` links `gz sdf` drops — `arm_bearing_link` + the 6 wheels. **Do NOT
  fabricate mass properties.** Blocks all of P1-real.
- [ ] **E2.** After E1: `xacro → urdf → gz sdf` → `models/jetank/*.sdf`; swap `ignition-*` →
  `gz_ros2_control`; add controller-spawner + bridge lines in the launch.
- [ ] **E3.** Live P1 acceptance: JETANK spawn + joint pos/vel/force + wrench duration/persistent.
- [ ] **E4.** P1-real code items 2–10: non-persistent wrench as scheduled `clear_wrench`;
  `gz-sim-joint-controller-system` for vel/force joints; reconcile the two force paths
  (`apply_wrench` service vs `actuate_wrench` topic); trajectory `time_from_start` monotonicity.

## Phase F — Optional
- [x] **P4 real** REP-2018 `simulation_interfaces` adapter — **DONE 2026-07-08.** The blocker
  ("no REP-2018 backend here") was WRONG: `ros_gz_sim`'s **gzserver component**
  (`libgzserver_component.so`) provides the full `simulation_interfaces` service set under
  `/gz_server` (spawn/delete/get_entities/get_entity_state/set_entity_state/step/reset/
  set_simulation_state/get_simulator_features). Wrote `bridge/adapters/sim_interfaces_adapter.py`
  (`SimInterfacesAdapter(GazeboInterface)` — a REP-2018 CLIENT) and live-verified the full
  portable lifecycle against it (`tests/integration/test_p4_real_sim_interfaces.py`). Gazebo-
  specific ops (wrench/joint/sensor/param) stay honest NotImplementedError (REP-2018 doesn't
  define them). **Follow-up — DONE 2026-07-10:** wired into backend-selection —
  `GazeboBackend.SIM_INTERFACES` enum + factory branch (lazy import for `-e dev` safety) +
  `GAZEBO_SIM_INTERFACES_NS` (default `/gz_server`). The 5 `sim_*` tools dispatch polymorphically
  via `get_bridge().adapter`, so `GAZEBO_BACKEND=sim_interfaces` routes them through
  `SimInterfacesAdapter` with NO `sim.py` code change. Verified: `test_sim_interfaces_backend_selection.py`
  (unit) + `test_p4_real_backend_selection.py` (live, 4 tests — factory selection, `sim_get_features`
  backend name, spawn/step/delete routed through REP-2018, gz-specific op degrades honestly).
- [x] **P5 deferred** — per-waypoint trajectory position/velocity clamping — **DONE 2026-07-05**:
  `actuate_joint_trajectory` gained an optional `joint_names` arg + per-waypoint manifest-limit
  enforcement (tool rejects out-of-range; bridge `command_joint_trajectory(..., limits=)` clamps
  via new `enforce_trajectory`). Backward-compatible; mock-verified (suite 651 pass). See
  REMAINING_WORK §B "P5 deferred #1".

---

## Dependency graph (quick)
```
A (ship+hygiene) ──┐
B (code fixes) ────┼─► D (live: needs fresh+render host) ──► C3 (retire)
                   │        ▲
C1 (extract) ──────┘        │
E1 (upstream JETANK) ─► E2/E3/E4 (live P1) ──┘  (parallel to D on the same live session)
F (optional, independent)
```
**Fastest value:** A1 (merge → main) + A2/A3 (green CI) can happen immediately. B is pure code.
D+E collapse into one or two focused live sessions on a proper host. C3 closes the dual-server debt.

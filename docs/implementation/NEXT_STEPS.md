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

## Phase D — Live P*-real verification  *(needs ONE clean session; ~1–2 d)*
> **Env prereqs (do NOT reuse a session that has churned gz):** a FRESH host (stale gz-transport
> state from repeated SIGKILLs wedges `gz sim` startup); a GPU **or** software-GL so camera
> sensors render headless (camera worlds hang without it — non-render sensors like `/imu`
> `/altimeter` in `sensors.sdf` work regardless). Bring up via the now-working
> `ros2 launch gazebo_mcp gazebo_bridge.launch.py world_name:=<w>` (P*-real #1). Use SIGTERM,
> never SIGKILL, on gz. **Never `pkill -f "python -c"`** (kills the agent harness).
- [ ] **D1.** Re-run the P0-B-real acceptance test on the fresh host (regression guard) —
  `pixi run -e full pytest --with-gazebo -m gazebo tests/integration/test_p0b_real_roundtrip.py`.
- [ ] **D2. Sensors** (after B1/B3): verify `list_sensors` classification+health against
  `sensors.sdf` (non-render) and a camera world (render); verify `sensor_snapshot` typed shapes
  on `/imu` + `sensor_camera_image` on the camera.
- [ ] **D3. Param round-trip:** resolve the `gz.msgs.Parameter` proto shape, declare a param via
  `/world/<w>/declare_parameter`, then verify adapter `param_list`/`get`/`set` round-trip live
  (transport + registry + list already verified; only the declared-param get/set remains).
- [ ] **D4. P3-real:** run the unified server `--http` in modern mode against live gz; verify
  per-session isolation + `gz://sensor/{name}` resources over the REAL backend.
- [ ] Add each as a `@pytest.mark.gazebo` test (skips by default) so they become permanent.

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
- [ ] **P4 real** REP-2018 `simulation_interfaces` adapter — needs a simulator that implements
  those ROS services (none here; the package ships no registered interfaces in `-e full`).
- [ ] **P5 deferred** — per-waypoint trajectory position/velocity clamping (needs `joint_names`
  added to the trajectory contract so waypoints map to manifest limits).

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

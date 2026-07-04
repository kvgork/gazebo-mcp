# P5 Hardening — Safety Bounds & Honest Behaviour

This guide documents the P5 "hardening" behaviour of the Gazebo MCP server:
actuation safety bounds, the true sensor-subscription mechanism, physics
reality, GUI deprecations, image caps, and how to run real (live-Gazebo)
acceptance tests. It describes what the code actually does — not aspirations.

---

## 1. Actuation bounds & safety

All actuation (wrench application, joint commands) is enforced at a **single
chokepoint** inside the bridge node (`gazebo_bridge_node`), *before* the call
reaches the backend adapter. Because the check sits below the tool layer, the
same limits apply identically across the mock, modern, and classic backends,
across all MCP tools, the legacy tool surface, and direct bridge calls.

**Qualification — `command_joint_trajectory` is only partially covered.** For
a joint *trajectory* (as opposed to a single `actuate_joint` command), the
bridge only rejects waypoint **positions that are non-finite** (`NaN`/`inf`)
with `ACTUATION_BOUNDS_EXCEEDED`. **Finite but out-of-range** trajectory
positions are **not clamped** — this is deliberately deferred: the trajectory
wire format carries `positions` as a bare list with no joint names, so a
waypoint value cannot be mapped to a specific joint's manifest limits at
either the tool or the bridge layer. See `REMAINING_WORK.md` for the proper
fix (adding `joint_names` to the trajectory contract).

### 1.1 Defaults and environment overrides

Every bound has a safe default and can be overridden with an environment
variable. Defaults are chosen to be permissive enough for typical desktop
robots but bounded enough to prevent a runaway command from diverging the sim.

| Bound | Env var | Default | Meaning |
|-------|---------|---------|---------|
| Max force | `GAZEBO_MAX_FORCE_N` | `1000` | Cap on the **magnitude** of the force vector (N). |
| Max torque | `GAZEBO_MAX_TORQUE_NM` | `500` | Cap on the **magnitude** of the torque vector (N·m). |
| Max joint velocity | `GAZEBO_MAX_JOINT_VELOCITY` | `10` | Cap on `\|value\|` for velocity-mode joint commands (rad/s or m/s). |
| Max joint effort | `GAZEBO_MAX_JOINT_EFFORT` | `500` | Cap on `\|value\|` for force/effort-mode joint commands (N·m or N). |
| Max persistent wrenches | `GAZEBO_MAX_PERSISTENT_WRENCHES` | `8` | Max number of simultaneous persistent wrenches (int). |
| Rate limit | `GAZEBO_RATE_LIMIT_HZ` | `50` | Per-entity actuation rate cap (Hz). `<= 0` disables rate limiting. |
| Strict bounds | `GAZEBO_STRICT_BOUNDS` | `0` | `0` (default) = clamp; `1`/`true`/`yes` = raise on any over-limit. |

These map to `BoundsConfig` fields and are read into `GazeboConfig` from the
environment. When no `GazeboConfig` is present (e.g. certain test/DI
constructions), **all defaults apply**.

### 1.2 Clamp vs. strict (the two enforcement modes)

The behaviour when a command exceeds a bound is governed by
`GAZEBO_STRICT_BOUNDS`:

- **Clamp mode (default, `GAZEBO_STRICT_BOUNDS=0`).** An over-limit command is
  silently reduced to the bound and then executed:
  - Force / torque **vectors are scaled to the magnitude cap while preserving
    their direction** (not clipped per-axis).
  - Joint values are clamped:
    - `pos` mode → clamped to the joint's `[lower, upper]` limits (when limits
      are known; if limits are unknown they are not enforced).
    - `vel` mode → clamped to `[-max_joint_velocity, +max_joint_velocity]`.
    - `force`/`effort` mode → clamped to `[-max_joint_effort, +max_joint_effort]`.
- **Strict mode (`GAZEBO_STRICT_BOUNDS=1`).** Any over-limit command is
  **rejected** — the operation raises an error with
  `error_code = ACTUATION_BOUNDS_EXCEEDED` instead of being clamped.

### 1.3 Persistent-wrench cap requires explicit clear

Persistent wrenches (applied with `persistent=True`) are tracked in a registry
per `(entity, world)`. Registration is idempotent for the same key. When
registering a **new** key would exceed `GAZEBO_MAX_PERSISTENT_WRENCHES`, the
operation raises `ACTUATION_BOUNDS_EXCEEDED`. There is **no automatic eviction**
— you must explicitly clear an existing persistent wrench (via the wrench-clear
path) before a new one can take its slot. This prevents an unbounded pile-up of
forces that would silently diverge the simulation.

### 1.4 Per-entity rate cap

A per-entity rate limiter caps how frequently actuation commands are accepted
for a given entity to `GAZEBO_RATE_LIMIT_HZ` (default 50 Hz). Commands arriving
faster than `1 / hz` since the last accepted command for that entity are
throttled.

**Scope: wrench-topic actuation only.** The rate cap applies **only** to
`apply_wrench_topic` (per `(entity, world)`). Joint commands
(`command_joint` / `command_joint_trajectory`) are **intentionally NOT
rate-limited** — a multi-joint controller legitimately issues many joint
commands per control cycle, and a per-model rate cap would wrongly throttle
that normal traffic.

**Setting the cap too low will throttle a legitimate control loop.** If your
wrench control loop calls `actuate_wrench` faster than `GAZEBO_RATE_LIMIT_HZ`,
throttled calls return `applied=False` (clamp mode) or raise
`ACTUATION_BOUNDS_EXCEEDED` (strict mode) instead of being queued or delayed.
Raise `GAZEBO_RATE_LIMIT_HZ` to match your loop's real rate, or set
`GAZEBO_RATE_LIMIT_HZ=0` (or any `<= 0` value) to disable rate limiting
entirely — **`<= 0` is the documented "disabled" sentinel**, not an invalid
configuration (it is exempt from the config's non-negative validation).

---

## 2. Sensor "subscriptions": notify-then-poll, NOT streaming

**There is no server-push data stream.** A sensor "subscription" over MCP is a
notify-then-poll cycle, and it is important to understand that the notification
carries **no sensor payload**:

1. The client issues `resources/subscribe` for a `gz://sensor/{name}` resource.
2. When a new sample is available, the server emits a
   `notifications/resources/updated` notification. This is a **bare URI ping**
   — it announces *that* the resource changed and carries **no data**.
3. The client then performs a `resources/read` on the resource URI to fetch the
   **cached latest sample**.

In other words, the server never pushes sensor bytes to the client on its own.
The client is always the one that pulls the data, in response to a
contentless "something changed" ping. Do not build client logic that expects
sensor values to arrive inside the update notification — they never will.

---

## 3. Physics is CPU-only

Simulation physics runs **on the CPU**. There is no GPU-accelerated physics
path. Expect real-time-factor and step throughput to be bounded by CPU
performance; heavy contact-rich scenes or large step counts will run slower
than wall-clock. Long stepping operations report progress incrementally (see
`world_step`) but the underlying compute is still CPU-bound.

---

## 4. GUI-gap deprecations

The MCP server drives Gazebo **headlessly** — it operates on the transport/
service layer, not the Gazebo GUI. There is no GUI automation surface exposed
through MCP, and GUI-only workflows are not covered. In addition, **Classic
Gazebo (gazebo-ros-pkgs) is deprecated** and slated for removal in v2.0.0;
Modern Gazebo (Fortress / Garden / Harmonic) is the primary, default backend.
Any GUI-dependent or Classic-only behaviour should be considered legacy and not
relied upon for new work.

---

## 5. Image caps (rejected, not downscaled)

Camera-image tooling enforces hard ceilings **before** the image is returned:

- **Maximum dimension:** `4096` px per side (width and height).
- **Maximum encoded size:** `1.5 MB` of base64 data.

An image exceeding either limit is **REJECTED** — it is **not** resized or
downscaled. The tool returns an error with `error_code = IMAGE_TOO_LARGE`.
Callers that need a larger frame must request a lower resolution / quality from
the sensor so the result fits under the caps.

---

## 6. Real (live-Gazebo) acceptance is DEFERRED

All P5 behaviour above is verified against the **mock** backend, which requires
no live simulator. Real acceptance against an actual running Gazebo (i.e.
running the server with the `-m gazebo` / modern backend against live services)
is **deferred** and is not part of the mock-verified suite.

To run real acceptance you need all of:

1. The full environment installed: `pixi install -e full`.
2. A running **Gazebo Harmonic** instance with its services up.
3. The **JETANK SDF** asset loaded.

Until that environment is stood up, live-Gazebo acceptance remains outstanding;
the mock suite is the source of truth for CI.

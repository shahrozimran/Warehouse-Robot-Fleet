# Fleetwise · Warehouse Robot Fleet

A functional local warehouse simulator with a **React frontend, Three.js digital twin, FastAPI backend, SQLite persistence, and nine MCP tools**. Multiple robots coordinate picking, shipping, traffic conflicts, and charging. Experiments are reproducible and every replay position comes from the backend.

<!-- GitHub README: Fleetwise Warehouse Robot Fleet -->

> **Local-first simulation · 3D digital twin · Multi-robot coordination · MCP-enabled**

**Fleetwise** is a reproducible warehouse robot fleet simulator designed for exploring scheduling, routing, congestion, charging, and operational trade-offs. It connects a browser-based 3D dashboard to a deterministic Python simulation backend, a SQLite history store, and nine MCP tools.

> **Deployment note:** This project runs locally. The `127.0.0.1` URLs and Windows paths below refer to the machine where Fleetwise is installed; they are not public demo links. The repository contains source code, not a hosted service.

## Contents

- [Open the app](#open-the-app)
- [Requirements and API keys](#requirements-and-api-keys)
- [What is implemented?](#what-is-implemented)
- [Dispatch policies](#dispatch-policies)
- [Scenarios](#scenarios)
- [How the simulation works](#how-the-simulation-works)
- [MCP connection](#mcp-connection)
- [Setup and development](#setup-and-development)
- [Data, API, and scope](#data-api-and-scope)
- [Source layout](#source-layout)

---

## Open the app

The project is installed and built in:

```text
D:\Desktop\Projects\Warehouse Robot Fleet
```

Dashboard: **http://127.0.0.1:8102/**

API reference: **http://127.0.0.1:8102/docs**

Double-click **Start.cmd**, or run the following from PowerShell:

```powershell
Set-Location 'D:\Desktop\Projects\Warehouse Robot Fleet'
.\Start.ps1
```

The foreground server stops with Ctrl+C. For a hidden background server, use `.\Start-Background.ps1`; stop it with `.\Stop.ps1`. Both accept `-Port`. The supplied project uses port **8102**, so the existing Agent Simulation MCP application can keep running on port 8000 independently.

If a PowerShell execution policy blocks a script, `Start.cmd` invokes a process-scoped bypass; it does not change the machine's permanent policy. Background logs are in `logs/`. The stop script verifies this project's interpreter path and API command before stopping a process.

## Requirements and API keys

| Component | Requirement |
|---|---|
| Python | 3.11+; installed environment tested with 3.14.5 |
| Node.js | 22.12+ or 24 LTS for frontend builds; tested with 24.15.0 |
| Database | Embedded SQLite; no database server required |
| Graphics | WebGL-capable browser for Three.js; a 2D recorded-grid fallback is included |
| LLM key | **Not required** for the application, simulator, REST API, or MCP server |
| AI client | Optional; any compatible client can supply its own model access for conversational MCP use |
| Robot hardware | Not required; this application controls simulated robots only |

All fonts, JavaScript libraries, and 3D geometry are local. After dependencies are installed, the app works offline. There is no built-in provider chat box and no place to enter LLM credentials. No external MCP client's configuration is modified automatically.

## What is implemented?

- **Control room:** scenario and dispatch policy, 2–10 robots, 4–80 generated orders, seed, and 100–1000 tick bounds.
- **Three.js warehouse:** storage racks, parcels, docks, charging pads, selectable robots, carried parcels, planned paths, aisle-closure barriers, and a full-run traffic heatmap.
- **Replay:** play/pause, seek, restart, and 1×/2×/4×/8× speed. This replays a completed backend calculation; the interface labels it as a recorded shift.
- **Cameras:** orbit, overhead, follow the selected robot, and reset. Drag to orbit, right-drag to pan, scroll to zoom, or click a robot to inspect it.
- **Fleet inspection:** per-robot battery, status, current job, position, target, traveled distance, completed orders, charging sessions, and decision explanation.
- **Order book:** timeline-aware statuses, search/filter, priorities, rack/dock details, due/completion ticks, and CSV export.
- **Experiments:** compare three dispatch strategies with identical generated demand; retrieve persisted history and replay any saved run.
- **Fleet analytics:** completed workload, battery, utilization, conflict waits, charging, throughput, and downloadable full JSON.
- **MCP:** nine validated tools over stdio or loopback Streamable HTTP, sharing the same engine and database as the dashboard.

The traffic heatmap is explicitly labeled as the **entire saved run**, even when viewing an earlier replay tick. Final analytics are also labeled separately from current replay statistics.

## Dispatch policies

| Policy | Decision behavior |
|---|---|
| `fifo` | Robots in ID order accept the oldest released feasible order |
| `nearest` | Each available robot chooses the closest reachable pickup |
| `auction` | Globally allocate the best robot/order bid using nominal route length, predicted lateness, priority, and prior workload |

The auction bid is `pickup travel + dock travel + 2 × predicted lateness − 3 × priority + 1.5 × previously completed jobs`. This is a heuristic, not a proof of optimal allocation. Ranking compares completed orders first, then makespan, then distance; it does not predetermine a winning policy.

## Scenarios

| ID | Behavior |
|---|---|
| `standard` | All orders are available at the start; batteries start at 100% |
| `peak` | Batches of eight release every 25 ticks with tighter deadlines |
| `blocked` | Aisle 12 cells close during ticks 45–109; occupied cells are deferred until robots vacate; the aisle reopens at tick 110 |
| `low_battery` | Several robots start at 18–32% charge and must recharge before accepting work |

Three genuine baseline shifts are initialized by `scripts.seed_demo` only if the database is empty. These are measured model outputs, not fabricated example metrics.

## How the simulation works

The warehouse has a 28×20 display grid. Robots move on interior walkable cells; racks and active maintenance cells are obstacles. Each robot has a dedicated home/charging pad, which avoids contention for a single charging destination. Eight rack-access cells and three shipping docks are shared resources. A robot handles one order at a time.

Each tick releases new orders, processes charging or service timers, assigns feasible work, plans routes, resolves simultaneous proposed moves, checks collision invariants, and saves a frame. Picking and handoff each take two service ticks. Movement uses four-neighbor BFS on the current obstacle grid, with stable routes, congestion detours after waits, and recent-cell exclusions to escape repeated movement cycles.

The centralized one-tick move resolver prevents two robots occupying the same cell, head-on edge swaps, and chains moving into a robot that cannot vacate its cell. Following into a simultaneously vacated cell is allowed. This is a discrete educational coordination model, not a real-world robot safety controller. It does not model sensor uncertainty, acceleration, footprints larger than one cell, continuous physical contact, or guaranteed deadlock-free planning for arbitrary demand.

Batteries use fictional percentage units: movement consumes 0.4 points per cell, service consumes 0.05 per tick, and charging adds 3.5 per tick up to 100. A robot accepts work only if it has estimated energy for pickup, delivery, return to its own pad, and a reserve. Charging releases the robot at 90%. Congestion and idle costs are also modeled. A genuinely exhausted robot becomes `stranded`, leaving its unfinished order visible.

The run stops after all orders are delivered or the tick bound is reached. **Unfinished work is reported truthfully as `tick_limit`; it is never counted as delivered.** At high demand or short bounds, partial completion is a valid result.

Metrics use simulated ticks and cells. Throughput is orders per 100 ticks. Cycle time is release-to-handoff time for completed orders. On-time rate is computed over completed orders and is accompanied by the completion count. Utilization is assigned movement/service ticks divided by total robot-ticks. Returned empty movement still contributes to total distance. These metrics do not estimate real warehouse capacity or cost.

## MCP connection

Open the **MCP connection** page for an exact, copyable configuration. Clients using the `mcpServers` format can use:

```json
{
  "mcpServers": {
    "warehouse-fleet": {
      "command": "D:\\Desktop\\Projects\\Warehouse Robot Fleet\\.venv\\Scripts\\python.exe",
      "args": ["D:\\Desktop\\Projects\\Warehouse Robot Fleet\\mcp_server.py"]
    }
  }
}
```

The client starts the stdio process. The dashboard does not need to be running for MCP tools to work. Both processes share the same project-relative absolute SQLite path, regardless of the client's working directory. Refresh the dashboard after experiments created by another client.

For Streamable HTTP:

```powershell
.\.venv\Scripts\python.exe mcp_server.py --http
```

Endpoint: **http://127.0.0.1:8103/mcp**. This is a separate process from the API on 8102. Change its port with `--port`. The tested SDK line is explicitly pinned to `mcp<2` and uses `FastMCP` from the v1 maintenance API.

| Tool | Purpose |
|---|---|
| `get_warehouse` | Inspect racks, walkable grid, chargers, and docks |
| `list_scenarios` | Discover scenario IDs |
| `list_policies` | Inspect dispatch algorithms |
| `run_simulation` | Run a bounded shift and persist it |
| `run_comparison` | Compare all policies with identical input conditions |
| `list_runs` | Paginated saved summaries |
| `get_run` | Retrieve metrics, orders, events, and heatmap without the large frame array |
| `get_frame` | Inspect all robot and order states at a specified saved tick |
| `compare_runs` | Compare saved IDs and flag mismatched conditions |

Example prompts:

- “Compare all policies in `blocked` with 6 robots, 24 orders, and seed 42.”
- “Run `low_battery`, then inspect the charging events and the number of completed orders.”
- “Inspect the robots at tick 60 of this run. Explain which jobs they are working on.”
- “Compare fleet sizes 4 and 8 in `peak`. Report completion and throughput, and acknowledge the differing fleet conditions.”

## Setup and development

From the project directory:

```powershell
.\Setup.ps1
.\.venv\Scripts\python.exe -m pytest -q
Set-Location frontend
npm.cmd test
npm.cmd run build
```

`Setup.ps1` creates `.venv`, installs the pinned Python lock, runs `npm ci`, builds the frontend, and initializes baseline runs only if empty. The Python lock is from the tested Windows environment and includes Windows-specific packages; resolve `requirements.txt` separately on another platform and verify it there.

For hot reload, start the backend from the project root and Vite from `frontend` in separate terminals:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8102 --reload
```

```powershell
npm.cmd run dev
```

Vite serves port **5174** and proxies `/api` to 8102. Rebuild after source changes before using the production server; `Start.ps1` serves the latest saved production build. Frontend replay tests use Node's TypeScript stripping, tested with Node 24.

## Data, API, and scope

SQLite is stored at `data/warehouse.sqlite3`. Set `WAREHOUSE_DB` to override its location. Tests automatically use isolated temporary databases. Runs store their configurations, metrics, orders, events, frame snapshots, and final traffic heatmap. Comparisons persist all three results in one transaction. SQLite WAL supports independent API/MCP readers and serializes writes. No runs are silently overwritten or deleted.

API routes are documented at `/docs`; a compact reference is in [docs/API.md](docs/API.md). Architecture and validation notes are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/VERIFICATION.md](docs/VERIFICATION.md).

This is a local single-user application bound to loopback. It does not include public hosting, authentication, physical robot control, a WMS integration, live inventory, or a provider-hosted LLM. A public multi-user deployment would need authentication, per-user ownership, job execution limits, and durable hosting.

## Source layout

```text
backend/
  catalog.py        Warehouse layout, scenarios, dispatch policies
  models.py         Bounded validated input models
  engine.py         Multi-robot state machine, routing, coordination, charging
  storage.py        SQLite schema and persisted experiment access
  service.py        Shared run/comparison service
  api.py            REST API and production frontend serving
frontend/src/
  main.tsx          Operations dashboard, order book, experiments, analytics
  WarehouseScene.tsx Three.js digital twin and frame-driven rendering
  replay.ts         Renderer-independent interpolation and coordinate mapping
  types.ts          Frontend data contracts
  styles.css        Responsive visual system
mcp_server.py       Nine MCP tools, stdio and Streamable HTTP
tests/              Engine, API, persistence, and real MCP transport tests
frontend/tests/     Replay interpolation and continuous spacing checks
scripts/            One-time measured baseline initialization
docs/               Architecture, API, verification, and screenshot
data/               Local SQLite data; excluded from Git
```
#

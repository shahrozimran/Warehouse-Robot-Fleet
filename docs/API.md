# REST API

Interactive OpenAPI reference: http://127.0.0.1:8102/docs

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | API and SQLite readiness |
| GET | `/api/catalog` | Layout, scenarios, policies |
| GET | `/api/overview` | All-run experiment totals |
| GET | `/api/runs?limit=100&offset=0` | Paginated summaries, up to 500 per request |
| POST | `/api/runs` | Execute and save a shift |
| GET | `/api/runs/{id}` | Complete result with frames |
| POST | `/api/comparisons` | Execute all three policies under common conditions |
| POST | `/api/compare` | Compare existing run IDs |
| GET | `/api/runs/{id}/export?format=json` | Complete JSON download |
| GET | `/api/runs/{id}/export?format=csv` | Per-order CSV download |
| GET | `/api/mcp` | Tool list and client configuration |

Run body:

```json
{"policy":"auction","scenario":"blocked","fleet_size":6,"order_count":24,"max_ticks":500,"seed":42}
```

Comparison body uses the same fields without `policy`. Saved comparison body: `{"run_ids":["id-1","id-2"]}`.

Invalid fields or out-of-bounds requests return 422. Missing results return 404. Each saved run contains `config`, `metrics`, `orders`, `frames`, `events`, `heatmap`, timestamps, and an ID. A frame includes robot states, order statuses, active closures, and current aggregate counters. A run's final metrics may differ from a partial frame's counters, by design.

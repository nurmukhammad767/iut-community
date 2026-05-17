# Changelog

All notable changes to this project will be documented in this file.
This project loosely follows [Semantic Versioning](https://semver.org/) and
the format of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.0.0] - 2026-05-17

Final submission build.

### Added
- **R3** - 4 new Postgres tables: `room_bookings`, `club_posts` (with GIN full-text
  index), `room_usage_daily`, `rate_limit_audit`. Alembic migration
  `a1b2c3d4e5f6`. Idempotent seed in `server/db/seed.py` (20 users, 5 courses,
  3 clubs, 10 posts, 3 bookings).
- **R4** - REST routers: `clubs`, `posts`, `bookings`, `dashboard` mounted on the
  auth service. OpenAPI auto-published at `/docs`.
- **R5** - Redis added to the stack: serves rate-limit buckets, chat backlog,
  and dashboard cache. Chat messages persisted to MongoDB `chat_messages`.
- **R7-a** - WebSocket chat at `WS /ws/chat/{club_id}?token=<jwt>`. In-process
  ConnectionManager, Redis-backed backlog (LPUSH + LTRIM 100), Mongo
  append-only history.
- **R7-b** - GraphQL endpoint at `POST /graphql` exposing a `dashboard` query
  that joins course / assignment / booking / club data into one round-trip.
- **R8** - Nginx gateway with `least_conn` load-balancing across `backend-1`
  and `backend-2` replicas. WebSocket-upgrade headers handled on `/ws/`.
- **R9** - `/healthz` endpoints on both FastAPI services; compose healthchecks
  on all services; `gateway` is the sole public port.
- **R10** - `nightly_analytics` Airflow DAG: aggregate Mongo `occupied_rooms`
  into Postgres `room_usage_daily`, expire past assignments, clear stale
  bookings.
- **R11** - Token-bucket rate limiter (from-scratch) backed by a Redis hash
  with atomic Lua check-and-decrement. Applied to `POST /clubs/{id}/posts`
  (capacity 5, refill 0.2 tok/s). Denials persisted to `rate_limit_audit`.
- **R12** - OpenTelemetry SDK initialized in both services; OTLP/HTTP export
  to a single-container Grafana LGTM (Loki + Grafana + Tempo + Prometheus +
  OTel collector) on port 3000.
- **R13** - README with architecture diagram, requirement map, env-var
  reference, endpoint table. This CHANGELOG. Live OpenAPI at `/docs`.

### Frontend
- `src/app/lib/api.ts` - fetch wrapper with JWT storage, error normalization,
  WebSocket helper.
- `LoginPage` wired to `POST /login` and stores JWT in `localStorage`.
- `OverviewPage` renders real `/dashboard` data.
- `CommunityPage` lists real clubs, supports join + post, embeds the live
  `ChatPanel` WebSocket component.

### Fixed
- `time_table_backend/requirements.txt` was missing `python-jose`, which would
  have crashed the timetable container on startup. Added.
- Airflow scheduler/triggerer/dag-processor were on `airflow-net` only and
  could not reach `backend-postgres` or `mongodb`. Added `backend-net` to the
  shared anchor.

## [0.2.0] - pre-submission

### Added
- JWT auth on every `/timetable/*` route via router-level dependency.

## [0.1.0] - initial scaffold

### Added
- FastAPI auth service (register / login / me).
- FastAPI timetable service backed by MongoDB.
- Airflow scraping DAG `iut_data_extractor` (3 parallel scraper tasks).
- React + Vite + shadcn/ui frontend skeleton with mock data.

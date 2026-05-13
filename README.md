# IUT Community

A full-stack student platform for Inha University in Tashkent.
Built as the Spring 2026 group project for *Database Application and Design*
(Dr. Sarvar Abdullaev).

> Real-time room booking · club community with live chat · personalized
> dashboard joining timetable + assignments + bookings · nightly analytics
> pipeline · token-bucket rate limiter · unified observability.

---

## Quick start

```bash
git clone https://github.com/<your-org>/iut-community
cd iut-community/server

# 1. .env (copy & edit values)
cp .env.example .env  # or fill in DB_USER, DB_PASSWORD, DB_NAME,
                      # MONGO_DB, SECRET_KEY, ALGORITHM, FERNET_KEY,
                      # AIRFLOW_UID, etc.

# 2. Bring up the entire stack (gateway, 2× backend replicas, timetable,
#    Postgres, MongoDB, Redis, Airflow, Grafana LGTM)
docker compose up -d

# 3. Wait ~60s for healthchecks. Then open:
#    http://localhost:8088/          → frontend (run `pnpm dev` from frontend/)
#    http://localhost:8088/docs      → OpenAPI / Swagger UI
#    http://localhost:8088/graphql   → GraphQL endpoint (POST queries here)
#    http://localhost:3000      → Grafana (admin / admin)
#    http://localhost:8080      → Airflow UI
```

Frontend dev server:

```bash
cd frontend
pnpm install
pnpm dev
```

Demo accounts (password is `Password123!` for everyone):

| Student ID    | Role      | Group     |
| ------------- | --------- | --------- |
| `U22107001`   | student   | SOC-22-A  |
| `U22107013`   | student   | BBA-22-A  |
| `PROF001`     | professor | FACULTY   |
| `ADMIN001`    | admin     | STAFF     |

---

## Architecture

```
                     ┌─────────────────────┐
                     │  Nginx Gateway :80  │  ← only public port
                     │  (least_conn LB)    │
                     └──────┬──────┬───────┘
            ┌───────────────┘      └────────────────┐
            ▼                                       ▼
    ┌──────────────┐                       ┌────────────────┐
    │  backend-1   │  ←──── shared deps ─→ │  backend-2     │
    │  FastAPI     │                       │  FastAPI       │
    │  :8000       │                       │  :8000         │
    └──┬──────────┬┘                       └─┬────────────┬─┘
       │          │                          │            │
       ▼          ▼                          ▼            ▼
  ┌────────┐  ┌────────┐                ┌────────┐  ┌─────────┐
  │Postgres│  │ Redis  │                │Postgres│  │ Redis   │
  │(users, │  │(rate-  │                │ (same  │  │  (same  │
  │ clubs, │  │ limit, │                │  shared│  │  shared │
  │ posts) │  │ chat,  │                │  store)│  │  store) │
  └────────┘  │ cache) │                └────────┘  └─────────┘
              └────────┘
                                       ┌──────────────────┐
                                       │  timetable :8001 │
                                       │  FastAPI         │
                                       └────────┬─────────┘
                                                ▼
                                            ┌────────┐
                                            │ Mongo  │
                                            │(time-  │
                                            │ table) │
                                            └────────┘

                  ┌───────────────┐     ┌──────────────────┐
                  │  Airflow      │ ──→ │  Postgres (R10   │
                  │ scheduler/    │     │ analytics writes)│
                  │ dag-processor │     └──────────────────┘
                  └───────────────┘

                  ┌────────────────────────────────┐
                  │  Grafana LGTM (observability)  │
                  │  3000=UI · 4317/4318=OTLP in   │
                  └────────────────────────────────┘
```

---

## Requirement Map (R1–R13)

| R   | Coverage                                    | Where                                        |
|-----|---------------------------------------------|----------------------------------------------|
| R1  | Business scenario, 5 use cases, NFR targets | report (Business Requirements §)             |
| R2  | ER + architecture + project + compose graph | report (Domain Model + System Architecture §) |
| R3  | Postgres + Alembic + seed                   | `server/models.py`, `server/db/versions/`, `server/db/seed.py` |
| R4  | REST API + OpenAPI                          | `server/auth/routers/`, served at `/docs`    |
| R5  | Polyglot: Mongo (timetable, chat) + Redis (cache, rate-limit, chat backlog) | docker-compose, `server/time_table_backend/`, `server/auth/ws/chat.py` |
| R6  | Postgres GIN on `club_posts.body`, Mongo index on `groups`, Redis dashboard cache | migration `a1b2c3d4e5f6`, report Optimisation § |
| R7  | WebSocket (chat) + GraphQL (dashboard)      | `server/auth/ws/chat.py`, `server/auth/graphql_api/` |
| R8  | Nginx gateway + 2 backend replicas (least_conn) | `server/gateway/nginx.conf`, compose `backend-1`/`backend-2` |
| R9  | docker-compose with healthchecks + volumes  | `server/docker-compose.yaml`                 |
| R10 | Airflow batch pipeline (2 DAGs)             | `server/timetable_web_scraping/dags/`        |
| R11 | Token-bucket rate limiter (Redis-backed, Lua-atomic) | `server/auth/rate_limiter/`         |
| R12 | OpenTelemetry → Grafana LGTM (traces+logs+metrics) | `server/auth/telemetry.py`, `server/observability/docker-compose.yaml` |
| R13 | README + CHANGELOG + OpenAPI                | this file, `CHANGELOG.md`, `/docs`           |

---

## Environment variables

`server/.env`:

| Variable                | Purpose                                    |
| ----------------------- | ------------------------------------------ |
| `DB_USER`               | Postgres user                              |
| `DB_PASSWORD`           | Postgres password                          |
| `DB_NAME`               | Postgres database name                     |
| `DB_HOST`               | (in-container) Postgres host               |
| `DB_PORT`               | (in-container) Postgres port               |
| `MONGO_HOST`            | Mongo host (default `mongodb`)             |
| `MONGO_PORT`            | Mongo port                                 |
| `MONGO_DB`              | Mongo DB name                              |
| `SECRET_KEY`            | JWT signing secret                         |
| `ALGORITHM`             | JWT algorithm (HS256)                      |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime (default 30)            |
| `FERNET_KEY`            | Airflow secret                             |
| `AIRFLOW_UID`           | UID for Airflow file ownership             |

---

## Endpoints

### REST (auth-protected unless noted)
- `POST /register` — public
- `POST /login` — public, returns `{access_token, token_type}`
- `GET  /me` — current user
- `GET  /healthz` — public
- `GET  /clubs`, `GET /clubs/{id}`, `POST /clubs/{id}/join`, `DELETE /clubs/{id}/leave`, `GET /clubs/{id}/members`
- `GET  /clubs/{id}/posts`, `POST /clubs/{id}/posts` ← rate-limited (5 burst, 0.2 tok/s)
- `POST /bookings`, `GET /bookings`, `DELETE /bookings/{id}`
- `GET  /dashboard`
- `GET  /timetable/group/{group_name}` ← protected
- `GET  /timetable/available_rooms`, `GET /timetable/occupied_rooms`

### GraphQL
- `POST /graphql` — single `dashboard(student_id)` query collapsing 4+ REST calls.

### WebSocket
- `WS /ws/chat/{club_id}?token=<jwt>` — receive `{type: backlog | message, …}` frames.

---

## Running tests / measurements

Cache + index measurements for the R6 Optimisation section:

```bash
# 1. Mongo index speedup
docker compose exec mongodb mongosh iut --eval \
  'db.timetable_with_groups.explain("executionStats").find({groups:"SOC-22-A"})'
docker compose exec mongodb mongosh iut --eval \
  'db.timetable_with_groups.createIndex({groups: 1})'
# rerun the explain

# 2. Postgres GIN full-text search
docker compose exec backend-postgres psql -U $DB_USER -d $DB_NAME -c \
  "EXPLAIN ANALYZE SELECT id FROM club_posts WHERE to_tsvector('english', body) @@ to_tsquery('database');"

# 3. wrk benchmark on /dashboard (install wrk first)
wrk -t2 -c10 -d20s -H "Authorization: Bearer $TOKEN" http://localhost:8088/dashboard
```

---

## Project layout

```
.
├── frontend/                 # React + Vite + shadcn/ui
│   └── src/app/
│       ├── components/       # LoginPage, OverviewPage, CommunityPage, ChatPanel…
│       └── lib/api.ts        # fetch wrapper + JWT + WebSocket helpers
└── server/
    ├── auth/                 # FastAPI auth service
    │   ├── main.py
    │   ├── routers/          # clubs, posts, bookings, dashboard
    │   ├── ws/chat.py        # WebSocket chat (Redis backlog + Mongo persist)
    │   ├── graphql_api/      # graphene schema + POST /graphql
    │   ├── rate_limiter/     # from-scratch token-bucket (Redis Lua)
    │   └── telemetry.py      # OpenTelemetry bootstrap
    ├── time_table_backend/   # FastAPI timetable service
    ├── timetable_web_scraping/
    │   └── dags/             # Airflow DAGs (iut_data_extractor, nightly_analytics)
    ├── db/
    │   ├── versions/         # Alembic migrations
    │   └── seed.py           # idempotent demo data
    ├── gateway/              # nginx.conf, proxy.conf
    ├── observability/        # Grafana LGTM include
    ├── docker-compose.yaml
    └── models.py
```

---

## Team

Submitted by Team … (see `LINKS.txt`).

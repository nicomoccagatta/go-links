# go/links

An internal URL shortcut service: create `go/oncall`, see every link, visit one and get redirected.
This is a first iteration meant for teammates to keep building on: a FastAPI + SQLite API and a
React single-page app, with end-to-end types generated from the API's OpenAPI schema.

## How to run

Prerequisites: Python 3.14 with [uv](https://docs.astral.sh/uv/), and Node 24 with pnpm. The web app
pins pnpm 12.4.1 through `devEngines`; an older pnpm downloads it on first use.

```sh
make setup   # uv sync + pnpm install
make api     # API on http://localhost:8000 (interactive docs at /docs and /redoc)
make web     # UI on http://localhost:5173, proxies /api to the API
```

Then create a link in the UI and open `http://localhost:8000/<slug>`. Opening a slug that doesn't
exist lands on the UI with the create form prefilled.

| Command      | What it does                                                                |
| ------------ | --------------------------------------------------------------------------- |
| `make test`  | pytest (API) and Vitest (web)                                               |
| `make check` | ruff lint + format check, Pyrefly, and `vp check` (Oxfmt, Oxlint, TS 7)     |
| `make gen`   | Regenerates `web/src/api/schema.d.ts` from the API's OpenAPI schema          |

Configuration (environment variables; the defaults suit local dev):

| Variable           | Default                  | Used for                                         |
| ------------------ | ------------------------ | ------------------------------------------------ |
| `DATABASE_URL`     | `sqlite:///./golinks.db` | SQLAlchemy URL                                   |
| `GO_BASE_URL`      | `http://localhost:8000`  | Where `go/` resolves; used to reject loop links  |
| `FRONTEND_URL`     | `http://localhost:5173`  | Where unknown slugs are sent to be created       |
| `LOG_LEVEL`        | `INFO`                   | JSON log level                                   |
| `VITE_GO_BASE_URL` | `http://localhost:8000`  | Build-time: the base for `go/<slug>` hrefs in UI |

### API

| Method | Path                | Result                                                                  |
| ------ | ------------------- | ----------------------------------------------------------------------- |
| GET    | `/api/links`        | 200 `{ items: Link[] }`, sorted by slug                                 |
| POST   | `/api/links`        | 201 + `Location`; 409 `slug_taken`; 422 `validation_error`             |
| GET    | `/api/links/{slug}` | 200 or 404 `link_not_found`                                            |
| GET    | `/{slug}`           | 302 to the target, or to `FRONTEND_URL/?new=<slug>` if it doesn't exist |
| GET    | `/healthz`          | 200 `{ status: "ok" }` after a DB round trip, else 503                  |
| GET    | `/metrics`          | Prometheus exposition format                                            |

Every non-2xx JSON response has the same shape, and it's part of the OpenAPI schema, so the web
client gets it typed:

```json
{ "error": { "code": "slug_taken", "message": "go/oncall already exists.", "request_id": "…",
             "details": [{ "field": "slug", "message": "go/oncall is already taken." }] } }
```

### Layout

```
api/src/golinks_api/
  main.py           app factory: settings, DB, middleware, routes
  routes.py         every endpoint: /api/links, /healthz, /metrics, and /{slug} last
  db.py             engine, session dependency, Link model
  schemas.py        request/response models and validation rules
  errors.py         ApiError, the error envelope, exception handlers
  middleware.py     request ID, access log, metrics, 500 envelope
  observability.py  JSON log formatter, Prometheus metrics
web/src/
  api/              openapi-fetch client, generated schema, ApiError parser
  links/            queries, validation, create form, list with filter
  components/       TextField, Notice, button styles
```

## Assumptions

- It runs on a trusted internal network, so there's no authentication (per the brief).
- Slugs are case-insensitive: trimmed and lowercased on the way in, stored lowercase. They must match
  `^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$`. Paths the service owns (`api`, `healthz`, `metrics`,
  `docs`, `redoc`, `static`) are reserved.
- Targets are stored exactly as entered, and must be absolute `http(s)` URLs with a host.
- A target on the same **hostname** as `GO_BASE_URL` is rejected so links can't loop. Ports are
  ignored, so in local dev every `localhost` target is rejected.
- A blank description is stored as `null`.
- A miss is an invitation: unknown `go/<slug>` redirects to the UI's create form, prefilled.
- Making `go/` resolve on the network (DNS or a search domain) happens outside this repo.
- Links are immutable once created (see "Not built").
- Visit counts are approximate: every GET counts, including link-preview bots.

## Tradeoffs

**Cutting-edge dev tooling, boring runtime.** What ships is latest stable: FastAPI, Pydantic 2,
SQLAlchemy 2.0 (2.1 isn't final), React 19.3 and TanStack Query 5. These use version ranges, with
lockfiles for reproducibility. The dev tools are pinned exactly, because several are pre-1.0 (Vite+
0.3, Oxfmt 0.x, `@rolldown/plugin-babel` 0.x) and change behavior between releases. None of them
ship, so if one breaks, a check fails; the service doesn't.

**TypeScript 7, with codegen isolated.** TS 7 (the Go port) is pinned to the exact version that
`oxlint-tsgolint` tracks. `openapi-typescript` still needs the TypeScript compiler API, which TS 7
doesn't ship, so `make gen` runs it in a throwaway `pnpm dlx` with TS 5.9 (its declared peer). The
generated `.d.ts` is plain TypeScript that TS 7 checks fine, and it's committed. That workaround
goes away once TS 7.1 ships a compiler API.

**Pyrefly, not mypy or ty.** Pyrefly is stable (1.x), fast, and understands Pydantic and
pydantic-settings without plugins. mypy would need the Pydantic plugin and is slower. ty is still
beta, and I didn't want a pre-1.0 checker gating backend correctness.

**Vite+ (Oxlint, Oxfmt, tsgolint, Vitest) instead of ESLint and Prettier.** One toolchain, one
config file (`vite.config.ts`), type-aware lint, and it's much faster. The cost is a smaller rule
ecosystem (no full `jsx-a11y` equivalent, for example) and a 0.x wrapper, hence the pinning. The
fallback is plain Vite plus Oxlint. The React Compiler runs through the documented Babel preset,
because plugin-react 6's native compiler option is marked experimental.

**The counter write sits on the redirect's hot path.** Each redirect runs one atomic
`UPDATE … SET visit_count = visit_count + 1 … RETURNING target_url`: no lost increments and no
read-then-write. It's simple and correct, but it makes every redirect a write, and SQLite
serializes writers. At scale, redirects should read from a cache and emit visit events that get
aggregated asynchronously.

**Sync over async.** Endpoints are plain `def` with a sync SQLAlchemy session, run on FastAPI's
threadpool. SQLite gains nothing from async, and sync code is easier to read and test. With
Postgres under real load, I'd move to an async driver, or keep sync and size the pool.

**Metrics cardinality.** Prometheus labels use the route template (`/{slug}`), never the raw path,
and unmatched paths are labeled `unmatched`. Anyone requesting random URLs would otherwise create
unbounded series. Per-link popularity belongs in the database (`visit_count`), not in labels.

Smaller calls:

- **302, not 301.** Browsers cache a 301 permanently, so changing a target would silently not apply.
- **Duplicate slugs are caught by the unique constraint.** The `IntegrityError` maps to 409, rather
  than a check-then-insert that can race.
- **The client mirrors the server's validation.** That gives instant feedback, but the server stays
  the source of truth: 409 and 422 `details` map onto form fields. The redirect-loop check is
  server-only, because it depends on server config.
- **The app factory (`create_app(settings)`) gives each test its own SQLite file** without
  dependency overrides.
- **pytest still uses httpx.** Starlette 1.6 deprecates `httpx` for its TestClient in favor of
  `httpx2`, so pytest prints that warning. I kept the specified stack; switching is a one-line dev
  dependency change.

## Not built, and why

- **Auth and link ownership.** Out of scope for the brief. They're the prerequisite for most of
  what's next.
- **Edit and delete.** Without ownership, anyone could repoint `go/payroll` to a phishing page.
  These come with SSO.
- **Analytics beyond the counter,** including filtering bot and unfurler traffic that inflates
  counts.
- **A cache layer.** Unneeded at this size, and it adds invalidation questions.
- **Pagination and server-side search.** The list is small, and a client-side filter covers it.
- **Migrations.** `create_all` is enough until the schema changes; Alembic comes then.
- **Docker and CI.** The brief asked not to; `make check` and `make test` are what CI would run.
- **OpenTelemetry tracing.** A next step; request IDs are the bridge until then.
- **A Trusted Types CSP.** Relevant hardening for an app that renders URLs, and React 19.3
  supports it.
- **Broad frontend tests.** Only the `ApiError` envelope parser is tested. The first ones to add
  would cover the form: `?new=` prefill and mapping 409/422 `details` to fields.

## What I'd do with another day

- **SSO with link ownership, then edit and delete.** Ownership is what makes them safe.
- **Cache hot redirects** (in-process LRU or Redis), and move visit counting to **async events**
  so the redirect path is read-only.
- **OpenTelemetry tracing**, carrying the request ID as a span attribute.
- **A Trusted Types CSP.**
- **Parameterized links:** `go/jira/123` expands a template like `https://jira…/browse/{1}`.
- **Dead-target detection:** a periodic check that flags links whose target returns 404.
- **DNS or a search domain** so `go/` resolves on the network, and browser extension or PAC
  guidance.
- **Postgres**, with Alembic migrations.
- **Frontend tests** for the form flows above, and filtering bots out of visit counts.
- **Form polish** left out to keep this iteration small: moving focus to the first invalid field on
  submit, and animating new links in with `<ViewTransition>`.

## Time spent

About an hour, in three passes:

- **~20 min: toolchain setup.** Resolving versions, scaffolding both apps, and smoke-testing the
  cutting-edge pieces (Vite+, TS 7, codegen on an isolated TS) before relying on them. This is a
  one-off cost that most of the first commit reflects.
- **~30 min: the build.** API, web app, tests and this README.
- **~15 min: a simplification pass** after reviewing the code: fewer modules, and the optional UI
  extras dropped.

I used Claude Code as a pair programmer, as the brief allows. I set the stack, the rules and the
scope, made the calls on the tradeoffs above, and reviewed the code.

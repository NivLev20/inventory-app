# Smart Retail Inventory – Application

Inventory management for a multi-store retail chain: track stock per store, get alerted when products drop below their minimum level, restock with one click, and follow stock trends on a dashboard.

This is the **application repository** of the project. Infrastructure (Kubernetes manifests, Jenkins pipeline, monitoring) lives in the `inventory-devops` repository.

## For reviewers

The infrastructure repository `inventory-devops` holds the Kubernetes manifests, the Jenkins pipeline and monitoring. Its README has a **requirements coverage** table that maps every item of the project brief to a file, and a one-command install (`scripts/bootstrap.sh`).

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Flask, gunicorn |
| Database | PostgreSQL 16 |
| Frontend | React 18, Vite, Chart.js, served by nginx |
| Containers | Docker (multi-stage builds, non-root images), Docker Compose |
| Quality | pytest (26 tests), flake8, ESLint |
| Observability | Prometheus metrics endpoint (`/metrics`) |

## Architecture

```
Browser ──► frontend (nginx :8080) ──/api──► backend (Flask :5000) ──► PostgreSQL (:5432, internal only)
                                                   │
                                                   └── /metrics ──► Prometheus ──► Grafana
```

## Repository layout

```
inventory-app/
├── backend/                  Flask REST API
│   ├── app.py                Endpoints and business logic
│   ├── db.py                 Database layer (PostgreSQL in runtime, SQLite in tests)
│   ├── seed.py               Demo data: 12 products, 3 stores, 14 days of history
│   ├── simulator.py          Store activity simulator (run as Kubernetes CronJobs)
│   ├── openapi.py            OpenAPI specification for /api/docs
│   ├── tests/               Unit tests (API and simulator)
│   ├── requirements.txt      Runtime dependencies
│   ├── requirements-dev.txt  Test and lint dependencies
│   └── Dockerfile
├── frontend/                 React dashboard
│   ├── src/App.jsx           Root component: loads data and holds state
│   ├── src/components/       One component per dashboard section
│   ├── src/api.js            All backend calls in one place
│   ├── vite.config.js        Vite config, /api proxy for local development
│   ├── nginx.conf.template   Serves the build and proxies /api to the backend
│   └── Dockerfile            Multi-stage: Node builds, nginx serves
└── docker-compose.yml        Local environment: db + backend + frontend
```

## Quick start

Requires Docker only.

```bash
docker compose up --build -d
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:8080 |
| API | http://localhost:5000/api/products |
| Health check | http://localhost:5000/health |

Stop with `docker compose down`. Data persists in the `pgdata` volume.

To change the local database password, copy `.env.example` to `.env` and edit it. `.env` is git-ignored.

## Development

### Frontend

The backend must be running (`docker compose up -d db backend`).

```bash
cd frontend
npm install      # first time, or after package.json changes
npm run dev      # http://localhost:5173 with hot reload
npm run lint
```

`package-lock.json` is committed so that local, Docker and CI builds install identical dependency versions.

### Backend tests and lint

Run inside a throwaway container, no local Python required:

```bash
docker run --rm -v "$PWD/backend:/app" -w /app python:3.12-slim \
  sh -c "pip install -q -r requirements-dev.txt && flake8 . && pytest -q"
```

Tests use a temporary SQLite database, so CI does not need a PostgreSQL server.

## API reference

| Method | Path | Description |
|---|---|---|
| GET | `/api/products` | List products. Filters: `?store=Haifa&status=LOW` |
| GET | `/api/products/<id>` | Get one product |
| POST | `/api/products` | Create a product. Required: `name`, `sku`. Optional: `stock`, `min_stock`, `price`, `category`, `store` |
| PUT | `/api/products/<id>` | Update a product or its stock |
| DELETE | `/api/products/<id>` | Delete a product |
| POST | `/api/products/<id>/restock` | Add stock. Required: `quantity`. Optional: `note` |
| POST | `/api/products/<id>/sell` | Record a sale (decreases stock). Required: `quantity` |
| GET | `/api/restocks` | Restock history |
| GET / PUT | `/api/simulation` | Read / set whether the store simulator runs (`{"enabled": true}`) |
| POST | `/api/simulation/rush` | Rush hour: about 20 random purchases immediately |
| GET | `/api/products/low-stock` | Products at or below their minimum, with a suggested reorder quantity |
| GET | `/api/products/analytics` | Totals and 14-day trends for the dashboard |
| GET | `/health` | Liveness probe: the process is running |
| GET | `/ready` | Readiness probe: the database is reachable |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/docs` | Interactive API documentation (Swagger UI) |
| GET | `/api/openapi.json` | OpenAPI 3 specification |

Example:

```bash
curl -X POST http://localhost:5000/api/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Laptop Stand","sku":"ELC-010","stock":4,"min_stock":10,"store":"Haifa","price":129}'

curl -X POST http://localhost:5000/api/products/1/restock \
  -H "Content-Type: application/json" \
  -d '{"quantity":25,"note":"supplier order"}'
```

## Features

- **Automatic stock status** per product: `OK`, `LOW` (at or below minimum) or `OUT`.
- **Suggested reorder quantity**: enough to reach twice the minimum level, exposed as a one-click "Order" button.
- **Multi-store**: every product belongs to a store; the dashboard filters by store and status.
- **Trends**: total units over 14 days, and units sold vs restocked per day.
- **Store simulator**: `simulator.py sales` makes random purchases (and supplier deliveries for sold-out items); `simulator.py new-product` launches the next product from a fixed catalog. In Kubernetes they run as CronJobs, so the dashboard and Grafana show live activity. The dashboard can pause or resume them and trigger a "rush hour".
- **API documentation**: interactive Swagger UI at `/api/docs`.
- **Business metrics for Prometheus**, beyond API latency: `inventory_low_stock_products`, `inventory_out_of_stock_products`, `inventory_units_total`, `inventory_value`, `inventory_units_sold_today`.

## Configuration

| Variable | Default | Description | Kubernetes source |
|---|---|---|---|
| `DATABASE_URL` | `sqlite:///inventory.db` | Database connection string, e.g. `postgresql://user:pass@host:5432/db` | Secret |
| `APP_ENV` | `development` | Environment name | ConfigMap |
| `SEED_DATA` | `false` | Load demo data when the database is empty | ConfigMap |
| `BACKEND_URL` | `http://backend:5000` | Frontend only: where nginx proxies `/api` | ConfigMap |

## Security notes

- Containers run as non-root users on minimal base images (`slim`, `alpine`).
- The database port is not published outside the Docker network.
- Secrets are never committed: `.env` is git-ignored and only `.env.example` with placeholder values is tracked.
- All SQL uses parameterized queries; API input is validated.

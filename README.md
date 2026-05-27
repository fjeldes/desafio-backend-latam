# User Management API

RESTful API for user management with full CRUD operations built with FastAPI.

## Project Structure

```
.
├── app/
│   ├── main.py          # FastAPI app entry point, middleware, lifespan
│   ├── routes.py        # HTTP endpoint definitions (delegates to CRUD)
│   ├── crud.py          # Business logic and database operations
│   ├── models.py        # SQLAlchemy ORM models (User table, Role enum)
│   ├── schemas.py        # Pydantic validation schemas (request/response)
│   ├── database.py      # Database engine, session factory, get_db dependency
│   └── limiter.py       # Rate limiting configuration (slowapi)
├── tests/
│   ├── conftest.py      # Pytest fixtures (isolated test DB, TestClient)
│   ├── test_api.py       # Integration tests for all CRUD endpoints
│   └── test_rate_limiting.py  # Rate limiting saturation tests
├── Dockerfile           # Container image (Python 3.11-slim)
├── docker-compose.yml   # Local dev: api, test, and test-rate-limit services
├── cloudbuild.yaml      # CI/CD pipeline (Cloud Build)
├── setup-gcp.sh         # One-time GCP infrastructure provisioning
└── requirements.txt
```

**Architecture**: layered pattern — routes delegate to CRUD, CRUD uses SQLAlchemy models + Pydantic schemas, database sessions are injected via FastAPI's dependency injection.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI (Python 3.11) |
| ORM | SQLAlchemy 2.0 (SQLite dev, PostgreSQL prod) |
| Validation | Pydantic v2 |
| Rate limiting | slowapi (per-IP, configurable) |
| Testing | pytest + httpx (29 tests) |
| Container | Docker + docker-compose |
| CI/CD | Google Cloud Build (`cloudbuild.yaml`) |
| Deployment | Cloud Run + Cloud SQL + Secret Manager |
| Infrastructure | `setup-gcp.sh` (idempotent shell script) |

## Quick Start with Docker

### Run the API

```bash
docker-compose up api
```

The API will be available at `http://localhost:8080`.
Interactive docs: `http://localhost:8080/docs`

### Run Tests

```bash
# Main integration tests (rate limiting disabled)
docker-compose run --rm test

# Rate limiting tests (rate limiting enabled)
docker-compose run --rm test-rate-limit
```

## API Endpoints

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| `GET` | `/health` | Health check | No limit |
| `GET` | `/users` | List users (paginated, filterable) | 60/min |
| `GET` | `/users/{id}` | Get user by ID | 60/min |
| `POST` | `/users` | Create a new user | 20/min |
| `PUT` | `/users/{id}` | Update a user (partial) | 30/min |
| `DELETE` | `/users/{id}` | Delete a user | 10/min |
| `PATCH` | `/users/{id}/deactivate` | Soft-deactivate a user | 10/min |

### Examples

**Create a User:**
```bash
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jperez",
    "email": "juan@example.com",
    "first_name": "Juan",
    "last_name": "Perez",
    "role": "user",
    "active": true
  }'
```

**List Users (with filters):**
```bash
curl "http://localhost:8080/users?skip=0&limit=10&active=true&role=admin"
```

**Update a User:**
```bash
curl -X PUT http://localhost:8080/users/{user_id} \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Juan Carlos", "last_name": "Perez Gomez"}'
```

**Delete / Deactivate:**
```bash
curl -X DELETE http://localhost:8080/users/{user_id}
curl -X PATCH http://localhost:8080/users/{user_id}/deactivate
```

### Response Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Read, update, delete, deactivate |
| 201 | Created | User created successfully |
| 400 | Bad Request | Empty update body |
| 404 | Not Found | User ID doesn't exist |
| 409 | Conflict | Duplicate username or email |
| 422 | Unprocessable | Validation error (invalid email, role, etc.) |
| 429 | Too Many Requests | Rate limit exceeded |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./users.db` |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `RATE_LIMIT_ENABLED` | Toggle rate limiting (`"false"` to disable) | `true` |

## Testing Strategy

**29 tests** organized by endpoint, covering every CRUD operation:

| Test Class | Tests | Covers |
|------------|-------|--------|
| `TestHealthCheck` | 1 | `GET /health` |
| `TestCreateUser` | 9 | Success, defaults, duplicate username/email, invalid email, short username, invalid chars, missing fields, invalid role |
| `TestGetUser` | 2 | Success, 404 not found |
| `TestListUsers` | 5 | Empty list, with data, pagination, filter by active, filter by role |
| `TestUpdateUser` | 4 | Success, 404, duplicate conflict, empty body |
| `TestDeleteUser` | 2 | Success + verify deleted, 404 |
| `TestDeactivateUser` | 2 | Success, 404 |
| `TestPostRateLimit` | 2 | 20 req → 201, 21st → 429 |
| `TestDeleteRateLimit` | 1 | 10 deletes → 200, 11th → 429 |
| `TestDeactivateRateLimit` | 1 | 10 deactivations → 200, 11th → 429 |
| `TestHealthNoRateLimit` | 1 | 50 health checks → all 200 |

- **Isolated database**: each test gets a clean SQLite database (drop_all/create_all)
- **Rate limiting tests**: run separately with `RATE_LIMIT_ENABLED=true` to verify saturation limits
- **Main tests**: run with `RATE_LIMIT_ENABLED=false` to avoid flakiness
- **Run locally**: `docker-compose run --rm test`

## Security

### Data Validation
Pydantic v2 schemas enforce strict constraints:
- `username`: 3–50 chars, alphanumeric + underscores only (regex)
- `email`: RFC 5322 validated via `EmailStr`
- `first_name` / `last_name`: 1–100 chars
- `role`: restricted enum (`admin`, `user`, `guest`)
- Extraneous fields are silently ignored

### Rate Limiting
Per-IP limits via slowapi protect against abuse (see endpoint table above). Returns `HTTP 429` when exceeded. Disable during testing with `RATE_LIMIT_ENABLED=false`.

### SQL Injection Prevention
All queries use SQLAlchemy ORM with parameterized queries. No raw SQL is executed.

### Production Hardening
| Concern | Solution |
|---------|----------|
| Database credentials | Stored in Secret Manager, never in code or images |
| Cloud SQL access | Auth Proxy via Unix socket (no public IP), authenticated via IAM |
| HTTPS | Automatic TLS termination via Cloud Run |
| Integrity errors | Caught and mapped to specific 409 messages (username vs email) |
| Transaction safety | Rollback on error before re-raising exceptions |
| Logging | Request-level logging middleware + per-operation logs, level configurable |

### Recommended Next Steps (documented, not implemented)
- **Authentication**: JWT or API key auth for write endpoints
- **Distributed rate limiting**: Redis-backed limiter for multi-instance Cloud Run
- **CORS**: Restrict origins via `CORSMiddleware`
- **Migrations**: Alembic for versioned database schema changes
- **Audit logging**: Structured logging of create/update/delete operations

## CI/CD Pipeline

On every push to `main`, Cloud Build runs `cloudbuild.yaml`:

```
GitHub push → Cloud Build trigger → ┬ build-image       (~40s)
                                     ├ run-tests         (~60s)
                                     │   └─ main tests (no rate limit)
                                     │   └─ rate-limit tests
                                     ├ push-image        (~20s)
                                     └ deploy-to-cloud-run (~20s)
                                                │
                                    https://<service>.a.run.app
```

If any step fails, the pipeline stops — images are never pushed and never deployed.

## Deployment to GCP

### 1. Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- A GCP project with billing enabled

### 2. Provision infrastructure (one-time)

```bash
export PROJECT_ID="<YOUR_PROJECT_ID>"
bash setup-gcp.sh
```

This idempotent script creates all GCP resources the pipeline needs:

| Resource | Details |
|----------|---------|
| Artifact Registry | Docker repo `user-management-api` in `us-central1` |
| Cloud SQL | PostgreSQL 16, `db-f1-micro`, database `users_db`, user `app_user` |
| Service Account | `user-api-cloud-run` with `roles/cloudsql.client` |
| Secret Manager | `database-url` with the full connection string |
| IAM bindings | Cloud Run SA can read secrets; Cloud Build & Compute SAs can deploy |

Safe to re-run — existing resources are skipped. Cloud SQL creation takes ~10 minutes the first time.

### 3. Create the Cloud Build trigger

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Click **Create Trigger**
3. Fill in:
   - **Name**: `deploy-on-push`
   - **Event**: Push to a branch
   - **Repository**: select this GitHub repository
   - **Branch**: `^main$`
   - **Configuration**: Cloud Build configuration file → `cloudbuild.yaml`
   - **Service account**: select the **Compute Engine default service account** (`...-compute@developer.gserviceaccount.com`)
4. Click **Create**

> **Important**: the trigger's service account must be the Compute Engine default SA (not the Cloud Run SA). `setup-gcp.sh` grants this SA all necessary permissions (`run.admin`, `artifactregistry.writer`, `iam.serviceAccountUser`).

### 4. Deploy

Push to `main`:

```bash
git push origin main
```

Cloud Build automatically builds, tests (full suite including rate limiting), pushes the image, and deploys to Cloud Run.

### 5. Verify

```bash
curl https://<cloud-run-url>/health
# {"status":"healthy"}

curl https://<cloud-run-url>/docs
# Interactive Swagger UI
```

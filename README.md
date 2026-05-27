# User Management API

RESTful API for user management with full CRUD operations built with FastAPI.

## Tech Stack

- **FastAPI** - Python web framework
- **SQLAlchemy** - ORM (SQLite for local dev, PostgreSQL for production)
- **Pydantic** - Data validation
- **Pytest** - Testing
- **Docker** - Containerization
- **GCP Cloud Run / Cloud SQL / Cloud Build** - Deployment

## Quick Start with Docker

### Run the API

```bash
docker-compose up api
```

The API will be available at `http://localhost:8080`.

Interactive docs: `http://localhost:8080/docs`

### Run Tests

```bash
docker-compose run --rm test
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/users` | List users (paginated, filterable) |
| `GET` | `/users/{id}` | Get user by ID |
| `POST` | `/users` | Create a new user |
| `PUT` | `/users/{id}` | Update a user |
| `DELETE` | `/users/{id}` | Delete a user |
| `PATCH` | `/users/{id}/deactivate` | Deactivate a user |

### Create a User

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

### List Users

```bash
curl http://localhost:8080/users
curl "http://localhost:8080/users?skip=0&limit=10&active=true&role=admin"
```

### Get a User

```bash
curl http://localhost:8080/users/{user_id}
```

### Update a User

```bash
curl -X PUT http://localhost:8080/users/{user_id} \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Juan Carlos", "last_name": "Perez Gomez"}'
```

### Delete a User

```bash
curl -X DELETE http://localhost:8080/users/{user_id}
```

### Deactivate a User

```bash
curl -X PATCH http://localhost:8080/users/{user_id}/deactivate
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./users.db` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `RATE_LIMIT_ENABLED` | Toggle rate limiting (set to `"false"` to disable) | `true` |

## Security Considerations

### Data Validation
All inputs are validated through Pydantic schemas with strict constraints:
- `username`: 3-50 chars, alphanumeric + underscores only (regex pattern)
- `email`: validated against RFC 5322 format via `EmailStr`
- `first_name` / `last_name`: 1-100 chars, required
- `role`: restricted enum (`admin`, `user`, `guest`)
- Extraneous fields are silently ignored

### Rate Limiting
Per-IP rate limits protect the API from abuse. Limits are enforced via slowapi:

| Endpoint | Limit |
|---|---|
| `GET /health` | No limit |
| `GET /users`, `GET /users/{id}` | 60 req/min |
| `POST /users` | 20 req/min |
| `PUT /users/{id}` | 30 req/min |
| `DELETE /users/{id}`, `PATCH .../deactivate` | 10 req/min |

When a limit is exceeded, the API returns `HTTP 429 Too Many Requests`.

### SQL Injection Prevention
All database queries use SQLAlchemy's ORM with parameterized queries. No raw SQL is executed. The `check_same_thread=False` flag for SQLite is only used in development mode.

### Cloud SQL Network Security
The production database (Cloud SQL) does **not** expose its public IP to the internet. Cloud Run connects exclusively via the Cloud SQL Auth Proxy through a Unix socket (`/cloudsql/<connection_name>`), which authenticates using IAM service account credentials. No passwords or connection strings are stored in the container image.

### Secrets Management
- `DATABASE_URL` is injected at runtime via environment variable (local) or Google Secret Manager (production)
- Deployments (`cloudbuild.yaml`) reference secrets by name, never by value

### HTTPS
Cloud Run provides automatic TLS termination. All traffic is encrypted in transit.

### Production Hardening (recommended next steps)
- **Authentication**: Add API key or JWT-based auth for write endpoints
- **Distributed rate limiting**: Replace in-memory slowapi with Redis-backed rate limiter for multi-instance Cloud Run deployments
- **CORS**: Restrict allowed origins via `CORSMiddleware` if the API is consumed from a browser
- **Audit logging**: Log user mutations (create/update/delete) to a structured log sink
- **Cloud SQL**: Consider using private IP + VPC for defense in depth, though the Auth Proxy already provides secure access

## Deployment to GCP

### 1. Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
- A GCP project with billing enabled

### 2. Create infrastructure (one-time setup)

```bash
export PROJECT_ID="<YOUR_PROJECT_ID>"
bash setup-gcp.sh
```

This idempotent script creates:
- **Artifact Registry** – Docker repository for container images
- **Cloud SQL** – PostgreSQL 16 instance (db-f1-micro)
- **Service Account** – For Cloud Run with Cloud SQL permissions
- **Secret Manager** – `DATABASE_URL` stored securely
- **IAM bindings** – Cloud Build can deploy, Cloud Run can read secrets and connect to DB

Safe to re-run — existing resources are skipped. Cloud SQL creation takes ~10 minutes the first time.

### 3. Connect GitHub to Cloud Build

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Create a trigger linked to this GitHub repository
3. Set branch: `^main$`
4. Configuration: Cloud Build configuration file (`cloudbuild.yaml`)

### 4. Deploy

Push to `main`:

```bash
git push origin main
```

Cloud Build automatically:
1. Builds the Docker image
2. Runs tests (unit + rate limiting)
3. Pushes the image to Artifact Registry
4. Deploys to Cloud Run with Cloud SQL connection and DATABASE_URL secret

### 5. Test in production

```bash
curl https://<cloud-run-url>/health
curl https://<cloud-run-url>/docs
```

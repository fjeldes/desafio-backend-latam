# User Management API

RESTful API for user management with full CRUD operations built with FastAPI.

## Tech Stack

- **FastAPI** - Python web framework
- **SQLAlchemy** - ORM (SQLite for local dev, PostgreSQL for production)
- **Pydantic** - Data validation
- **Pytest** - Testing
- **Docker** - Containerization
- **GCP Cloud Run** - Deployment

## Quick Start with Docker

### Run the API

```bash
docker compose up api
```

The API will be available at `http://localhost:8080`.

Interactive docs: `http://localhost:8080/docs`

### Run Tests

```bash
docker compose run --rm test
```

## API Endpoints

### Health Check

```bash
curl http://localhost:8080/health
```

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
# Get all users
curl http://localhost:8080/users

# With pagination and filters
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

## Deployment to GCP

This project uses Google Cloud Build for CI/CD. On each push to the main branch:

1. Docker image is built
2. Tests are executed
3. Image is pushed to Container Registry
4. Cloud Run deployment is triggered

### Prerequisites for GCP

1. Create a GCP project and enable billing
2. Enable APIs: Cloud Run, Cloud Build, Cloud SQL
3. Set up a PostgreSQL instance on Cloud SQL
4. Connect your GitHub repository to Cloud Build
5. Store `DATABASE_URL` as a secret in Cloud Build triggers

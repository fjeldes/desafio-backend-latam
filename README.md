# User Management API

RESTful API for user management with full CRUD operations built with FastAPI.

## Tech Stack

- **FastAPI** - Python web framework
- **SQLAlchemy** - ORM (SQLite for local dev, PostgreSQL for production)
- **Pydantic** - Data validation
- **Pytest** - Testing
- **Docker** - Containerization
- **Terraform** - Infrastructure as Code
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

## Deployment to GCP

### 1. Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
- [Terraform](https://developer.hashicorp.com/terraform/downloads) >= 1.5 installed
- A GCP project with billing enabled

### 2. Provision infrastructure with Terraform

```bash
cd terraform

# Copy and customize the variables file
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars → set your project_id

# Login to GCP
gcloud auth application-default login

# Initialize and apply
terraform init
terraform plan
terraform apply
```

This creates:
- **Artifact Registry** (Docker repository for container images)
- **Cloud SQL** (PostgreSQL 16, db-f1-micro)
- **Secret Manager** (DATABASE_URL stored securely)
- **Service Account** (for Cloud Run with Cloud SQL permissions)
- All required GCP APIs enabled

### 3. Outputs after `terraform apply`

After apply finishes, note the outputs. The `DATABASE_URL` secret is automatically stored in Secret Manager. You don't need to copy it manually.

### 4. Connect GitHub to Cloud Build

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Create a trigger linked to this GitHub repository
3. Set branch: `^main$`
4. Configuration: Cloud Build configuration file (`cloudbuild.yaml`)
5. Update the substitution `_CLOUD_RUN_SA` in the trigger to match your project ID (replace `PROJECT`)

### 5. Deploy

Push to `main`:

```bash
git push origin main
```

Cloud Build automatically:
1. Builds the Docker image
2. Runs tests
3. Pushes the image to Artifact Registry
4. Deploys to Cloud Run with the correct Cloud SQL connection

### 6. Test in production

```bash
curl https://<cloud-run-url>/health
curl https://<cloud-run-url>/docs
```

### Cleanup

```bash
cd terraform && terraform destroy
```

#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup-gcp.sh – One-time GCP infrastructure setup for cloudbuild.yaml
# ---------------------------------------------------------------------------
# Usage:
#   export PROJECT_ID="desafio-backend-latam"
#   bash setup-gcp.sh
#
# Creates all resources cloudbuild.yaml needs: Artifact Registry, Cloud SQL,
# Secret Manager, a Cloud Run service account, and IAM bindings.
# Safe to re-run – every step is idempotent.
# ---------------------------------------------------------------------------

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ -z "${PROJECT_ID:-}" ]; then
    echo -e "${RED}ERROR: PROJECT_ID is not set.${NC}"
    echo '  export PROJECT_ID="your-gcp-project-id"'
    exit 1
fi

REGION="${REGION:-us-central1}"
SA_NAME="user-api-cloud-run"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
SQL_INSTANCE="user-management-db"
DB_NAME="users_db"
DB_USER="app_user"
SECRET_NAME="database-url"
ARTIFACT_REPO="user-management-api"

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  GCP Infrastructure Setup                  ${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo ""

# ---------------------------------------------------------------------------
# 1. Enable required APIs
# ---------------------------------------------------------------------------
echo -e "${GREEN}[1/8] Enabling APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    sqladmin.googleapis.com \
    --project="${PROJECT_ID}" --quiet
echo "  Done."

# ---------------------------------------------------------------------------
# 2. Artifact Registry – Docker repository
# ---------------------------------------------------------------------------
echo -e "${GREEN}[2/8] Creating Artifact Registry repository...${NC}"
if gcloud artifacts repositories describe "${ARTIFACT_REPO}" \
    --location="${REGION}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "  Repository '${ARTIFACT_REPO}' already exists."
else
    gcloud artifacts repositories create "${ARTIFACT_REPO}" \
        --repository-format=docker \
        --location="${REGION}" \
        --project="${PROJECT_ID}"
    echo "  Repository created."
fi

# ---------------------------------------------------------------------------
# 3. Service Account for Cloud Run
# ---------------------------------------------------------------------------
echo -e "${GREEN}[3/8] Creating Cloud Run service account...${NC}"
if gcloud iam service-accounts describe "${SA_EMAIL}" \
    --project="${PROJECT_ID}" &>/dev/null; then
    echo "  Service account '${SA_EMAIL}' already exists."
else
    gcloud iam service-accounts create "${SA_NAME}" \
        --display-name="Cloud Run service account" \
        --project="${PROJECT_ID}"
    echo "  Service account created."
fi

# Grant Cloud SQL client role (Cloud Run needs this to connect via Auth Proxy)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudsql.client" \
    --condition=None --quiet 2>/dev/null || true

# ---------------------------------------------------------------------------
# 4. Cloud SQL – PostgreSQL instance (this step takes ~10 minutes)
# ---------------------------------------------------------------------------
echo -e "${GREEN}[4/8] Creating Cloud SQL instance (may take several minutes)...${NC}"
if gcloud sql instances describe "${SQL_INSTANCE}" \
    --project="${PROJECT_ID}" &>/dev/null; then
    echo "  Instance '${SQL_INSTANCE}' already exists."
else
    echo "  Creating PostgreSQL 16 instance (db-f1-micro) – please wait..."
    gcloud sql instances create "${SQL_INSTANCE}" \
        --database-version=POSTGRES_16 \
        --tier=db-f1-micro \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --quiet
fi

# ---------------------------------------------------------------------------
# 5. Database and user
# ---------------------------------------------------------------------------
echo -e "${GREEN}[5/8] Creating database and user...${NC}"
if gcloud sql databases describe "${DB_NAME}" \
    --instance="${SQL_INSTANCE}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "  Database '${DB_NAME}' already exists."
else
    gcloud sql databases create "${DB_NAME}" \
        --instance="${SQL_INSTANCE}" --project="${PROJECT_ID}"
    echo "  Database created."
fi

# Generate a random password if one doesn't exist yet
DB_PASSWORD_FILE="/tmp/gcp-db-password-${PROJECT_ID}"
if [ -f "${DB_PASSWORD_FILE}" ]; then
    DB_PASSWORD=$(cat "${DB_PASSWORD_FILE}")
    echo "  Using existing password from ${DB_PASSWORD_FILE}"
else
    DB_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
    echo "${DB_PASSWORD}" > "${DB_PASSWORD_FILE}"
    echo "  Password generated and saved to ${DB_PASSWORD_FILE}"
fi

if gcloud sql users describe "${DB_USER}" \
    --instance="${SQL_INSTANCE}" --project="${PROJECT_ID}" &>/dev/null 2>&1; then
    echo "  User '${DB_USER}' already exists – updating password..."
    gcloud sql users set-password "${DB_USER}" \
        --instance="${SQL_INSTANCE}" --password="${DB_PASSWORD}" \
        --project="${PROJECT_ID}" --quiet
else
    gcloud sql users create "${DB_USER}" \
        --instance="${SQL_INSTANCE}" --password="${DB_PASSWORD}" \
        --project="${PROJECT_ID}"
    echo "  User created."
fi

# ---------------------------------------------------------------------------
# 6. Secret Manager – DATABASE_URL
# ---------------------------------------------------------------------------
CLOUDSQL_CONNECTION="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"
DATABASE_URL="postgresql+psycopg2://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CLOUDSQL_CONNECTION}"

echo -e "${GREEN}[6/8] Storing DATABASE_URL in Secret Manager...${NC}"
if gcloud secrets describe "${SECRET_NAME}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "  Secret '${SECRET_NAME}' already exists – adding new version."
else
    gcloud secrets create "${SECRET_NAME}" \
        --replication-policy="automatic" \
        --project="${PROJECT_ID}"
    echo "  Secret created."
fi
echo -n "${DATABASE_URL}" | gcloud secrets versions add "${SECRET_NAME}" \
    --data-file=- --project="${PROJECT_ID}" --quiet
echo "  Secret version added."

# Grant Cloud Run SA access to read the secret at runtime
gcloud secrets add-iam-policy-binding "${SECRET_NAME}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="${PROJECT_ID}" --quiet 2>/dev/null || true

# ---------------------------------------------------------------------------
# 7. Cloud Build service account permissions (for cloudbuild.yaml)
# ---------------------------------------------------------------------------
echo -e "${GREEN}[7/8] Granting Cloud Build deploy permissions...${NC}"
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

for ROLE in roles/run.admin roles/iam.serviceAccountUser roles/artifactregistry.writer; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${CLOUDBUILD_SA}" \
        --role="${ROLE}" \
        --condition=None --quiet 2>/dev/null || true
done
echo "  Cloud Build SA configured."

# ---------------------------------------------------------------------------
# 8. Grant Cloud Run SA permission to use Cloud Build SA (for deployment)
# ---------------------------------------------------------------------------
echo -e "${GREEN}[8/8] Granting iam.serviceAccountUser to Cloud Build SA...${NC}"
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
    --member="serviceAccount:${CLOUDBUILD_SA}" \
    --role="roles/iam.serviceAccountUser" \
    --project="${PROJECT_ID}" --quiet 2>/dev/null || true
echo "  Done – Cloud Build can now deploy as Cloud Run SA."

# Also grant deploy permissions to the Compute Engine default SA, since
# Cloud Build triggers created via Developer Connect may use it.
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for ROLE in roles/run.admin roles/iam.serviceAccountUser roles/artifactregistry.writer roles/storage.objectViewer; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="${ROLE}" \
        --condition=None --quiet 2>/dev/null || true
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Setup complete!                           ${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "  Resources created:"
echo "    Artifact Registry : ${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}"
echo "    Cloud SQL         : ${SQL_INSTANCE} (PostgreSQL 16, db-f1-micro)"
echo "    Database          : ${DB_NAME}"
echo "    DB user           : ${DB_USER}"
echo "    Secret Manager    : ${SECRET_NAME}"
echo "    Cloud Run SA      : ${SA_EMAIL}"
echo "    DB password saved : ${DB_PASSWORD_FILE}"
echo ""
echo "  Cloud SQL connection name:"
echo "    ${CLOUDSQL_CONNECTION}"
echo ""
echo "  Next steps:"
echo "    1. Go to Cloud Build Triggers → create a trigger for this repo"
echo "    2. Set branch: ^main$"
echo "    3. Configuration: cloudbuild.yaml"
echo "    4. Push to main – Cloud Build will deploy automatically"
echo ""

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Uncomment and configure for team usage. For solo use, local state is fine.
  # backend "gcs" {
  #   bucket = "terraform-state-<PROJECT_ID>"
  #   prefix = "user-management-api"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# APIs
# ---------------------------------------------------------------------------

resource "google_project_service" "services" {
  for_each = toset([
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "sqladmin.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "compute.googleapis.com",
    "secretmanager.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# Artifact Registry – Docker repository for Cloud Build
# ---------------------------------------------------------------------------

resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = var.artifact_registry_repo
  format        = "DOCKER"

  depends_on = [google_project_service.services]
}

# ---------------------------------------------------------------------------
# Service Account for Cloud Run
# ---------------------------------------------------------------------------

resource "google_service_account" "cloud_run_sa" {
  account_id   = var.service_account_id
  display_name = "Cloud Run service account for User Management API"
  depends_on   = [google_project_service.services]
}

resource "google_project_iam_member" "cloud_run_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "cloud_run_artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# ---------------------------------------------------------------------------
# Cloud SQL – PostgreSQL
# ---------------------------------------------------------------------------

resource "google_sql_database_instance" "postgres" {
  name             = var.sql_instance_name
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = var.sql_tier
    edition           = "ENTERPRISE"
    disk_size         = 10
    disk_type         = "PD_SSD"
    disk_autoresize   = true
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "Cloud Run"
        value = "0.0.0.0/0"
      }
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    backup_configuration {
      enabled    = true
      start_time = "03:00"
      location   = var.region
    }
  }

  deletion_protection = false
  depends_on          = [google_project_service.services]
}

resource "random_password" "db_password" {
  length  = 24
  special = false
}

resource "google_sql_user" "app_user" {
  instance = google_sql_database_instance.postgres.name
  name     = var.db_user
  password = random_password.db_password.result
}

resource "google_sql_database" "app_db" {
  instance = google_sql_database_instance.postgres.name
  name     = var.db_name
}

# ---------------------------------------------------------------------------
# Secret Manager – DB password (so Cloud Build can inject it safely)
# ---------------------------------------------------------------------------

resource "google_secret_manager_secret" "db_password" {
  secret_id = var.db_password_secret_id
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "db_password_version" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = var.database_url_secret_id
  replication {
    auto {}
  }
  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_version" "database_url_version" {
  secret = google_secret_manager_secret.database_url.id
  secret_data = format(
    "postgresql+psycopg2://%s:%s@/%s?host=/cloudsql/%s",
    google_sql_user.app_user.name,
    random_password.db_password.result,
    google_sql_database.app_db.name,
    google_sql_database_instance.postgres.connection_name,
  )
}

# Grant Secret Manager accessor role to the default Cloud Build service account
# so cloudbuild.yaml can read secrets at build time.

data "google_project" "current" {}

resource "google_secret_manager_secret_iam_member" "cloudbuild_secret_accessor" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
}

# Grant Cloud Build permissions to deploy to Cloud Run

resource "google_project_iam_member" "cloudbuild_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
}

resource "google_project_iam_member" "cloudbuild_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
}

resource "google_project_iam_member" "cloudbuild_artifact_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"
}

# Grant Cloud Run service account access to read the DATABASE_URL secret

resource "google_secret_manager_secret_iam_member" "cloudrun_secret_accessor" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

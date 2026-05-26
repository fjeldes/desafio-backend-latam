variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "artifact_registry_repo" {
  description = "Name of the Artifact Registry Docker repository"
  type        = string
  default     = "user-management-api"
}

variable "service_account_id" {
  description = "ID for the Cloud Run service account"
  type        = string
  default     = "user-api-cloud-run"
}

variable "sql_instance_name" {
  description = "Cloud SQL instance name"
  type        = string
  default     = "user-management-db"
}

variable "sql_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "users_db"
}

variable "db_user" {
  description = "PostgreSQL database user"
  type        = string
  default     = "app_user"
}

variable "db_password_secret_id" {
  description = "Secret Manager secret ID for the DB password"
  type        = string
  default     = "db-password"
}

variable "database_url_secret_id" {
  description = "Secret Manager secret ID for the full DATABASE_URL"
  type        = string
  default     = "database-url"
}

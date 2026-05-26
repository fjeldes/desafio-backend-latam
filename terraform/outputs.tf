output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "Deployed region"
  value       = var.region
}

output "artifact_registry_url" {
  description = "Artifact Registry Docker repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}"
}

output "cloud_run_service_account_email" {
  description = "Service account email used by Cloud Run"
  value       = google_service_account.cloud_run_sa.email
}

output "sql_instance_connection_name" {
  description = "Cloud SQL instance connection name (used in Cloud Run)"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_url" {
  description = "Full DATABASE_URL for the application (sensitive)"
  value       = google_secret_manager_secret_version.database_url_version.secret_data
  sensitive   = true
}

output "database_url_secret_resource" {
  description = "Secret Manager resource ID for the DATABASE_URL secret"
  value       = "projects/${var.project_id}/secrets/${google_secret_manager_secret.database_url.secret_id}/versions/latest"
}

output "db_password_secret_resource" {
  description = "Secret Manager resource ID for the DB password secret"
  value       = "projects/${var.project_id}/secrets/${google_secret_manager_secret.db_password.secret_id}/versions/latest"
}

output "next_steps" {
  description = "Commands to run after terraform apply"
  value       = <<-EOT
    1. Retrieve the DATABASE_URL (already stored as a Secret Manager secret).
       Secret resource ID: projects/${var.project_id}/secrets/${google_secret_manager_secret.database_url.secret_id}/versions/latest

    2. Update cloudbuild.yaml if needed:
       - Update --image to point to the Artifact Registry:
         ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/user-management-api:\$SHORT_SHA
       - Reference the DATABASE_URL secret:
         --set-secrets DATABASE_URL=${google_secret_manager_secret.database_url.secret_id}:latest
       - Add Cloud SQL instance:
         --add-cloudsql-instances ${google_sql_database_instance.postgres.connection_name}
       - Use the service account:
         --service-account ${google_service_account.cloud_run_sa.email}

    3. Connect your GitHub repo to Cloud Build:
       https://console.cloud.google.com/cloud-build/triggers

    4. Push to GitHub – Cloud Build will deploy automatically.
  EOT
}

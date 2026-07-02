variable "project_id" {
  description = "The GCP project ID to deploy resources into."
  type        = string
  default     = "your-gcp-project-id"
}

variable "region" {
  description = "The primary GCP region for resources."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone for the GCE database server VM."
  type        = string
  default     = "us-central1-a"
}

variable "mssql_password" {
  description = "The password for the MS SQL Server SA account."
  type        = string
  default     = "YourStrong!Password123"
  sensitive   = true
}

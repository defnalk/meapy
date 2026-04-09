# cloudrun/main.tf — Deploy meapy to Google Cloud Run.
#
# Push the image to Artifact Registry first (the AR repository is created
# below). Apply this from inside `infra/cloudrun/`.

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.27"
    }
  }
}

variable "project_id" {
  type        = string
  description = "GCP project ID."
}

variable "region" {
  type        = string
  default     = "europe-west1"
  description = "GCP region."
}

variable "service_name" {
  type        = string
  default     = "meapy"
  description = "Cloud Run service name."
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "Image tag in Artifact Registry."
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_artifact_registry_repository" "meapy" {
  location      = var.region
  repository_id = var.service_name
  description   = "meapy container images"
  format        = "DOCKER"
}

locals {
  image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.meapy.repository_id}/${var.service_name}:${var.image_tag}"
}

resource "google_cloud_run_v2_service" "meapy" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = local.image

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.meapy.name
  location = google_cloud_run_v2_service.meapy.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "service_url" {
  value = google_cloud_run_v2_service.meapy.uri
}

output "latest_revision" {
  value = google_cloud_run_v2_service.meapy.latest_ready_revision
}

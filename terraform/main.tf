terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Create VPC Network
resource "google_compute_network" "mssql_vpc" {
  name                    = "mssql-vpc"
  auto_create_subnetworks = false
}

# Create Subnetwork
resource "google_compute_subnetwork" "mssql_subnet" {
  name                     = "mssql-subnet"
  ip_cidr_range            = "10.0.0.0/24"
  region                   = var.region
  network                  = google_compute_network.mssql_vpc.id
  private_ip_google_access = true
}

# Datastream Private Connection (VPC Peering)
resource "google_datastream_private_connection" "datastream_priv_conn" {
  display_name          = "Datastream Private Connection"
  private_connection_id = "datastream-priv-conn"
  location              = var.region

  vpc_peering_config {
    vpc    = google_compute_network.mssql_vpc.id
    subnet = "172.16.0.0/29" # Non-overlapping Class B /29 range in mssql-vpc
  }
}

# Firewall rule to allow Datastream private peered subnet to access SQL Server on port 1433
resource "google_compute_firewall" "allow_datastream_private" {
  name    = "allow-datastream-private-to-mssql"
  network = google_compute_network.mssql_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["1433"]
  }

  # Allow traffic from the Datastream peering subnet
  source_ranges = [
    "172.16.0.0/29"
  ]

  target_tags = ["mssql-server"]
}

# Allow SSH for administration/bootstrap (Internal or IAP)
resource "google_compute_firewall" "allow_ssh_iap" {
  name    = "allow-ssh-iap-to-mssql"
  network = google_compute_network.mssql_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # Allow GCE Identity-Aware Proxy (IAP) range for secure browser-based SSH without external IP
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["mssql-server"]
}

# GCE VM Running Container-Optimized OS (COS)
resource "google_compute_instance" "mssql_server" {
  name         = "mssql-db-server"
  machine_type = "e2-medium"
  zone         = var.zone

  tags = ["mssql-server"]

  boot_disk {
    initialize_params {
      image = "cos-cloud/cos-stable"
      size  = 30
      type  = "pd-standard"
    }
  }

  # Private IP only (no access_config block to prevent external IP assignment)
  network_interface {
    network    = google_compute_network.mssql_vpc.id
    subnetwork = google_compute_subnetwork.mssql_subnet.id
  }

  # Satisfies constraints/compute.requireShieldedVm
  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  metadata = {
    startup-script = <<-EOT
      #!/bin/bash
      # Pull and run MS SQL Server 2022 Docker container
      docker run -e 'ACCEPT_EULA=Y' \
                 -e 'MSSQL_SA_PASSWORD=${var.mssql_password}' \
                 -e 'MSSQL_AGENT_ENABLED=true' \
                 -p 1433:1433 \
                 --name sql1 \
                 --restart always \
                 -d mcr.microsoft.com/mssql/server:2022-latest
    EOT
  }

  service_account {
    scopes = ["cloud-platform"]
  }
}

# Create Cloud Router
resource "google_compute_router" "router" {
  name    = "mssql-router"
  region  = var.region
  network = google_compute_network.mssql_vpc.id
}

# Create Cloud NAT
resource "google_compute_router_nat" "nat" {
  name                               = "mssql-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Create landing BQ dataset (ODS)
resource "google_bigquery_dataset" "mssql_ods" {
  dataset_id  = "mssql_ods"
  description = "Landing ODS dataset for MS SQL Server replication via Datastream"
  location    = var.region
}

# Create Datastream Source Connection Profile (SQL Server)
resource "google_datastream_connection_profile" "mssql_profile" {
  display_name          = "MS SQL Source Profile"
  connection_profile_id = "mssql-source-profile"
  location              = var.region

  sql_server_profile {
    hostname = google_compute_instance.mssql_server.network_interface[0].network_ip
    port     = 1433
    username = "sa"
    password = var.mssql_password
    database = "InventoryDB"
  }

  private_connectivity {
    private_connection = google_datastream_private_connection.datastream_priv_conn.id
  }
}

# Create Datastream Target Connection Profile (BigQuery)
resource "google_datastream_connection_profile" "bigquery_profile" {
  display_name          = "BigQuery Target Profile"
  connection_profile_id = "bigquery-target-profile"
  location              = var.region

  bigquery_profile {}
}

# Create Datastream Stream
resource "google_datastream_stream" "mssql_to_bigquery" {
  stream_id                 = "mssql-to-bigquery-stream"
  display_name              = "MS SQL to BigQuery Stream"
  location                  = var.region
  desired_state             = "RUNNING"
  create_without_validation = true

  source_config {
    source_connection_profile = google_datastream_connection_profile.mssql_profile.id
    sql_server_source_config {
      include_objects {
        schemas {
          schema = "dbo"
          tables {
            table = "d_oe_user"
          }
          tables {
            table = "NVUser3"
          }
          tables {
            table = "UserSubService"
          }
          tables {
            table = "AdminLogging"
          }
          tables {
            table = "NeoDest"
          }
          tables {
            table = "adminLoggingArchive"
          }
        }
      }
    }
  }

  destination_config {
    destination_connection_profile = google_datastream_connection_profile.bigquery_profile.id
    bigquery_destination_config {
      single_target_dataset {
        dataset_id = google_bigquery_dataset.mssql_ods.id
      }
    }
  }

  backfill_all {}
}

# Create modeled EDW dataset (BigQuery)
resource "google_bigquery_dataset" "inventory_edw" {
  dataset_id  = "inventory_edw"
  description = "Modeled Enterprise Data Warehouse dataset for transformed SQL Server tables"
  location    = var.region
}

# Create Dataform Repository
resource "google_dataform_repository" "dataform_repo" {
  provider = google-beta
  name     = "mssql-dataform-pipeline"
  region   = var.region
}

# Create Service Account for Looker
resource "google_service_account" "looker_sa" {
  account_id   = "sa-looker-connector"
  display_name = "Looker BI Connector Service Account"
}

# Grant BigQuery Job User to Looker Service Account
resource "google_project_iam_member" "looker_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.looker_sa.email}"
}

# Grant BigQuery Data Viewer on EDW dataset to Looker Service Account
resource "google_bigquery_dataset_iam_member" "looker_edw_viewer" {
  dataset_id = google_bigquery_dataset.inventory_edw.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.looker_sa.email}"
}

# Grant Service Account Token Creator to Dataform Service Agent on Default Compute SA
resource "google_service_account_iam_member" "dataform_token_creator" {
  service_account_id = "projects/your-gcp-project-id/serviceAccounts/123456789012-compute@developer.gserviceaccount.com"
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-123456789012@gcp-sa-dataform.iam.gserviceaccount.com"
}

# Grant BigQuery Admin to default compute service account for Dataform execution
resource "google_project_iam_member" "compute_sa_bq_admin" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:123456789012-compute@developer.gserviceaccount.com"
}





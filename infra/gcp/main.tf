terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0"
    }
  }
}

provider "google" {
  project     = var.project_id
  region      = var.region
  zone        = var.zone
  credentials = var.credentials_json
}

resource "google_compute_network" "brain" {
  name                    = "brain-cloud-vpc"
  auto_create_subnetworks = true
}

resource "google_compute_firewall" "brain_internal" {
  name    = "brain-cloud-internal"
  network = google_compute_network.brain.name

  allow {
    protocol = "tcp"
    ports    = ["3000", "2222"]
  }

  source_tags = ["brain-cloud"]
  target_tags = ["brain-cloud"]
}

resource "google_compute_instance" "brain" {
  name         = "brain-cloud-host"
  machine_type = "e2-micro"
  zone         = var.zone
  tags         = ["brain-cloud"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 30
      type  = "pd-standard"
    }
  }

  network_interface {
    network = google_compute_network.brain.name
    access_config {}
  }

  metadata_startup_script = file("${path.module}/startup.sh")

  labels = {
    project = "electronic-brain"
    role    = "control-plane"
  }
}

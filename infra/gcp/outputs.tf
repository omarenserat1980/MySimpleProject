output "brain_host_name" {
  value = google_compute_instance.brain.name
}

output "brain_host_zone" {
  value = google_compute_instance.brain.zone
}

output "brain_host_public_ip" {
  value = google_compute_instance.brain.network_interface[0].access_config[0].nat_ip
}

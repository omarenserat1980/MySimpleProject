variable "project_id" {
  type = string
}

variable "credentials_json" {
  type      = string
  sensitive = true
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}

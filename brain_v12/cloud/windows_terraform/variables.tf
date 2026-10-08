variable "resource_group_location" {
  type        = string
  description = "Azure region for the Brain Windows node."
  default     = "westeurope"
}

variable "vm_name" {
  type    = string
  default = "brain-windows-2025"
}

variable "resource_group_name" {
  type    = string
  default = "brain-windows-rg"
}

variable "admin_username" {
  type      = string
  sensitive = true
  default   = "brainadmin"
}

variable "admin_password" {
  type      = string
  sensitive = true
  default   = null
}

variable "vm_size" {
  type    = string
  default = "Standard_D4s_v5"
}

variable "allowed_source_ip" {
  type        = string
  description = "CIDR allowed to reach management port. Do not use 0.0.0.0/0."
}

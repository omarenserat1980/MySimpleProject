output "brain_vm_id" {
  value = azurerm_windows_virtual_machine.brain.id
}

output "brain_provider" {
  value = "azure"
}

output "brain_region" {
  value = azurerm_resource_group.brain.location
}

output "brain_state" {
  value = "PROVISIONED"
}

output "brain_os" {
  value = "Windows Server 2025"
}

output "brain_architecture" {
  value = "x86_64"
}

output "brain_public_ip" {
  value = azurerm_public_ip.brain.ip_address
}

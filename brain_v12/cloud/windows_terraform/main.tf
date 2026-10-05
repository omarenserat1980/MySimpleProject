resource "azurerm_resource_group" "brain" {
  name     = var.resource_group_name
  location = var.resource_group_location
}

resource "azurerm_virtual_network" "brain" {
  name                = "${var.vm_name}-vnet"
  address_space       = ["10.42.0.0/16"]
  location            = azurerm_resource_group.brain.location
  resource_group_name = azurerm_resource_group.brain.name
}

resource "azurerm_subnet" "brain" {
  name                 = "${var.vm_name}-subnet"
  resource_group_name  = azurerm_resource_group.brain.name
  virtual_network_name = azurerm_virtual_network.brain.name
  address_prefixes     = ["10.42.1.0/24"]
}

resource "azurerm_public_ip" "brain" {
  name                = "${var.vm_name}-pip"
  location            = azurerm_resource_group.brain.location
  resource_group_name = azurerm_resource_group.brain.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_security_group" "brain" {
  name                = "${var.vm_name}-nsg"
  location            = azurerm_resource_group.brain.location
  resource_group_name = azurerm_resource_group.brain.name

  security_rule {
    name                   = "AllowWinRM"
    priority               = 100
    direction              = "Inbound"
    access                = "Allow"
    protocol               = "Tcp"
    source_port_range      = "*"
    destination_port_range = "5986"
    source_address_prefix  = var.allowed_source_ip
  }
}

resource "azurerm_network_interface" "brain" {
  name                = "${var.vm_name}-nic"
  location            = azurerm_resource_group.brain.location
  resource_group_name = azurerm_resource_group.brain.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.brain.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.brain.id
  }
}

resource "azurerm_network_interface_security_group_association" "brain" {
  network_interface_id      = azurerm_network_interface.brain.id
  network_security_group_id = azurerm_network_security_group.brain.id
}

resource "azurerm_windows_virtual_machine" "brain" {
  name                  = var.vm_name
  computer_name         = "BRAINWIN2025"
  resource_group_name   = azurerm_resource_group.brain.name
  location              = azurerm_resource_group.brain.location
  size                  = var.vm_size
  admin_username        = var.admin_username
  admin_password        = var.admin_password
  network_interface_ids = [azurerm_network_interface.brain.id]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
  }

  source_image_reference {
    publisher = "MicrosoftWindowsServer"
    offer     = "WindowsServer"
    sku       = "2025-datacenter-azure-edition"
    version   = "latest"
  }
}

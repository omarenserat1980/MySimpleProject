terraform {
  required_version = ">= 1.6.0"
  required_providers {
    oci = { source = "oracle/oci", version = ">= 7.0.0" }
  }
}
provider "oci" {
  tenancy_ocid = var.tenancy_ocid
  user_ocid = var.user_ocid
  fingerprint = var.fingerprint
  private_key = var.private_key
  region = var.region
}
data "oci_identity_availability_domains" "ads" { compartment_id = var.compartment_ocid }
data "oci_core_images" "ubuntu" {
  compartment_id = var.compartment_ocid
  operating_system = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape = "VM.Standard.A1.Flex"
  sort_by = "TIMECREATED"
  sort_order = "DESC"
}
resource "oci_core_vcn" "brain" {
  compartment_id = var.compartment_ocid
  display_name = "brain-cloud-vcn"
  cidr_blocks = ["10.20.0.0/16"]
  dns_label = "braincloud"
}
resource "oci_core_internet_gateway" "brain" {
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.brain.id
  display_name = "brain-cloud-igw"
  enabled = true
}
resource "oci_core_route_table" "brain" {
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.brain.id
  display_name = "brain-cloud-route"
  route_rules {
    destination = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.brain.id
  }
}
resource "oci_core_security_list" "brain" {
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.brain.id
  display_name = "brain-cloud-security"
  egress_security_rules { destination = "0.0.0.0/0" protocol = "all" }
  ingress_security_rules {
    protocol = "6"
    source = "0.0.0.0/0"
    tcp_options { min = 22 max = 22 }
  }
}
resource "oci_core_subnet" "brain" {
  compartment_id = var.compartment_ocid
  vcn_id = oci_core_vcn.brain.id
  cidr_block = "10.20.10.0/24"
  display_name = "brain-cloud-public-subnet"
  route_table_id = oci_core_route_table.brain.id
  security_list_ids = [oci_core_security_list.brain.id]
  prohibit_public_ip_on_vnic = false
}
resource "oci_core_instance" "brain" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id = var.compartment_ocid
  display_name = "brain-cloud-host"
  shape = "VM.Standard.A1.Flex"
  shape_config { ocpus = 2 memory_in_gbs = 12 }
  create_vnic_details {
    subnet_id = oci_core_subnet.brain.id
    assign_public_ip = true
    hostname_label = "braincloud"
  }
  source_details {
    source_type = "image"
    source_id = data.oci_core_images.ubuntu.images[0].id
  }
  metadata {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(file("cloud-init.sh"))
  }
  freeform_tags = { project = "ElectronicBrain", role = "brain-cloud-host" }
}

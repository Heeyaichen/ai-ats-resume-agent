variable "project_name" { type = string }
variable "environment" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

variable "vnet_address_space" {
  type    = string
  default = "10.0.0.0/16"
}
variable "container_apps_subnet_cidr" {
  type    = string
  default = "10.0.0.0/20"
}
variable "function_app_subnet_cidr" {
  type    = string
  default = "10.0.16.0/24"
}
variable "private_endpoints_subnet_cidr" {
  type    = string
  default = "10.0.17.0/24"
}

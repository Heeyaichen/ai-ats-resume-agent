variable "project_name" { type = string }
variable "environment" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

variable "servicebus_namespace_id" { type = string }
variable "container_app_environment_id" { type = string }

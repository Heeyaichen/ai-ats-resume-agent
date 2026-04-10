variable "project_name" { type = string }
variable "environment" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

variable "cosmos_throughput" {
  type    = number
  default = 400
}
variable "redis_sku" {
  type    = string
  default = "Basic"
}
variable "redis_capacity" {
  type    = number
  default = 0
}
variable "redis_family" {
  type    = string
  default = "C"
}
variable "search_sku" {
  type    = string
  default = "basic"
}
variable "search_replicas" {
  type    = number
  default = 1
}

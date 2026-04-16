variable "project_name" { type = string }
variable "environment" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

# ── External references ────────────────────────────────────────
variable "openai_endpoint" { type = string }
variable "openai_key" {
  type      = string
  sensitive = true
}
variable "cosmos_endpoint" { type = string }
variable "cosmos_key" {
  type      = string
  sensitive = true
}
variable "servicebus_connection_string" {
  type      = string
  sensitive = true
}
variable "storage_connection_string" {
  type      = string
  sensitive = true
}
variable "storage_account_name" { type = string }
variable "storage_access_key" {
  type      = string
  sensitive = true
}
variable "redis_host_name" { type = string }
variable "redis_primary_key" {
  type      = string
  sensitive = true
}
variable "search_endpoint" { type = string }
variable "search_primary_key" {
  type      = string
  sensitive = true
}
variable "application_insights_connection_string" {
  type      = string
  sensitive = true
}

# ── SKU / sizing ───────────────────────────────────────────────
variable "acr_sku" {
  type    = string
  default = "Basic"
}
variable "api_cpu" {
  type    = string
  default = "0.5"
}
variable "api_memory" {
  type    = string
  default = "1.0Gi"
}
variable "worker_cpu" {
  type    = string
  default = "0.5"
}
variable "worker_memory" {
  type    = string
  default = "1.0Gi"
}
variable "function_sku" {
  type    = string
  default = "Y1"
}
variable "static_web_app_sku" {
  type    = string
  default = "Free"
}
variable "cdn_sku" {
  type    = string
  default = "Standard_Microsoft"
}
variable "apim_sku" {
  type    = string
  default = "Developer_1"
}
variable "apim_publisher_email" {
  type    = string
  default = "admin@example.com"
}

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
variable "bootstrap_image" {
  type        = string
  description = "Placeholder image for initial Container App creation (replaced by CI/CD)."
  default     = "mcr.microsoft.com/azure-functions/base:4-python3.11"
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
variable "static_web_app_location" {
  type        = string
  description = "Location for Static Web App (must be a supported region)."
  default     = "westeurope"
}
variable "frontdoor_sku" {
  type    = string
  default = "Standard_AzureFrontDoor"
}
variable "enable_frontdoor" {
  type        = bool
  description = "Enable Azure Front Door edge delivery. Disable on subscriptions that do not support Front Door."
  default     = false
}
variable "apim_sku" {
  type    = string
  default = "Developer_1"
}
variable "apim_publisher_email" {
  type    = string
  default = "admin@example.com"
}

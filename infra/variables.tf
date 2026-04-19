variable "project_name" {
  description = "Project name used in resource naming."
  type        = string
  default     = "ats-agent"
}

variable "environment" {
  description = "Deployment environment (dev or prod)."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "swedencentral"
}

variable "tags" {
  description = "Common tags applied to all resources."
  type        = map(string)
  default = {
    project     = "ats-agent"
    managed_by  = "terraform"
    cost_center = "engineering"
  }
}

# ── Storage ────────────────────────────────────────────────────

variable "storage_replication_type" {
  description = "Storage account replication type."
  type        = string
  default     = "LRS"
}

# ── AI Services ────────────────────────────────────────────────

variable "openai_sku" {
  type    = string
  default = "S0"
}

variable "openai_capacity" {
  type    = number
  default = 30
}

variable "openai_chat_model_name" {
  type        = string
  description = "Azure OpenAI chat model name. Must be available in your region."
  default     = "gpt-4o"
}

variable "openai_chat_model_version" {
  type        = string
  description = "Azure OpenAI chat model version. Must be currently supported."
  default     = "2025-01-01-preview"
}

variable "openai_embedding_model_name" {
  type    = string
  default = "text-embedding-ada-002"
}

variable "openai_embedding_model_version" {
  type    = string
  default = "2"
}

variable "doc_intelligence_sku" {
  type    = string
  default = "S0"
}

variable "translator_sku" {
  type    = string
  default = "S1"
}

variable "language_sku" {
  type    = string
  default = "S"
}

variable "content_safety_sku" {
  type    = string
  default = "S0"
}

# ── Compute ────────────────────────────────────────────────────

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

variable "static_web_app_location" {
  type        = string
  description = "Location for Static Web App (must be a supported region). swedencentral is not supported."
  default     = "westeurope"
}

variable "frontdoor_sku" {
  description = "Azure Front Door SKU (only used when enable_frontdoor=true)."
  type        = string
  default     = "Standard_AzureFrontDoor"
}

variable "enable_frontdoor" {
  description = "Enable Azure Front Door. Disable on subscriptions that restrict Front Door."
  type        = bool
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

# ── Data ───────────────────────────────────────────────────────

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

# ── Networking ─────────────────────────────────────────────────

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

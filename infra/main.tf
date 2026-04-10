/**
 * Root module — wires all infrastructure modules.
 * Design spec Section 8.1: resource group + module calls.
 */

resource "azurerm_resource_group" "this" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location
  tags     = var.tags
}

# ── Storage ────────────────────────────────────────────────────

module "storage" {
  source              = "./modules/storage"
  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  replication_type    = var.storage_replication_type
  tags                = var.tags
}

# ── AI Services ────────────────────────────────────────────────

module "ai_services" {
  source              = "./modules/ai_services"
  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = var.tags

  openai_sku           = var.openai_sku
  openai_capacity      = var.openai_capacity
  doc_intelligence_sku = var.doc_intelligence_sku
  translator_sku       = var.translator_sku
  language_sku         = var.language_sku
  content_safety_sku   = var.content_safety_sku
}

# ── Data ───────────────────────────────────────────────────────

module "data" {
  source              = "./modules/data"
  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = var.tags

  cosmos_throughput = var.cosmos_throughput
  redis_sku         = var.redis_sku
  redis_capacity    = var.redis_capacity
  redis_family      = var.redis_family
  search_sku        = var.search_sku
  search_replicas   = var.search_replicas
}

# ── Networking ─────────────────────────────────────────────────

module "networking" {
  source              = "./modules/networking"
  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = var.tags
}

# ── Compute ────────────────────────────────────────────────────

module "compute" {
  source              = "./modules/compute"
  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = var.tags

  # External service references.
  openai_endpoint              = module.ai_services.openai_endpoint
  openai_key                   = module.ai_services.openai_key
  cosmos_endpoint              = module.data.cosmos_endpoint
  cosmos_key                   = module.data.cosmos_key
  servicebus_connection_string = module.data.servicebus_connection_string
  storage_connection_string    = module.storage.storage_account_primary_connection_string
  storage_account_name         = module.storage.storage_account_name
  storage_access_key           = module.storage.storage_account_primary_access_key

  # SKU overrides.
  acr_sku              = var.acr_sku
  api_cpu              = var.api_cpu
  api_memory           = var.api_memory
  worker_cpu           = var.worker_cpu
  worker_memory        = var.worker_memory
  function_sku         = var.function_sku
  static_web_app_sku   = var.static_web_app_sku
  cdn_sku              = var.cdn_sku
  apim_sku             = var.apim_sku
  apim_publisher_email = var.apim_publisher_email
}

# ── Observability ──────────────────────────────────────────────

module "observability" {
  source              = "./modules/observability"
  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = var.tags

  servicebus_namespace_id      = module.data.servicebus_namespace_id
  container_app_environment_id = module.compute.container_app_environment_id
}

# ── Security ───────────────────────────────────────────────────

module "security" {
  source              = "./modules/security"
  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  tags                = var.tags

  # Identity principal IDs.
  api_identity_principal_id      = module.compute.api_identity_principal_id
  function_identity_principal_id = module.compute.function_app_identity_principal_id

  # Resource IDs for RBAC scopes.
  storage_account_id          = module.storage.storage_account_id
  cosmos_account_id           = module.data.cosmos_account_id
  servicebus_namespace_id     = module.data.servicebus_namespace_id
  openai_account_id           = module.ai_services.openai_id
  doc_intelligence_account_id = module.ai_services.doc_intelligence_id
  translator_account_id       = module.ai_services.translator_id
  language_account_id         = module.ai_services.language_id
  content_safety_account_id   = module.ai_services.content_safety_id
  search_service_id           = module.data.search_service_id
}

data "azurerm_client_config" "current" {}

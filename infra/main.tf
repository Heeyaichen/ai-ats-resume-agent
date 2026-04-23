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

  openai_sku                     = var.openai_sku
  openai_capacity                = var.openai_capacity
  openai_chat_model_name         = var.openai_chat_model_name
  openai_chat_model_version      = var.openai_chat_model_version
  openai_embedding_model_name    = var.openai_embedding_model_name
  openai_embedding_model_version = var.openai_embedding_model_version
  doc_intelligence_sku           = var.doc_intelligence_sku
  translator_sku                 = var.translator_sku
  language_sku                   = var.language_sku
  content_safety_sku             = var.content_safety_sku

  # Share existing OpenAI account when subscription quota is exhausted.
  use_existing_openai            = var.use_existing_openai
  existing_openai_name           = var.existing_openai_name
  existing_openai_resource_group = var.existing_openai_resource_group
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
  openai_endpoint                        = module.ai_services.openai_endpoint
  openai_key                             = module.ai_services.openai_key
  cosmos_endpoint                        = module.data.cosmos_endpoint
  cosmos_key                             = module.data.cosmos_key
  servicebus_connection_string           = module.data.servicebus_connection_string
  storage_connection_string              = module.storage.storage_account_primary_connection_string
  storage_account_name                   = module.storage.storage_account_name
  storage_access_key                     = module.storage.storage_account_primary_access_key
  redis_host_name                        = module.data.redis_host_name
  redis_primary_key                      = module.data.redis_primary_key
  search_endpoint                        = module.data.search_endpoint
  search_primary_key                     = module.data.search_primary_key
  application_insights_connection_string = module.observability.application_insights_connection_string

  # SKU overrides.
  acr_sku                 = var.acr_sku
  api_cpu                 = var.api_cpu
  api_memory              = var.api_memory
  worker_cpu              = var.worker_cpu
  worker_memory           = var.worker_memory
  function_sku            = var.function_sku
  static_web_app_sku      = var.static_web_app_sku
  static_web_app_location = var.static_web_app_location
  frontdoor_sku           = var.frontdoor_sku
  enable_frontdoor        = var.enable_frontdoor
  enable_apim             = var.enable_apim
  apim_sku                = var.apim_sku
  apim_publisher_email    = var.apim_publisher_email

  # Share existing Container Apps Environment when subscription quota is exhausted.
  existing_cae_id = var.existing_cae_id

  # CORS origins for the API.
  cors_origins = var.cors_origins
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
  worker_identity_principal_id   = module.compute.worker_identity_principal_id
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
  acr_id                      = module.compute.acr_id
}

data "azurerm_client_config" "current" {}

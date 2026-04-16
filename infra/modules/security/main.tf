/**
 * Security module — Key Vault and RBAC assignments.
 * Design spec Sections 8.4, 9.2.
 */

# ── Key Vault ──────────────────────────────────────────────────

resource "azurerm_key_vault" "this" {
  name                       = "${var.project_name}-${var.environment}-kv"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 7
  tags                       = var.tags
}

# ── RBAC: Container App managed identity ───────────────────────
# Section 8.4: required role assignments.

resource "azurerm_role_assignment" "api_blob_contributor" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.api_identity_principal_id
}

resource "azurerm_role_assignment" "api_cosmos_contributor" {
  scope                = var.cosmos_account_id
  role_definition_name = "Cosmos DB Built-in Data Contributor"
  principal_id         = var.api_identity_principal_id
}

resource "azurerm_role_assignment" "api_sb_receiver" {
  scope                = var.servicebus_namespace_id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = var.api_identity_principal_id
}

resource "azurerm_role_assignment" "api_openai_user" {
  scope                = var.openai_account_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.api_identity_principal_id
}

resource "azurerm_role_assignment" "api_search_contributor" {
  scope                = var.search_service_id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = var.api_identity_principal_id
}

resource "azurerm_role_assignment" "api_keyvault_secrets_user" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.api_identity_principal_id
}

# ── RBAC: Function App managed identity ────────────────────────

resource "azurerm_role_assignment" "func_blob_reader" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = var.function_identity_principal_id
}

resource "azurerm_role_assignment" "func_sb_sender" {
  scope                = var.servicebus_namespace_id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = var.function_identity_principal_id
}

resource "azurerm_role_assignment" "func_cosmos_reader" {
  scope                = var.cosmos_account_id
  role_definition_name = "Cosmos DB Built-in Data Reader"
  principal_id         = var.function_identity_principal_id
}

resource "azurerm_role_assignment" "func_keyvault_secrets_user" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.function_identity_principal_id
}

# ── RBAC: Cognitive Services User on non-OpenAI AI services ────

resource "azurerm_role_assignment" "api_doc_intelligence_user" {
  scope                = var.doc_intelligence_account_id
  role_definition_name = "Cognitive Services User"
  principal_id         = var.api_identity_principal_id
}

resource "azurerm_role_assignment" "api_translator_user" {
  scope                = var.translator_account_id
  role_definition_name = "Cognitive Services User"
  principal_id         = var.api_identity_principal_id
}

resource "azurerm_role_assignment" "api_language_user" {
  scope                = var.language_account_id
  role_definition_name = "Cognitive Services User"
  principal_id         = var.api_identity_principal_id
}

resource "azurerm_role_assignment" "api_content_safety_user" {
  scope                = var.content_safety_account_id
  role_definition_name = "Cognitive Services User"
  principal_id         = var.api_identity_principal_id
}

# ── RBAC: Worker managed identity ──────────────────────────────
# Worker runs the agent and needs the same service access as the API.

resource "azurerm_role_assignment" "worker_blob_contributor" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.worker_identity_principal_id
}

resource "azurerm_role_assignment" "worker_cosmos_contributor" {
  scope                = var.cosmos_account_id
  role_definition_name = "Cosmos DB Built-in Data Contributor"
  principal_id         = var.worker_identity_principal_id
}

resource "azurerm_role_assignment" "worker_sb_receiver" {
  scope                = var.servicebus_namespace_id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = var.worker_identity_principal_id
}

resource "azurerm_role_assignment" "worker_openai_user" {
  scope                = var.openai_account_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = var.worker_identity_principal_id
}

resource "azurerm_role_assignment" "worker_search_contributor" {
  scope                = var.search_service_id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = var.worker_identity_principal_id
}

resource "azurerm_role_assignment" "worker_keyvault_secrets_user" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.worker_identity_principal_id
}

resource "azurerm_role_assignment" "worker_doc_intelligence_user" {
  scope                = var.doc_intelligence_account_id
  role_definition_name = "Cognitive Services User"
  principal_id         = var.worker_identity_principal_id
}

resource "azurerm_role_assignment" "worker_translator_user" {
  scope                = var.translator_account_id
  role_definition_name = "Cognitive Services User"
  principal_id         = var.worker_identity_principal_id
}

resource "azurerm_role_assignment" "worker_language_user" {
  scope                = var.language_account_id
  role_definition_name = "Cognitive Services User"
  principal_id         = var.worker_identity_principal_id
}

resource "azurerm_role_assignment" "worker_content_safety_user" {
  scope                = var.content_safety_account_id
  role_definition_name = "Cognitive Services User"
  principal_id         = var.worker_identity_principal_id
}

/**
 * AI Services module — Azure OpenAI, Document Intelligence, Translator,
 * AI Language, and Content Safety.
 * Design spec Sections 3.3 and 4.3.
 */

# ── Azure OpenAI ───────────────────────────────────────────────

data "azurerm_cognitive_account" "existing_openai" {
  count               = var.use_existing_openai ? 1 : 0
  name                = var.existing_openai_name
  resource_group_name = var.existing_openai_resource_group
}

resource "azurerm_cognitive_account" "openai" {
  count                         = var.use_existing_openai ? 0 : 1
  name                          = "${var.project_name}-${var.environment}-openai"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  kind                          = "OpenAI"
  sku_name                      = var.openai_sku
  custom_subdomain_name         = "${var.project_name}-${var.environment}-openai"
  public_network_access_enabled = true
  tags                          = var.tags
}

locals {
  openai_account = var.use_existing_openai ? data.azurerm_cognitive_account.existing_openai[0] : azurerm_cognitive_account.openai[0]
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  count                = var.use_existing_openai ? 0 : 1
  name                 = var.openai_chat_model_name
  cognitive_account_id = local.openai_account.id
  model {
    format  = "OpenAI"
    name    = var.openai_chat_model_name
    version = var.openai_chat_model_version
  }
  sku {
    name     = "Standard"
    capacity = var.openai_capacity
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  count                = var.use_existing_openai ? 0 : 1
  name                 = var.openai_embedding_model_name
  cognitive_account_id = local.openai_account.id
  model {
    format  = "OpenAI"
    name    = var.openai_embedding_model_name
    version = var.openai_embedding_model_version
  }
  sku {
    name     = "Standard"
    capacity = var.openai_capacity
  }
}

# ── Document Intelligence ──────────────────────────────────────

resource "azurerm_cognitive_account" "doc_intelligence" {
  name                = "${var.project_name}-${var.environment}-docint"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "FormRecognizer"
  sku_name            = var.doc_intelligence_sku
  tags                = var.tags
}

# ── Translator ─────────────────────────────────────────────────

resource "azurerm_cognitive_account" "translator" {
  name                = "${var.project_name}-${var.environment}-translator"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "TextTranslation"
  sku_name            = var.translator_sku
  tags                = var.tags
}

# ── AI Language (PII detection/redaction) ──────────────────────

resource "azurerm_cognitive_account" "language" {
  name                = "${var.project_name}-${var.environment}-language"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "TextAnalytics"
  sku_name            = var.language_sku
  tags                = var.tags
}

# ── Content Safety (harmful-content moderation) ────────────────

resource "azurerm_cognitive_account" "content_safety" {
  name                = "${var.project_name}-${var.environment}-contentsafety"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "ContentSafety"
  sku_name            = var.content_safety_sku
  tags                = var.tags
}

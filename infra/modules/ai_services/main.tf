/**
 * AI Services module — Azure OpenAI, Document Intelligence, Translator,
 * AI Language, and Content Safety.
 * Design spec Sections 3.3 and 4.3.
 */

# ── Azure OpenAI ───────────────────────────────────────────────

resource "azurerm_cognitive_account" "openai" {
  name                          = "${var.project_name}-${var.environment}-openai"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  kind                          = "OpenAI"
  sku_name                      = var.openai_sku
  custom_subdomain_name         = "${var.project_name}-${var.environment}-openai"
  public_network_access_enabled = true
  tags                          = var.tags
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-08-06"
  }
  sku {
    name     = "Standard"
    capacity = var.openai_capacity
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = "text-embedding-ada-002"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "text-embedding-ada-002"
    version = "2"
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

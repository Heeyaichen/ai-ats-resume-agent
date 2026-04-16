/**
 * Compute module — Container Registry, Container Apps Environment,
 * FastAPI Container App, worker, Function App, Static Web App, CDN, APIM.
 * Design spec Sections 3.3, 8.1, 8.4.
 */

# ── Managed Identities ─────────────────────────────────────────

resource "azurerm_user_assigned_identity" "api" {
  name                = "${var.project_name}-${var.environment}-api-id"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_user_assigned_identity" "worker" {
  name                = "${var.project_name}-${var.environment}-worker-id"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

# ── Container Registry ─────────────────────────────────────────

resource "azurerm_container_registry" "this" {
  name                = "${replace(var.project_name, "-", "")}${var.environment}acr"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.acr_sku
  admin_enabled       = false
  tags                = var.tags
}

# ── Container Apps Environment ─────────────────────────────────

resource "azurerm_container_app_environment" "this" {
  name                = "${var.project_name}-${var.environment}-cae"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

# ── FastAPI Container App ──────────────────────────────────────

resource "azurerm_container_app" "api" {
  name                         = "${var.project_name}-${var.environment}-api"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  tags                         = var.tags

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.api.id
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api.id]
  }

  template {
    container {
      name   = "api"
      image  = "${azurerm_container_registry.this.login_server}/ats-agent-api:latest"
      cpu    = tonumber(var.api_cpu)
      memory = var.api_memory

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.openai_endpoint
      }
      env {
        name        = "AZURE_OPENAI_KEY"
        secret_name = "azure-openai-key"
      }
      env {
        name  = "CHAT_MODEL_DEPLOYMENT_NAME"
        value = "gpt-4o"
      }
      env {
        name  = "EMBEDDING_MODEL_DEPLOYMENT_NAME"
        value = "text-embedding-ada-002"
      }
      env {
        name        = "SERVICEBUS_CONNECTION_STRING"
        secret_name = "servicebus-connection-string"
      }
      env {
        name  = "COSMOS_ENDPOINT"
        value = var.cosmos_endpoint
      }
      env {
        name        = "COSMOS_KEY"
        secret_name = "cosmos-key"
      }
      env {
        name        = "STORAGE_CONNECTION_STRING"
        secret_name = "storage-connection-string"
      }
      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "app-insights-conn-str"
      }
    }
  }

  ingress {
    target_port = 8000
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
    external_enabled = true
  }

  secret {
    name  = "azure-openai-key"
    value = var.openai_key
  }
  secret {
    name  = "servicebus-connection-string"
    value = var.servicebus_connection_string
  }
  secret {
    name  = "cosmos-key"
    value = var.cosmos_key
  }
  secret {
    name  = "storage-connection-string"
    value = var.storage_connection_string
  }
  secret {
    name  = "app-insights-conn-str"
    value = var.application_insights_connection_string
  }
}

# ── Worker Container App ───────────────────────────────────────

resource "azurerm_container_app" "worker" {
  name                         = "${var.project_name}-${var.environment}-worker"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  tags                         = var.tags

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.worker.id
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.worker.id]
  }

  template {
    container {
      name   = "worker"
      image  = "${azurerm_container_registry.this.login_server}/ats-agent-worker:latest"
      cpu    = tonumber(var.worker_cpu)
      memory = var.worker_memory

      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.openai_endpoint
      }
      env {
        name        = "AZURE_OPENAI_KEY"
        secret_name = "azure-openai-key"
      }
      env {
        name  = "CHAT_MODEL_DEPLOYMENT_NAME"
        value = "gpt-4o"
      }
      env {
        name  = "EMBEDDING_MODEL_DEPLOYMENT_NAME"
        value = "text-embedding-ada-002"
      }
      env {
        name        = "SERVICEBUS_CONNECTION_STRING"
        secret_name = "servicebus-connection-string"
      }
      env {
        name  = "COSMOS_ENDPOINT"
        value = var.cosmos_endpoint
      }
      env {
        name        = "COSMOS_KEY"
        secret_name = "cosmos-key"
      }
      env {
        name        = "STORAGE_CONNECTION_STRING"
        secret_name = "storage-connection-string"
      }
      env {
        name        = "REDIS_URL"
        secret_name = "redis-url"
      }
      env {
        name  = "SEARCH_ENDPOINT"
        value = var.search_endpoint
      }
      env {
        name        = "SEARCH_KEY"
        secret_name = "search-key"
      }
      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "app-insights-conn-str"
      }
    }
  }

  secret {
    name  = "azure-openai-key"
    value = var.openai_key
  }
  secret {
    name  = "servicebus-connection-string"
    value = var.servicebus_connection_string
  }
  secret {
    name  = "cosmos-key"
    value = var.cosmos_key
  }
  secret {
    name  = "storage-connection-string"
    value = var.storage_connection_string
  }
  secret {
    name  = "redis-url"
    value = "rediss://:${var.redis_primary_key}@${var.redis_host_name}:6380"
  }
  secret {
    name  = "search-key"
    value = var.search_primary_key
  }
  secret {
    name  = "app-insights-conn-str"
    value = var.application_insights_connection_string
  }
}

# ── Function App (blob trigger) ────────────────────────────────

resource "azurerm_service_plan" "function" {
  name                = "${var.project_name}-${var.environment}-func-asp"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.function_sku
  tags                = var.tags
}

resource "azurerm_linux_function_app" "this" {
  name                       = "${var.project_name}-${var.environment}-func"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  service_plan_id            = azurerm_service_plan.function.id
  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_access_key
  tags                       = var.tags

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    "AzureWebJobsStorage"                   = var.storage_connection_string
    "SERVICEBUS_QUEUE_NAME"                 = "ats-agent-jobs"
    "ServiceBusConnection"                  = var.servicebus_connection_string
    "AZURE_OPENAI_ENDPOINT"                 = var.openai_endpoint
    "COSMOS_ENDPOINT"                       = var.cosmos_endpoint
    "COSMOS_KEY"                            = var.cosmos_key
    "FUNCTIONS_WORKER_RUNTIME"              = "python"
    "WEBSITE_RUN_FROM_PACKAGE"              = "1"
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.application_insights_connection_string
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }
}

# ── Static Web App ─────────────────────────────────────────────

resource "azurerm_static_web_app" "this" {
  name                = "${var.project_name}-${var.environment}-swa"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku_tier            = var.static_web_app_sku
  tags                = var.tags
}

# ── Front Door (edge delivery for Static Web App) ─────────────

resource "azurerm_cdn_frontdoor_profile" "this" {
  name                = "${var.project_name}-${var.environment}-fd"
  resource_group_name = var.resource_group_name
  sku_name            = var.frontdoor_sku
  tags                = var.tags
}

resource "azurerm_cdn_frontdoor_origin_group" "this" {
  name                     = "${var.project_name}-${var.environment}-og"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.this.id

  load_balancing {
    sample_size                 = 4
    successful_samples_required = 3
  }

  health_probe {
    protocol            = "Https"
    interval_in_seconds = 100
  }
}

resource "azurerm_cdn_frontdoor_origin" "swa" {
  name                          = "staticwebapp"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.this.id
  enabled                       = true

  host_name                    = azurerm_static_web_app.this.default_host_name
  http_port                    = 80
  https_port                   = 443
  origin_host_header           = azurerm_static_web_app.this.default_host_name
  priority                     = 1
  weight                       = 1000
  certificate_name_check_enabled = false
}

resource "azurerm_cdn_frontdoor_endpoint" "this" {
  name                     = "${replace(var.project_name, "-", "")}${var.environment}fd"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.this.id
  tags                     = var.tags
}

resource "azurerm_cdn_frontdoor_route" "this" {
  name                          = "swa-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.this.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.this.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.swa.id]
  supported_protocols           = ["Https"]
  patterns_to_match             = ["/*"]
  forwarding_protocol           = "HttpsOnly"
  link_to_default_domain        = true
  https_redirect_enabled        = true
}

# ── API Management ─────────────────────────────────────────────

resource "azurerm_api_management" "this" {
  name                = "${var.project_name}-${var.environment}-apim"
  resource_group_name = var.resource_group_name
  location            = var.location
  publisher_name      = "ATS Agent"
  publisher_email     = var.apim_publisher_email
  sku_name            = var.apim_sku
  tags                = var.tags
}

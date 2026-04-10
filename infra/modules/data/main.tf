/**
 * Data module — Cosmos DB, Service Bus, Redis, and AI Search.
 * Design spec Sections 7.1, 7.3, 7.4, 7.5.
 */

# ── Cosmos DB ──────────────────────────────────────────────────

resource "azurerm_cosmosdb_account" "this" {
  name                = "${var.project_name}-${var.environment}-cosmos"
  resource_group_name = var.resource_group_name
  location            = var.location
  offer_type          = "Standard"
  tags                = var.tags

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }
}

resource "azurerm_cosmosdb_sql_database" "ats" {
  name                = "ats-db"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  throughput          = var.cosmos_throughput
}

resource "azurerm_cosmosdb_sql_container" "jobs" {
  name                = "jobs"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.ats.name
  partition_key_paths = ["/id"]
  default_ttl         = 7776000 # 90 days
}

resource "azurerm_cosmosdb_sql_container" "candidates" {
  name                = "candidates"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.ats.name
  partition_key_paths = ["/id"]
  default_ttl         = 7776000
}

resource "azurerm_cosmosdb_sql_container" "scores" {
  name                = "scores"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.ats.name
  partition_key_paths = ["/job_id"]
  default_ttl         = 7776000
}

resource "azurerm_cosmosdb_sql_container" "agent_traces" {
  name                = "agent_traces"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.ats.name
  partition_key_paths = ["/job_id"]
  default_ttl         = 7776000
}

resource "azurerm_cosmosdb_sql_container" "review_flags" {
  name                = "review_flags"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.this.name
  database_name       = azurerm_cosmosdb_sql_database.ats.name
  partition_key_paths = ["/job_id"]
  default_ttl         = 7776000
}

# ── Service Bus ────────────────────────────────────────────────

resource "azurerm_servicebus_namespace" "this" {
  name                = "${var.project_name}-${var.environment}-sb"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_servicebus_queue" "ats_agent_jobs" {
  name                = "ats-agent-jobs"
  namespace_id        = azurerm_servicebus_namespace.this.id
  max_delivery_count  = 3
  default_message_ttl = "PT1H"
}

# ── Redis ──────────────────────────────────────────────────────

resource "azurerm_redis_cache" "this" {
  name                = "${var.project_name}-${var.environment}-redis"
  resource_group_name = var.resource_group_name
  location            = var.location
  capacity            = var.redis_capacity
  family              = var.redis_family
  sku_name            = var.redis_sku
  minimum_tls_version = "1.2"
  tags                = var.tags

  redis_configuration {
  }
}

# ── AI Search ──────────────────────────────────────────────────

resource "azurerm_search_service" "this" {
  name                = "${var.project_name}-${var.environment}-search"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.search_sku
  replica_count       = var.search_replicas
  partition_count     = 1
  tags                = var.tags
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.this.endpoint
}

output "cosmos_key" {
  value     = azurerm_cosmosdb_account.this.primary_key
  sensitive = true
}

output "servicebus_connection_string" {
  value     = azurerm_servicebus_namespace.this.default_primary_connection_string
  sensitive = true
}

output "redis_host_name" {
  value = azurerm_redis_cache.this.hostname
}

output "redis_primary_key" {
  value     = azurerm_redis_cache.this.primary_access_key
  sensitive = true
}

output "search_endpoint" {
  value = azurerm_search_service.this.endpoint
}

output "search_primary_key" {
  value     = azurerm_search_service.this.primary_key
  sensitive = true
}

output "cosmos_account_id" {
  value = azurerm_cosmosdb_account.this.id
}

output "servicebus_namespace_id" {
  value = azurerm_servicebus_namespace.this.id
}

output "search_service_id" {
  value = azurerm_search_service.this.id
}

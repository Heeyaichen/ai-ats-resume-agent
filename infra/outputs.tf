# Design spec Section 13.5: required outputs.
# Additional outputs for CI/CD convenience.

output "api_url" {
  description = "FastAPI Container App URL."
  value       = module.compute.api_fqdn
}

output "static_web_app_url" {
  description = "Static Web App default host name."
  value       = module.compute.static_web_app_host_name
}

output "apim_gateway_url" {
  description = "API Management gateway URL."
  value       = module.compute.apim_gateway_url
}

output "key_vault_uri" {
  description = "Key Vault URI for secret access."
  value       = module.security.key_vault_uri
}

output "cosmos_endpoint" {
  description = "Cosmos DB account endpoint."
  value       = module.data.cosmos_endpoint
}

output "search_endpoint" {
  description = "AI Search service endpoint."
  value       = module.data.search_endpoint
}

output "application_insights_connection_string" {
  description = "Application Insights connection string."
  value       = module.observability.application_insights_connection_string
  sensitive   = true
}

output "frontdoor_endpoint_host_name" {
  description = "Front Door endpoint hostname (replaces deprecated CDN)."
  value       = module.compute.frontdoor_endpoint_host_name
}

output "resource_group_name" {
  description = "Resource group name."
  value       = azurerm_resource_group.this.name
}

# ── CI/CD convenience outputs ──────────────────────────────────

output "acr_name" {
  description = "Container Registry name (for az acr login)."
  value       = module.compute.acr_name
}

output "acr_login_server" {
  description = "Container Registry login server."
  value       = module.compute.acr_login_server
}

output "api_container_app_name" {
  description = "API Container App name (for az containerapp update)."
  value       = module.compute.api_container_app_name
}

output "worker_container_app_name" {
  description = "Worker Container App name (for az containerapp update)."
  value       = module.compute.worker_container_app_name
}

output "function_app_name" {
  description = "Function App name (for az functionapp deploy)."
  value       = module.compute.function_app_name
}

output "static_web_app_name" {
  description = "Static Web App name."
  value       = module.compute.static_web_app_name
}

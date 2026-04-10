# Design spec Section 13.5: required outputs.

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

output "cdn_endpoint_host_name" {
  description = "CDN endpoint FQDN."
  value       = module.compute.cdn_endpoint_host_name
}

output "resource_group_name" {
  description = "Resource group name."
  value       = azurerm_resource_group.this.name
}

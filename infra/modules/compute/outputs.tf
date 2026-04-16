output "api_fqdn" {
  value = azurerm_container_app.api.latest_revision_fqdn
}

output "static_web_app_host_name" {
  value = azurerm_static_web_app.this.default_host_name
}

output "apim_gateway_url" {
  value = azurerm_api_management.this.gateway_url
}

output "acr_login_server" {
  value = azurerm_container_registry.this.login_server
}

output "acr_name" {
  value = azurerm_container_registry.this.name
}

output "function_app_identity_principal_id" {
  value = azurerm_linux_function_app.this.identity[0].principal_id
}

output "function_app_name" {
  value = azurerm_linux_function_app.this.name
}

output "api_identity_principal_id" {
  value = azurerm_user_assigned_identity.api.principal_id
}

output "worker_identity_principal_id" {
  value = azurerm_user_assigned_identity.worker.principal_id
}

output "api_container_app_name" {
  value = azurerm_container_app.api.name
}

output "worker_container_app_name" {
  value = azurerm_container_app.worker.name
}

output "cdn_endpoint_host_name" {
  value = azurerm_cdn_endpoint.this.fqdn
}

output "container_app_environment_id" {
  value = azurerm_container_app_environment.this.id
}

output "static_web_app_name" {
  value = azurerm_static_web_app.this.name
}

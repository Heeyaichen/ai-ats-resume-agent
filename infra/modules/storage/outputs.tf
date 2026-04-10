output "storage_account_id" {
  value = azurerm_storage_account.this.id
}

output "storage_account_name" {
  value = azurerm_storage_account.this.name
}

output "storage_account_primary_connection_string" {
  value     = azurerm_storage_account.this.primary_connection_string
  sensitive = true
}

output "resumes_raw_container_name" {
  value = azurerm_storage_container.resumes_raw.name
}

output "reports_container_name" {
  value = azurerm_storage_container.reports.name
}

output "storage_account_primary_access_key" {
  value     = azurerm_storage_account.this.primary_access_key
  sensitive = true
}

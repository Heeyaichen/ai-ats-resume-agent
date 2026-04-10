variable "project_name" { type = string }
variable "environment" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tenant_id" { type = string }
variable "tags" {
  type    = map(string)
  default = {}
}

# Identity principal IDs for RBAC.
variable "api_identity_principal_id" { type = string }
variable "function_identity_principal_id" { type = string }

# Resource IDs for role assignment scopes.
variable "storage_account_id" { type = string }
variable "cosmos_account_id" { type = string }
variable "servicebus_namespace_id" { type = string }
variable "openai_account_id" { type = string }
variable "doc_intelligence_account_id" { type = string }
variable "translator_account_id" { type = string }
variable "language_account_id" { type = string }
variable "content_safety_account_id" { type = string }
variable "search_service_id" { type = string }

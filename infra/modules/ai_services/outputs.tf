output "openai_endpoint" {
  value = local.openai_account.endpoint
}

output "openai_id" {
  value = local.openai_account.id
}

output "openai_key" {
  value     = local.openai_account.primary_access_key
  sensitive = true
}

output "doc_intelligence_endpoint" {
  value = azurerm_cognitive_account.doc_intelligence.endpoint
}

output "doc_intelligence_id" {
  value = azurerm_cognitive_account.doc_intelligence.id
}

output "doc_intelligence_key" {
  value     = azurerm_cognitive_account.doc_intelligence.primary_access_key
  sensitive = true
}

output "translator_endpoint" {
  value = azurerm_cognitive_account.translator.endpoint
}

output "translator_id" {
  value = azurerm_cognitive_account.translator.id
}

output "translator_key" {
  value     = azurerm_cognitive_account.translator.primary_access_key
  sensitive = true
}

output "language_endpoint" {
  value = azurerm_cognitive_account.language.endpoint
}

output "language_id" {
  value = azurerm_cognitive_account.language.id
}

output "language_key" {
  value     = azurerm_cognitive_account.language.primary_access_key
  sensitive = true
}

output "content_safety_endpoint" {
  value = azurerm_cognitive_account.content_safety.endpoint
}

output "content_safety_id" {
  value = azurerm_cognitive_account.content_safety.id
}

output "content_safety_key" {
  value     = azurerm_cognitive_account.content_safety.primary_access_key
  sensitive = true
}

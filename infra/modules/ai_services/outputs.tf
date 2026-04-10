output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "openai_id" {
  value = azurerm_cognitive_account.openai.id
}

output "openai_key" {
  value     = azurerm_cognitive_account.openai.primary_access_key
  sensitive = true
}

output "doc_intelligence_endpoint" {
  value = azurerm_cognitive_account.doc_intelligence.endpoint
}

output "doc_intelligence_id" {
  value = azurerm_cognitive_account.doc_intelligence.id
}

output "translator_endpoint" {
  value = azurerm_cognitive_account.translator.endpoint
}

output "translator_id" {
  value = azurerm_cognitive_account.translator.id
}

output "language_endpoint" {
  value = azurerm_cognitive_account.language.endpoint
}

output "language_id" {
  value = azurerm_cognitive_account.language.id
}

output "content_safety_endpoint" {
  value = azurerm_cognitive_account.content_safety.endpoint
}

output "content_safety_id" {
  value = azurerm_cognitive_account.content_safety.id
}

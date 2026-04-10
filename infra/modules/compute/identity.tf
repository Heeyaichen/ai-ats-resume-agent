/** Managed identity for the Container App (API + worker). */

resource "azurerm_user_assigned_identity" "api" {
  name                = "${var.project_name}-${var.environment}-api-mi"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

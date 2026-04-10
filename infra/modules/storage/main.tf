/**
 * Storage module — Blob Storage account, containers, and lifecycle management.
 * Design spec Section 7.2: resumes-raw and reports containers with 90-day retention.
 */

resource "azurerm_storage_account" "this" {
  name                     = "${var.project_name}${var.environment}st"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = var.replication_type
  min_tls_version          = "TLS1_2"
  tags                     = var.tags
}

resource "azurerm_storage_container" "resumes_raw" {
  name                  = "resumes-raw"
  storage_account_name  = azurerm_storage_account.this.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "reports" {
  name                  = "reports"
  storage_account_name  = azurerm_storage_account.this.name
  container_access_type = "private"
}

# 90-day lifecycle rule for both containers (design spec Section 9.5).
resource "azurerm_storage_management_policy" "retention" {
  storage_account_id = azurerm_storage_account.this.id

  rule {
    name    = "delete-after-90-days"
    enabled = true

    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["resumes-raw/", "reports/"]
    }

    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 90
      }
    }
  }
}

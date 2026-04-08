terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.100"
    }
  }

  # Phase 9: add backend configuration for remote state storage.
}

provider "azurerm" {
  features {}
}

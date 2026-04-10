terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.100"
    }
  }

  # Backend configuration for remote state:
  # Uncomment and fill in for your storage account.
  # backend "azurerm" {
  #   resource_group_name  = "tfstate-rg"
  #   storage_account_name = "tfstatesa"
  #   container_name       = "tfstate"
  #   key                  = "ats-agent.tfstate"
  # }
}

provider "azurerm" {
  features {}
}

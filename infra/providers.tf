terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.100"
    }
  }

  # Remote state backend — configured via -backend-config flags
  # in CI (terraform.yml) or manual terraform init.
  #
  # Required -backend-config keys:
  #   resource_group_name  = "<tfstate resource group>"
  #   storage_account_name = "<tfstate storage account>"
  #   container_name       = "<tfstate container>"
  #   key                  = "<environment>.tfstate"
  #
  # The state storage account and container must be bootstrapped
  # before the first terraform init. See README for bootstrap steps.
  backend "azurerm" {
    # All values supplied via -backend-config at init time.
  }
}

provider "azurerm" {
  features {}
}

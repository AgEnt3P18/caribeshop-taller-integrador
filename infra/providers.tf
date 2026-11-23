terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.12"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # S1: estado remoto en Azure Storage, autenticado con Entra ID (sin llaves).
  # Los valores concretos se pasan con: terraform init -backend-config=backend.hcl
  # (backend.hcl esta en .gitignore).
  backend "azurerm" {}
}

provider "azurerm" {
  features {
    key_vault {
      # Purge protection activo: nunca purgar al destruir
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id     = var.subscription_id
  storage_use_azuread = true
}

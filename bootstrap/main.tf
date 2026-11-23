# Bootstrap del backend remoto de Terraform (S1).
# Se ejecuta UNA vez con estado local (ignorado por Git). Crea la cuenta de
# almacenamiento que guarda el estado del proyecto principal.
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
  }
}

provider "azurerm" {
  features {}
  subscription_id     = var.subscription_id
  storage_use_azuread = true
}

variable "subscription_id" {
  type        = string
  description = "ID de la suscripcion de Azure"
}

variable "location" {
  type    = string
  default = "eastus"
}

variable "operator_ips" {
  type        = list(string)
  description = "Rangos CIDR de salida del operador permitidos en el firewall"
}

data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_resource_group" "tfstate" {
  name     = "rg-caribeshop-tfstate"
  location = var.location
}

resource "azurerm_storage_account" "tfstate" {
  #checkov:skip=CKV_AZURE_206:LRS suficiente para el estado de un proyecto academico; versionado + soft delete cubren borrados
  #checkov:skip=CKV2_AZURE_1:Cifrado con llaves administradas por Microsoft; CMK agrega costo y complejidad sin beneficio en este alcance
  #checkov:skip=CKV2_AZURE_33:Sin private endpoint: el operador accede desde su IP (firewall) y no hay VPN
  #checkov:skip=CKV_AZURE_33:No se usan colas en esta cuenta
  #checkov:skip=CKV_AZURE_59:El acceso publico de red queda limitado por firewall a la IP del operador
  name                            = "stcstfstate${random_string.suffix.result}"
  resource_group_name             = azurerm_resource_group.tfstate.name
  location                        = azurerm_resource_group.tfstate.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  default_to_oauth_authentication = true

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
    ip_rules       = [for c in var.operator_ips : endswith(c, "/32") ? trimsuffix(c, "/32") : c]
  }

  sas_policy {
    expiration_period = "01.00:00:00"
  }
}

resource "azurerm_role_assignment" "operator_blob" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_storage_container" "tfstate" {
  #checkov:skip=CKV2_AZURE_21:El logging de lectura de blobs se cubre con diagnostic settings opcionales; fuera de alcance del bootstrap
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.tfstate.id
  container_access_type = "private"
}

output "backend_config" {
  value = <<-EOT
    resource_group_name  = "${azurerm_resource_group.tfstate.name}"
    storage_account_name = "${azurerm_storage_account.tfstate.name}"
    container_name       = "${azurerm_storage_container.tfstate.name}"
    key                  = "caribeshop.tfstate"
    use_azuread_auth     = true
  EOT
}

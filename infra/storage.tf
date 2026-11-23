# Storage de la aplicacion: sin llaves compartidas (solo Entra ID) y con firewall.
resource "azurerm_storage_account" "app" {
  #checkov:skip=CKV_AZURE_206:LRS aceptado en entorno de taller; en produccion se usaria ZRS
  #checkov:skip=CKV2_AZURE_1:Cifrado con llaves administradas por Microsoft (PMK); CMK fuera de alcance
  #checkov:skip=CKV2_AZURE_33:Sin private endpoint; acceso de red limitado a snet-app (service endpoint) e IP del operador
  #checkov:skip=CKV_AZURE_33:La cuenta no usa colas
  #checkov:skip=CKV_AZURE_59:public_network_access se mantiene con default_action=Deny (firewall)
  name                            = "stcsapp${local.suffix}"
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  default_to_oauth_authentication = true
  tags                            = var.tags

  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  network_rules {
    default_action             = "Deny"
    bypass                     = ["AzureServices"]
    ip_rules                   = local.storage_ip_rules
    virtual_network_subnet_ids = [azurerm_subnet.app.id]
  }

  sas_policy {
    expiration_period = "01.00:00:00"
  }
}

resource "azurerm_storage_container" "assets" {
  #checkov:skip=CKV2_AZURE_21:Logging de lectura de blobs no requerido para el contenedor de assets del taller
  name                  = "assets"
  storage_account_id    = azurerm_storage_account.app.id
  container_access_type = "private"
}

data "azurerm_client_config" "current" {}

# S3: Key Vault con RBAC, purge protection y firewall (subred de la app + IP del operador).
resource "azurerm_key_vault" "main" {
  #checkov:skip=CKV2_AZURE_32:Sin private endpoint; el acceso de red queda restringido por firewall a snet-app (service endpoint) y a la IP del operador
  #checkov:skip=CKV_AZURE_189:El acceso publico se mantiene con default_action=Deny para permitir al operador administrar desde su IP
  name                          = "kv-cs-${local.suffix}"
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  purge_protection_enabled      = true
  soft_delete_retention_days    = 7
  public_network_access_enabled = true
  tags                          = var.tags

  network_acls {
    default_action             = "Deny"
    bypass                     = "AzureServices"
    ip_rules                   = var.operator_ips
    virtual_network_subnet_ids = [azurerm_subnet.app.id]
  }
}

# El operador (quien ejecuta Terraform) administra secretos.
resource "azurerm_role_assignment" "operator_kv" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Propagacion de RBAC antes de escribir el secreto.
resource "time_sleep" "rbac_propagation" {
  create_duration = "90s"
  depends_on      = [azurerm_role_assignment.operator_kv]
}

resource "random_password" "db" {
  length           = 32
  special          = true
  override_special = "!#%*-_=+"
}

resource "time_offset" "secret_expiry" {
  offset_days = 90
}

resource "azurerm_key_vault_secret" "db" {
  name            = var.secret_name
  value           = random_password.db.result
  key_vault_id    = azurerm_key_vault.main.id
  content_type    = "text/plain"
  expiration_date = time_offset.secret_expiry.rfc3339
  tags            = var.tags

  depends_on = [time_sleep.rbac_propagation]
}

# S4: la identidad del VMSS SOLO puede leer ESTE secreto
# (rol de datos "Key Vault Secrets User" con alcance al secreto, no al vault).
resource "azurerm_role_assignment" "vmss_secret_reader" {
  scope                = azurerm_key_vault_secret.db.resource_versionless_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_virtual_machine_scale_set.app.identity[0].principal_id
}

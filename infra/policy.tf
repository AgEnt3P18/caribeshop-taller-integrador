# S5: politicas con efecto Deny asignadas por Terraform al grupo de recursos.

# 1) Built-in "Network interfaces should not have public IPs" (efecto Deny).
#    Refuerza S2: nadie puede crear una NIC con IP publica en el RG.
resource "azurerm_resource_group_policy_assignment" "deny_nic_public_ip" {
  name                 = "deny-nic-public-ip"
  display_name         = "CaribeShop - Denegar NICs con IP publica"
  resource_group_id    = azurerm_resource_group.main.id
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/83a86a26-fd1f-447c-b59d-e51f44264114"
  enforce              = true
}

# 2) Built-in "Allowed locations" (efecto Deny): solo la region del proyecto.
resource "azurerm_resource_group_policy_assignment" "allowed_locations" {
  name                 = "allowed-locations"
  display_name         = "CaribeShop - Solo region ${var.location}"
  resource_group_id    = azurerm_resource_group.main.id
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/e56962a6-4747-49cd-b67b-bf8b01975c4c"
  enforce              = true

  parameters = jsonencode({
    listOfAllowedLocations = { value = [var.location] }
  })
}

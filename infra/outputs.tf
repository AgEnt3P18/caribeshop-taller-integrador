output "resource_group" {
  value = azurerm_resource_group.main.name
}

output "app_url" {
  value = "http://${azurerm_public_ip.lb.fqdn}"
}

output "lb_public_ip" {
  value = azurerm_public_ip.lb.ip_address
}

output "vmss_name" {
  value = azurerm_linux_virtual_machine_scale_set.app.name
}

output "vmss_principal_id" {
  value = azurerm_linux_virtual_machine_scale_set.app.identity[0].principal_id
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.main.workspace_id
}

output "autoscale_name" {
  value = azurerm_monitor_autoscale_setting.app.name
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

# S6: auditoria del Key Vault (incluye SecretGet de la identidad del VMSS).
resource "azurerm_monitor_diagnostic_setting" "kv" {
  name                       = "diag-kv-to-law"
  target_resource_id         = azurerm_key_vault.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "AuditEvent"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

# Historial del autoscale consultable por KQL (E3).
resource "azurerm_monitor_diagnostic_setting" "autoscale" {
  name                       = "diag-autoscale-to-law"
  target_resource_id         = azurerm_monitor_autoscale_setting.app.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "AutoscaleEvaluations"
  }

  enabled_log {
    category = "AutoscaleScaleActions"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "lb" {
  name                       = "diag-lb-to-law"
  target_resource_id         = azurerm_lb.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_metric {
    category = "AllMetrics"
  }
}

# E5: grupo de acciones con notificacion por correo.
resource "azurerm_monitor_action_group" "ops" {
  name                = "ag-${var.prefix}-ops"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "csops"
  tags                = var.tags

  email_receiver {
    name                    = "operador"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
}

# E5: sonda de salud por debajo de 100 % (alguna instancia no sana).
resource "azurerm_monitor_metric_alert" "probe" {
  name                = "alert-health-probe-below-100"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_lb.main.id]
  description         = "El estado de la sonda /health del balanceador cayo por debajo de 100 %."
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"
  tags                = var.tags

  criteria {
    metric_namespace = "Microsoft.Network/loadBalancers"
    metric_name      = "DipAvailability"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 100
  }

  action {
    action_group_id = azurerm_monitor_action_group.ops.id
  }
}

# E5: CPU sostenida alta en el VMSS.
resource "azurerm_monitor_metric_alert" "cpu" {
  name                = "alert-vmss-cpu-sustained"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_linux_virtual_machine_scale_set.app.id]
  description         = "CPU promedio del VMSS > 80 % durante 15 minutos."
  severity            = 3
  frequency           = "PT1M"
  window_size         = "PT15M"
  tags                = var.tags

  criteria {
    metric_namespace = "Microsoft.Compute/virtualMachineScaleSets"
    metric_name      = "Percentage CPU"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.ops.id
  }
}

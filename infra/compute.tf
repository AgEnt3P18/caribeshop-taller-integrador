# Llave SSH generada solo porque Azure exige una credencial de administrador en
# Linux. La llave privada nunca se exporta y el puerto 22 no es alcanzable
# (NSG + sin IP publica). Queda en el estado remoto cifrado (ver informe, P6).
resource "tls_private_key" "admin" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

locals {
  cloud_init = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    app_b64     = filebase64("${path.module}/../app/app.py")
    vault_name  = azurerm_key_vault.main.name
    secret_name = var.secret_name
    work_ms     = var.work_ms
  })
}

resource "azurerm_linux_virtual_machine_scale_set" "app" {
  #checkov:skip=CKV_AZURE_97:Encryption at host requiere registrar la feature EncryptionAtHost en la suscripcion; los discos ya van cifrados en reposo con SSE (PMK)
  #checkov:skip=CKV_AZURE_178:Se usa autenticacion por llave SSH; la contrasena esta deshabilitada (falso positivo en VMSS)
  name                            = "vmss-${var.prefix}"
  location                        = azurerm_resource_group.main.location
  resource_group_name             = azurerm_resource_group.main.name
  sku                             = var.vm_size
  instances                       = var.min_instances
  zones                           = var.zones
  zone_balance                    = true
  overprovision                   = false
  upgrade_mode                    = "Manual"
  admin_username                  = "azureops"
  disable_password_authentication = true
  custom_data                     = base64encode(local.cloud_init)
  health_probe_id                 = azurerm_lb_probe.health.id
  provision_vm_agent              = true
  extension_operations_enabled    = true
  secure_boot_enabled             = true
  vtpm_enabled                    = true
  tags                            = var.tags

  admin_ssh_key {
    username   = "azureops"
    public_key = tls_private_key.admin.public_key_openssh
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
  }

  # Sin bloque public_ip_address => instancias sin IP publica (S2)
  network_interface {
    name                      = "nic-app"
    primary                   = true
    network_security_group_id = azurerm_network_security_group.app.id

    ip_configuration {
      name                                   = "ipcfg"
      primary                                = true
      subnet_id                              = azurerm_subnet.app.id
      load_balancer_backend_address_pool_ids = [azurerm_lb_backend_address_pool.app.id]
    }
  }

  identity {
    type = "SystemAssigned"
  }

  # E4: reparacion automatica basada en la sonda del balanceador.
  automatic_instance_repair {
    enabled      = true
    grace_period = "PT10M"
    action       = "Replace"
  }

  boot_diagnostics {}

  lifecycle {
    # E3: el autoscale es el duenio del numero de instancias
    ignore_changes = [instances]
  }

  depends_on = [
    azurerm_lb_rule.http,
    azurerm_lb_outbound_rule.egress,
    azurerm_subnet_network_security_group_association.app,
  ]
}

# E3: autoscale con histeresis (70 % sube / 30 % baja) y cooldowns asimetricos.
resource "azurerm_monitor_autoscale_setting" "app" {
  name                = "autoscale-${var.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  target_resource_id  = azurerm_linux_virtual_machine_scale_set.app.id
  tags                = var.tags

  profile {
    name = "default"

    capacity {
      default = var.min_instances
      minimum = var.min_instances
      maximum = var.max_instances
    }

    # Scale-out: CPU promedio > 70 % en 5 min -> +1. Cooldown 5 min: tiempo de
    # arranque de una instancia (~2-3 min) + estabilizacion de la metrica.
    rule {
      metric_trigger {
        metric_name        = "Percentage CPU"
        metric_resource_id = azurerm_linux_virtual_machine_scale_set.app.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT5M"
        time_aggregation   = "Average"
        operator           = "GreaterThan"
        threshold          = 70
      }
      scale_action {
        direction = "Increase"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT5M"
      }
    }

    # Scale-in: CPU promedio < 30 % en 10 min -> -1. Ventana y cooldown mas
    # largos para no retirar capacidad ante un valle momentaneo (flapping).
    rule {
      metric_trigger {
        metric_name        = "Percentage CPU"
        metric_resource_id = azurerm_linux_virtual_machine_scale_set.app.id
        time_grain         = "PT1M"
        statistic          = "Average"
        time_window        = "PT10M"
        time_aggregation   = "Average"
        operator           = "LessThan"
        threshold          = 30
      }
      scale_action {
        direction = "Decrease"
        type      = "ChangeCount"
        value     = "1"
        cooldown  = "PT10M"
      }
    }
  }

  notification {
    email {
      custom_emails = [var.alert_email]
    }
  }
}

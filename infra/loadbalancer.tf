# IP publica Standard zonal-redundante: unica IP publica de la solucion.
resource "azurerm_public_ip" "lb" {
  name                = "pip-lb-${var.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  zones               = ["1", "2", "3"]
  domain_name_label   = "${var.prefix}-${local.suffix}"
  tags                = var.tags
}

resource "azurerm_lb" "main" {
  name                = "lb-${var.prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  tags                = var.tags

  frontend_ip_configuration {
    name                 = "fe-public"
    public_ip_address_id = azurerm_public_ip.lb.id
  }
}

resource "azurerm_lb_backend_address_pool" "app" {
  name            = "be-app"
  loadbalancer_id = azurerm_lb.main.id
}

# E2: sonda HTTP sobre el endpoint dedicado /health.
# 5 s x 2 fallos => una instancia sale de rotacion en ~10 s.
resource "azurerm_lb_probe" "health" {
  name                = "probe-health"
  loadbalancer_id     = azurerm_lb.main.id
  protocol            = "Http"
  port                = 80
  request_path        = "/health"
  interval_in_seconds = 5
  probe_threshold     = 2
}

resource "azurerm_lb_rule" "http" {
  name                           = "rule-http"
  loadbalancer_id                = azurerm_lb.main.id
  protocol                       = "Tcp"
  frontend_port                  = 80
  backend_port                   = 80
  frontend_ip_configuration_name = "fe-public"
  backend_address_pool_ids       = [azurerm_lb_backend_address_pool.app.id]
  probe_id                       = azurerm_lb_probe.health.id
  disable_outbound_snat          = true
  idle_timeout_in_minutes        = 4
}

# SNAT explicito para la salida permitida por el NSG (Key Vault, Monitor, Storage).
resource "azurerm_lb_outbound_rule" "egress" {
  name                     = "outbound-egress"
  loadbalancer_id          = azurerm_lb.main.id
  protocol                 = "All"
  backend_address_pool_id  = azurerm_lb_backend_address_pool.app.id
  allocated_outbound_ports = 1024

  frontend_ip_configuration {
    name = "fe-public"
  }
}

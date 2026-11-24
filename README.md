# CaribeShop · Plataforma segura, escalable y altamente disponible en Azure

Taller integrador — Infraestructura para TI (UTB, NRC 1216).
Integrantes: Santiago Payares González · Cristian Matteo Benitez Montes.

Toda la plataforma se despliega con **Terraform** (estado remoto en Azure Storage con
Entra ID, sin llaves), se valida en **GitHub Actions** (fmt · validate · Checkov bloqueante)
y se prueba con **Locust** y pruebas de falla.

## Arquitectura

```
                Internet
                    │  HTTP 80
     IP pública Standard (zonas 1-2-3)  ──  FQDN caribeshop-<sufijo>.eastus.cloudapp.azure.com
                    │
     Load Balancer Standard ── sonda HTTP /health (5 s × 2)
           │  regla 80 + regla de salida (SNAT explícito)
 ┌──────── snet-app 10.20.1.0/24 ── NSG nsg-app ────────────────────────────────┐
 │  Entrada: 80 desde Internet, sondas AzureLoadBalancer; todo lo demás Deny     │
 │  Salida : 443 → AzureKeyVault, AzureMonitor, Storage.eastus; Internet Deny    │
 │                                                                               │
 │  VMSS vmss-caribeshop  (Standard_D2s_v4, zonas 1/2/3, min 2 · max 4)          │
 │   · Ubuntu 24.04 + cloud-init (app Python stdlib)  · sin IP pública           │
 │   · identidad administrada (SystemAssigned)       · reparación automática     │
 │   · autoscale CPU >70 % (+1, 5 min) / <30 % (−1, 10 min)                      │
 └───────────┬───────────────────────────────────────┬───────────────────────────┘
             │ service endpoint Microsoft.KeyVault    │ service endpoint Microsoft.Storage
   Key Vault (RBAC, purge protection, firewall)   Storage (sin llaves, firewall)
             │ AuditEvent
   Log Analytics ◄── diagnostic settings (KV, autoscale, LB) ── alertas (correo)

 Azure Policy (Deny) sobre el RG: NIC sin IP pública · solo región eastus
 GitHub Actions: terraform fmt -check · validate · Checkov (bloqueante)
```

## Estructura

| Ruta | Contenido |
|---|---|
| `bootstrap/` | Cuenta de almacenamiento del estado remoto (se ejecuta una sola vez) |
| `infra/` | Red, NSG, LB, VMSS, autoscale, Key Vault, Storage, monitoreo, políticas |
| `infra/cloud-init.yaml.tftpl` | Configuración automática de la instancia (D3) |
| `app/app.py` | App (solo biblioteca estándar): `/`, `/health`, `/secret`, `/work`, `/egress-check` |
| `load/locustfile.py` | Perfiles `capacity`, `staircase` (28 min) y `steady` |
| `scripts/` | Pruebas de falla, seguridad y recolección de evidencias |
| `evidencias/` | CSV y HTML de Locust, salidas de comandos y capturas |
| `.github/workflows/iac-security.yml` | Pipeline DevSecOps |

## Variables requeridas (`infra/terraform.tfvars`, ignorado por Git)

| Variable | Descripción |
|---|---|
| `subscription_id` | Suscripción de Azure |
| `operator_ips` | CIDR de salida del operador (firewalls de Key Vault y Storage) |
| `alert_email` | Correo para alertas y notificaciones del autoscale |
| `location` | Región (por defecto `eastus`) |
| `vm_size` | Tamaño de VM (por defecto `Standard_D2s_v4`) |
| `max_instances` | Tope del autoscale (por defecto 4; cuota regional 10 vCPU) |

Ver `infra/terraform.tfvars.example` y `infra/backend.hcl.example`.

## Desplegar

```bash
az login
# 1. Backend remoto (una vez)
cd bootstrap && terraform init && terraform apply
terraform output -raw backend_config > ../infra/backend.hcl
# 2. Plataforma
cd ../infra
terraform init -backend-config=backend.hcl
terraform plan -out tfplan && terraform apply tfplan
terraform output app_url
```

## Destruir

```bash
cd infra && terraform destroy
cd ../bootstrap && terraform destroy   # opcional: elimina el estado
```

El Key Vault queda en *soft delete* 7 días (purge protection), por diseño.

## Acceso de soporte (sin SSH)

El puerto 22 nunca se abre. El soporte en temporada alta usa el plano de control de Azure,
autenticado con Entra ID y auditado en el registro de actividad:

```bash
az vmss run-command invoke -g rg-caribeshop -n vmss-caribeshop --instance-id <id>   --command-id RunShellScript --scripts "journalctl -u caribeshop -n 50"
```

## Checklist de la línea base de seguridad

- [x] Estado en backend remoto `azurerm` con `use_azuread_auth` (sin llaves compartidas); `*.tfstate`, `*.tfvars` y `backend.hcl` en `.gitignore`
- [x] Sin credenciales en el código: el secreto lo genera `random_password` y vive solo en Key Vault y en el estado cifrado
- [x] Ninguna VM con IP pública; la única IP pública es la del balanceador
- [x] SSH/RDP no expuestos: NSG con `Deny-All-Inbound` y solo 80 desde Internet/AzureLoadBalancer
- [x] Salida a Internet denegada en el NSG (solo Key Vault, Monitor y Storage por etiqueta de servicio)
- [x] Key Vault con RBAC, purge protection, firewall (subred + IP del operador) y secreto con expiración (90 días)
- [x] Identidad administrada del VMSS con **Key Vault Secrets User** con alcance **al secreto** (mínimo privilegio)
- [x] Storage sin llaves compartidas, TLS 1.2, sin acceso público a blobs y con firewall
- [x] Azure Policy con efecto Deny asignada por Terraform (NIC con IP pública · ubicaciones permitidas)
- [x] Diagnostic settings del Key Vault hacia Log Analytics (AuditEvent)
- [x] Alertas de Azure Monitor (sonda < 100 %, CPU sostenida) con correo
- [x] Pipeline con `terraform fmt -check`, `validate` y Checkov bloqueante; cada `#checkov:skip` justificado

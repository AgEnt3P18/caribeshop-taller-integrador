variable "subscription_id" {
  type        = string
  description = "ID de la suscripcion de Azure donde se despliega."
}

variable "location" {
  type        = string
  description = "Region con zonas de disponibilidad."
  default     = "eastus"
}

variable "prefix" {
  type        = string
  description = "Prefijo de nombres de recursos."
  default     = "caribeshop"
}

variable "operator_ips" {
  type        = list(string)
  description = "Rangos CIDR de salida del operador (su ISP puede usar varias IPs). Se permiten en los firewalls de Key Vault y Storage."

  validation {
    condition     = alltrue([for c in var.operator_ips : can(cidrhost(c, 0))])
    error_message = "Cada elemento debe ser un CIDR IPv4, p. ej. 181.0.0.10/32."
  }
}

variable "alert_email" {
  type        = string
  description = "Correo que recibe las alertas de Azure Monitor y las notificaciones del autoscale."
}

variable "vm_size" {
  type        = string
  description = "Tamano de las instancias del VMSS."
  default     = "Standard_D2s_v4"
}

variable "zones" {
  type        = list(string)
  description = "Zonas de disponibilidad del VMSS (E1: al menos 2)."
  default     = ["1", "2", "3"]

  validation {
    condition     = length(var.zones) >= 2
    error_message = "E1 exige al menos 2 zonas."
  }
}

variable "min_instances" {
  type    = number
  default = 2

  validation {
    condition     = var.min_instances >= 1
    error_message = "min_instances debe ser >= 1 (2 en operacion normal; 1 solo para la medicion P1.1)."
  }
}

variable "max_instances" {
  type        = number
  description = "Tope del autoscale. Revisar cuota: az vm list-usage -l <region> -o table."
  default     = 4
}

variable "work_ms" {
  type        = number
  description = "Milisegundos de CPU que consume cada peticion a /work."
  default     = 40
}

variable "secret_name" {
  type    = string
  default = "db-password"
}

variable "tags" {
  type = map(string)
  default = {
    proyecto   = "caribeshop"
    curso      = "infraestructura-ti-utb"
    entorno    = "taller"
    gestionado = "terraform"
  }
}

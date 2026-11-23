#!/usr/bin/env bash
# Recolecta evidencias de configuracion (S2, S3, S4, E1, E2, E3) en evidencias/cli/
set -euo pipefail
cd "$(dirname "$0")/../infra"
OUT=../evidencias/cli
mkdir -p "$OUT"

RG=$(terraform output -raw resource_group)
VMSS=$(terraform output -raw vmss_name)
PID=$(terraform output -raw vmss_principal_id)
KV=$(terraform output -raw key_vault_name)
URL=$(terraform output -raw app_url)

echo "## S2 - instancias del VMSS y sus IPs (sin IP publica)" > "$OUT/s2_vmss_ips.txt"
az vmss nic list -g "$RG" --vmss-name "$VMSS" \
  --query "[].{nic:name, privateIp:ipConfigurations[0].privateIPAddress, publicIp:ipConfigurations[0].publicIPAddress}" \
  -o table >> "$OUT/s2_vmss_ips.txt"
echo -e "\n## az vm list-ip-addresses (VMs independientes en el RG: debe estar vacio)" >> "$OUT/s2_vmss_ips.txt"
az vm list-ip-addresses -g "$RG" -o table >> "$OUT/s2_vmss_ips.txt" 2>&1 || true
echo -e "\n## IPs publicas en el RG (solo la del balanceador)" >> "$OUT/s2_vmss_ips.txt"
az network public-ip list -g "$RG" --query "[].{name:name, ip:ipAddress, sku:sku.name, zones:join(',',zones)}" -o table >> "$OUT/s2_vmss_ips.txt"

echo "## S2 - reglas del NSG" > "$OUT/s2_nsg_rules.txt"
az network nsg rule list -g "$RG" --nsg-name nsg-app \
  --query "sort_by([], &priority)[].{prio:priority, dir:direction, acc:access, proto:protocol, src:sourceAddressPrefix, dst:destinationAddressPrefix, port:destinationPortRange, name:name}" \
  -o table >> "$OUT/s2_nsg_rules.txt"

echo "## S4 - az role assignment list --assignee <principal_id> --all" > "$OUT/s4_role_assignments.txt"
az role assignment list --assignee "$PID" --all \
  --query "[].{role:roleDefinitionName, scope:scope}" -o table >> "$OUT/s4_role_assignments.txt"

echo "## S3 - Key Vault" > "$OUT/s3_keyvault.txt"
az keyvault show -n "$KV" --query "{name:name, rbac:properties.enableRbacAuthorization, purgeProtection:properties.enablePurgeProtection, softDeleteDays:properties.softDeleteRetentionInDays, defaultAction:properties.networkAcls.defaultAction, ipRules:properties.networkAcls.ipRules[].value, subnets:properties.networkAcls.virtualNetworkRules[].id}" -o json >> "$OUT/s3_keyvault.txt"
az keyvault secret show --vault-name "$KV" -n db-password --query "{name:name, enabled:attributes.enabled, expires:attributes.expires, contentType:contentType}" -o json >> "$OUT/s3_keyvault.txt"
echo -e "\n## Endpoint /secret de la app (huella, nunca el valor)" >> "$OUT/s3_keyvault.txt"
for i in 1 2 3 4; do curl -s "$URL/secret"; echo; done >> "$OUT/s3_keyvault.txt"

echo "## E1 - instancias y zonas" > "$OUT/e1_instances_zones.txt"
az vmss list-instances -g "$RG" -n "$VMSS" \
  --query "[].{instance:name, id:instanceId, zone:zones[0], state:provisioningState}" -o table >> "$OUT/e1_instances_zones.txt"

echo "## E2 - sonda de salud" > "$OUT/e2_probe.txt"
az network lb probe list -g "$RG" --lb-name lb-caribeshop -o table >> "$OUT/e2_probe.txt"

echo "## E3/E4 - autoscale y reparacion automatica" > "$OUT/e3_e4_config.txt"
az monitor autoscale show -g "$RG" -n "$(terraform output -raw autoscale_name)" \
  --query "{min:profiles[0].capacity.minimum, max:profiles[0].capacity.maximum, rules:profiles[0].rules[].{metric:metricTrigger.metricName, op:metricTrigger.operator, thr:metricTrigger.threshold, window:metricTrigger.timeWindow, dir:scaleAction.direction, cooldown:scaleAction.cooldown}}" -o json >> "$OUT/e3_e4_config.txt"
az vmss show -g "$RG" -n "$VMSS" --query "{repair:automaticRepairsPolicy, zones:zones, zoneBalance:zoneBalance, sku:sku}" -o json >> "$OUT/e3_e4_config.txt"

echo "OK -> $OUT"

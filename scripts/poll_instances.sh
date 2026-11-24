#!/usr/bin/env bash
# Registra cada 20 s el numero de instancias del VMSS (tsv: timestamp_utc \t total \t succeeded \t detalle)
OUT=$1; DUR=${2:-3600}; END=$(( $(date +%s) + DUR ))
while [ "$(date +%s)" -lt "$END" ]; do
  J=$(az vmss list-instances -g rg-caribeshop -n vmss-caribeshop --query "[].[instanceId,zones[0],provisioningState]" -o tsv 2>/dev/null | tr '\t\r\n' ':  ')
  T=$(echo "$J" | wc -w); S=$(echo "$J" | grep -o "Succeeded" | wc -l)
  printf "%s\t%s\t%s\t%s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$T" "$S" "$J" >> "$OUT"
  sleep 20
done

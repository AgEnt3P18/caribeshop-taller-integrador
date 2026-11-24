#!/usr/bin/env bash
# P2 - Pruebas de falla con carga moderada.
#   bash scripts/p2_failure.sh logica  <instance_id>   # /health -> 503 en esa instancia
#   bash scripts/p2_failure.sh abrupta <instance_id>   # elimina la instancia
# Genera en evidencias/: p2_<tipo>_monitor.csv, p2_<tipo>_locust*.csv/html, p2_<tipo>_t0.txt
set -euo pipefail
TIPO=$1; ID=$2
cd "$(dirname "$0")/.."
URL=http://caribeshop-s0pya.eastus.cloudapp.azure.com
RG=rg-caribeshop; VMSS=vmss-caribeshop
EV=evidencias
PRE=${PRE:-60}; POST=${POST:-540}
DUR=$((PRE + POST))

echo "[$(date -u +%T)] carga moderada (Locust steady 40 usuarios) + monitor 10 req/s durante ${DUR}s"
( cd load && LOCUST_MODE=steady STEADY_USERS=40 DURATION=$DUR python3 -m locust -f locustfile.py --host $URL \
    --headless --csv ../$EV/p2_${TIPO}_locust --csv-full-history --html ../$EV/p2_${TIPO}_locust.html --only-summary >/dev/null 2>&1 ) &
LP=$!
python3 scripts/probe_monitor.py $URL/ $EV/p2_${TIPO}_monitor.csv --rate 10 --duration $DUR --timeout 3 > $EV/p2_${TIPO}_monitor_summary.txt &
MP=$!
sleep $PRE

if [ "$TIPO" = "logica" ]; then
  echo "[$(date -u +%T)] marcando instancia $ID como no sana (crea /var/lib/caribeshop/unhealthy)"
  az vmss run-command invoke -g $RG -n $VMSS --instance-id $ID --command-id RunShellScript \
    --scripts 'touch /var/lib/caribeshop/unhealthy; echo T0_EPOCH=$(date +%s.%N); hostname' \
    --query "value[0].message" -o tsv | tee $EV/p2_${TIPO}_t0.txt
else
  T0=$(date +%s.%N)
  echo "T0_EPOCH=$T0" > $EV/p2_${TIPO}_t0.txt
  echo "[$(date -u +%T)] eliminando instancia $ID (az vmss delete-instances)"
  az vmss delete-instances -g $RG -n $VMSS --instance-ids $ID --no-wait
  echo "eliminacion solicitada" >> $EV/p2_${TIPO}_t0.txt
fi
wait $MP $LP || true
echo "[$(date -u +%T)] fin"; cat $EV/p2_${TIPO}_monitor_summary.txt

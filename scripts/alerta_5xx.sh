#!/usr/bin/env bash
# Crea (NO ejecutar sin revisar) una política de Cloud Monitoring que avisa por email
# cuando el servicio Cloud Run `erp-backend` devuelve MÁS DE 3 respuestas 5xx en 5 minutos.
#
# Uso:
#   ALERT_EMAIL=ops@soldigem.com.pe ./scripts/alerta_5xx.sh            # crea canal + política
#   ALERT_EMAIL=ops@soldigem.com.pe ./scripts/alerta_5xx.sh --dry-run  # solo imprime lo que haría
#
# Requisitos: gcloud autenticado con permisos monitoring.alertPolicies.create y
# monitoring.notificationChannels.create en el proyecto; API monitoring.googleapis.com habilitada.
# Idempotencia: si ya existe un canal con el mismo email o una política con el mismo
# nombre, se reutilizan (no se duplican).
set -euo pipefail

PROJECT="${PROJECT:-erp-system-468516}"
SERVICE="${SERVICE:-erp-backend}"
ALERT_EMAIL="${ALERT_EMAIL:?Define ALERT_EMAIL=correo@dominio con el destinatario de la alerta}"
UMBRAL="${UMBRAL:-3}"            # > 3 respuestas 5xx
VENTANA="${VENTANA:-300s}"       # en 5 minutos
POLICY_NAME="ERP backend: >${UMBRAL} respuestas 5xx en ${VENTANA}"
DRY_RUN="${1:-}"

run() { if [[ "$DRY_RUN" == "--dry-run" ]]; then echo "+ $*"; else "$@"; fi; }

echo "Proyecto: $PROJECT · servicio: $SERVICE · email: $ALERT_EMAIL · umbral: >$UMBRAL 5xx / $VENTANA"
run gcloud services enable monitoring.googleapis.com --project "$PROJECT"

# 1) Canal de notificación por email (reutiliza si ya existe).
CHANNEL=$(gcloud beta monitoring channels list --project "$PROJECT" \
  --filter="type=\"email\" AND labels.email_address=\"$ALERT_EMAIL\"" \
  --format='value(name)' 2>/dev/null | head -1 || true)
if [[ -z "$CHANNEL" ]]; then
  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo "+ gcloud beta monitoring channels create --display-name='ERP alertas (email)' --type=email --channel-labels=email_address=$ALERT_EMAIL --project $PROJECT"
    CHANNEL="projects/$PROJECT/notificationChannels/<se-crea-al-ejecutar>"
  else
    CHANNEL=$(gcloud beta monitoring channels create --project "$PROJECT" \
      --display-name="ERP alertas (email)" --type=email \
      --channel-labels="email_address=$ALERT_EMAIL" --format='value(name)')
  fi
fi
echo "Canal: $CHANNEL"

# 2) Política: métrica run.googleapis.com/request_count filtrada a response_code_class=5xx,
#    sumada en ventanas de 5 min (ALIGN_SUM) y agregada entre revisiones (REDUCE_SUM);
#    dispara si el total > UMBRAL. duration=0s → evalúa cada ventana.
POLICY_JSON=$(mktemp)
cat > "$POLICY_JSON" <<JSON
{
  "displayName": "$POLICY_NAME",
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$CHANNEL"],
  "documentation": {
    "mimeType": "text/markdown",
    "content": "El backend ERP (Cloud Run \`$SERVICE\`) devolvió más de $UMBRAL respuestas 5xx en $VENTANA.\n\nRevisar: \`gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE AND severity>=ERROR' --freshness=15m\`\nLos logs son JSON: filtrar por jsonPayload.request_id / jsonPayload.empresa_id.\nRollback: ver DEPLOY.md §7."
  },
  "conditions": [{
    "displayName": "5xx > $UMBRAL en $VENTANA",
    "conditionThreshold": {
      "filter": "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"$SERVICE\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\"",
      "aggregations": [{
        "alignmentPeriod": "$VENTANA",
        "perSeriesAligner": "ALIGN_SUM",
        "crossSeriesReducer": "REDUCE_SUM",
        "groupByFields": ["resource.labels.service_name"]
      }],
      "comparison": "COMPARISON_GT",
      "thresholdValue": $UMBRAL,
      "duration": "0s",
      "trigger": {"count": 1}
    }
  }],
  "alertStrategy": {"autoClose": "1800s"}
}
JSON

EXISTING=$(gcloud alpha monitoring policies list --project "$PROJECT" \
  --filter="displayName=\"$POLICY_NAME\"" --format='value(name)' 2>/dev/null | head -1 || true)
if [[ -n "$EXISTING" ]]; then
  echo "La política ya existe: $EXISTING → se actualiza"
  run gcloud alpha monitoring policies update "$EXISTING" --project "$PROJECT" --policy-from-file="$POLICY_JSON"
else
  run gcloud alpha monitoring policies create --project "$PROJECT" --policy-from-file="$POLICY_JSON"
fi

if [[ "$DRY_RUN" == "--dry-run" ]]; then echo "--- política (JSON) ---"; cat "$POLICY_JSON"; fi
rm -f "$POLICY_JSON"
echo "Listo. Probar: forzar un 5xx no es trivial en prod; verificar la política en https://console.cloud.google.com/monitoring/alerting?project=$PROJECT"

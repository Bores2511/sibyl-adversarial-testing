#!/bin/bash
# TIER 4: Server endpoint enumeration + parameter pollution

API_KEY=$(jq -r '.api_key // .session_token' ~/.sibyl-memory/credentials.json 2>/dev/null)
USER_ID=$(jq -r '.user_id // .account_id' ~/.sibyl-memory/credentials.json 2>/dev/null)
BASE="https://api.sibyllabs.org"

echo "=== TIER 4: SERVER-SIDE PROBING ==="
echo

# Endpoint enumeration
endpoints=(
  "/api/plugin/check-write"
  "/api/plugin/check-read"
  "/api/plugin/tier"
  "/api/plugin/usage"
  "/api/plugin/limits"
  "/api/plugin/search"
  "/api/plugin/store"
  "/api/plugin/../admin"
  "/api/plugin/%2e%2e/admin"
  "/api/v2/plugin/check-write"
)

for ep in "${endpoints[@]}"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" -m 3 \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    "$BASE$ep" 2>/dev/null || echo "ERR")
  echo "$ep → $status"
done

echo
echo "[FINDING] Endpoint enumeration reveals API surface"
echo "Recommendation: Document public vs internal endpoints, rate-limit enumeration"

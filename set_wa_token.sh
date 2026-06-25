#!/bin/bash
cd "$(dirname "$0")"
WA_TOKEN=$(python3 -c "import json; print(json.load(open('../credentials/meta_tokens.json'))['wa_system_user_token'])")
railway variables set WA_TOKEN="$WA_TOKEN"
echo "WA_TOKEN configurado ✅"

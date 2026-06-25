#!/bin/bash
cd "$(dirname "$0")"
exec /usr/bin/python3 webhook_server.py >> /tmp/ghh_webhook.log 2>&1

#!/bin/bash

# Simple script to watch Open WebUI logs in real-time
# Usage: ./watch_openwebui_logs.sh

echo "Watching Open WebUI logs (Ctrl+C to stop)..."
echo ""

docker logs -f open-webui 2>&1


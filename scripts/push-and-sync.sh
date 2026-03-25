#!/usr/bin/env bash
# Push to GitHub and sync the Coolify server
# Usage: bash scripts/push-and-sync.sh
set -euo pipefail

git push

# Pull on Coolify server (background, non-blocking)
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@103.249.238.17 \
  "cd /opt/agend-ops && git pull --ff-only" &

echo "Pushed + server sync triggered"

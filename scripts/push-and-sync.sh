#!/usr/bin/env bash
# Push to GitHub and sync the Coolify server
# Usage: bash scripts/push-and-sync.sh
set -euo pipefail

git push

# Pull on Coolify server (background, non-blocking)
# Reset untracked queue files first — dashboard creates actions.jsonl on the server,
# which conflicts with the tracked version from git push. Safe to discard since
# we already pulled the queue entries before processing.
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@103.249.238.17 \
  "cd /opt/agend-ops && git checkout -- data/queue/ 2>/dev/null; git clean -f data/queue/ 2>/dev/null; git pull --ff-only" &

echo "Pushed + server sync triggered"

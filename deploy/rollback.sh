#!/usr/bin/env bash
set -euo pipefail

unit=${1:-gamota-research-mcp.service}
printf 'Stopping and disabling %s; database is left untouched.\n' "$unit"
sudo systemctl disable --now "$unit"

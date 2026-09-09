#!/usr/bin/env bash
set -euo pipefail

IEPP_RESOURCE_GROUP="${IEPP_RESOURCE_GROUP:-iepp-l2-experiment}"

az group show --name "$IEPP_RESOURCE_GROUP" --query '{name:name,location:location,tags:tags}' --output json
read -r -p "Type the exact resource-group name to delete every resource above: " IEPP_DELETE_CONFIRM
if [[ "$IEPP_DELETE_CONFIRM" != "$IEPP_RESOURCE_GROUP" ]]; then
  echo "Deletion cancelled."
  exit 2
fi
az group delete --name "$IEPP_RESOURCE_GROUP" --yes --no-wait
echo "Deletion requested. Verify with: az group exists --name $IEPP_RESOURCE_GROUP"

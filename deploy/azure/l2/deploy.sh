#!/usr/bin/env bash
set -euo pipefail

: "${IEPP_SSH_PUBLIC_KEY:?Set IEPP_SSH_PUBLIC_KEY to an OpenSSH public key}"
: "${IEPP_ADMIN_SOURCE_CIDR:?Set IEPP_ADMIN_SOURCE_CIDR, normally your public IPv4/32}"

IEPP_LOCATION="${IEPP_LOCATION:-koreacentral}"
IEPP_RESOURCE_GROUP="${IEPP_RESOURCE_GROUP:-iepp-l2-experiment}"
IEPP_GIT_REF="${IEPP_GIT_REF:-agent/l2-azure-cvm}"
IEPP_DELETE_AFTER_UTC="${IEPP_DELETE_AFTER_UTC:-$(date -u -d '+3 hours' '+%Y-%m-%dT%H:%M:%SZ')}"

az account show --output table
az vm list-skus --location "$IEPP_LOCATION" --size Standard_DC2as_v5 --all \
  --query "[?name=='Standard_DC2as_v5'].{name:name,restrictions:restrictions}" --output table

az group create --name "$IEPP_RESOURCE_GROUP" --location "$IEPP_LOCATION" --output table

az deployment group what-if \
  --resource-group "$IEPP_RESOURCE_GROUP" \
  --template-file "$(dirname "$0")/main.bicep" \
  --parameters \
    adminSshPublicKey="$IEPP_SSH_PUBLIC_KEY" \
    adminSourceCidr="$IEPP_ADMIN_SOURCE_CIDR" \
    ieppGitRef="$IEPP_GIT_REF" \
    deleteAfterUtc="$IEPP_DELETE_AFTER_UTC"

read -r -p "This creates two billable Confidential VMs. Type DEPLOY to continue: " IEPP_CONFIRM
if [[ "$IEPP_CONFIRM" != "DEPLOY" ]]; then
  echo "Deployment cancelled. The empty resource group is not billable."
  exit 2
fi

az deployment group create \
  --resource-group "$IEPP_RESOURCE_GROUP" \
  --template-file "$(dirname "$0")/main.bicep" \
  --parameters \
    adminSshPublicKey="$IEPP_SSH_PUBLIC_KEY" \
    adminSourceCidr="$IEPP_ADMIN_SOURCE_CIDR" \
    ieppGitRef="$IEPP_GIT_REF" \
    deleteAfterUtc="$IEPP_DELETE_AFTER_UTC" \
  --query properties.outputs --output json

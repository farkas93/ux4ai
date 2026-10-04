#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$*"; }
fail() { log "ERROR: $*" >&2; exit 1; }

OVERWRITE=false
if [[ $# -eq 1 && "$1" == "--overwrite" ]]; then
  OVERWRITE=true
elif [[ $# -ne 0 ]]; then
  fail "Usage: ./gitea_helm_release.sh [--overwrite]"
fi
[[ -f .env ]] || fail ".env not found; copy .env.example and set the Gitea registry values."
[[ -f helm/Chart.yaml && -f pyproject.toml ]] || fail "Run this script from the AIPM repository root."
command -v helm >/dev/null || fail "helm is not installed or is not on PATH."
command -v python3 >/dev/null || fail "python3 is required to read pyproject.toml."
git remote get-url origin >/dev/null || fail "Configure origin to point to your GitHub repository."

if [[ -n "$(git status --porcelain)" ]]; then
  fail "Git working tree is not clean. Commit or stash changes before publishing."
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

[[ -n "${DOCKER_REGISTRY:-}" ]] || fail "DOCKER_REGISTRY must be set in .env."
[[ -n "${DOCKER_USERNAME:-}" ]] || fail "DOCKER_USERNAME must be set in .env."

APP_VERSION=$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')
[[ "$APP_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9.]+)?$ ]] || fail "Invalid project version: $APP_VERSION"

REGISTRY="${DOCKER_REGISTRY%/}"
IMAGE_REPOSITORY="${REGISTRY}/${DOCKER_USERNAME}/aipm-toolkit"
HELM_REGISTRY_HOST="$REGISTRY"
if [[ "$REGISTRY" == "docker.io" ]]; then
  HELM_REGISTRY_HOST="registry-1.docker.io"
fi
OCI_NAMESPACE="${HELM_OCI_NAMESPACE:-$DOCKER_USERNAME}"
OCI_REPOSITORY="oci://${HELM_REGISTRY_HOST}/${OCI_NAMESPACE}"
CHART_NAME=$(helm show chart ./helm | awk '/^name:/{print $2}')
[[ -n "$CHART_NAME" ]] || fail "Could not read name from helm/Chart.yaml."
CHART_VERSION="${HELM_CHART_VERSION:-$(date -u '+%y.%m.%d')-helm}"
[[ "$CHART_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+[-+A-Za-z0-9.]+$ ]] || fail "Invalid Helm chart version: $CHART_VERSION"

log "Fetching GitHub release tags from origin"
git fetch --tags origin
if git rev-parse -q --verify "refs/tags/${CHART_VERSION}" >/dev/null; then
  if [[ "$OVERWRITE" == true ]]; then
    git push origin ":refs/tags/${CHART_VERSION}"
    git tag -d "$CHART_VERSION"
  else
    fail "Git tag ${CHART_VERSION} already exists. Use --overwrite to recreate it."
  fi
fi

if [[ -n "${DOCKER_PASSWORD:-}" ]]; then
  printf '%s' "$DOCKER_PASSWORD" | helm registry login "$HELM_REGISTRY_HOST" --username "$DOCKER_USERNAME" --password-stdin
else
  log "DOCKER_PASSWORD is unset; using existing Helm registry credentials."
fi

log "Linting and rendering ${CHART_NAME}"
helm lint ./helm --set image.repository="$IMAGE_REPOSITORY" --set image.tag="$APP_VERSION"
helm template aipm ./helm --set image.repository="$IMAGE_REPOSITORY" --set image.tag="$APP_VERSION" >/dev/null

if helm show chart "${OCI_REPOSITORY}/${CHART_NAME}" --version "$CHART_VERSION" >/dev/null 2>&1; then
  if [[ "$OVERWRITE" != true ]]; then
    fail "Chart ${CHART_NAME}:${CHART_VERSION} already exists. Set HELM_CHART_VERSION or use --overwrite."
  fi
  log "Overwrite requested; registry may reject immutable chart versions."
fi

DESTINATION=".artifacts/helm/${CHART_VERSION}"
mkdir -p "$DESTINATION"
log "Packaging ${CHART_NAME}:${CHART_VERSION} for app ${APP_VERSION}"
helm package ./helm --version "$CHART_VERSION" --app-version "$APP_VERSION" --destination "$DESTINATION"
helm push "${DESTINATION}/${CHART_NAME}-${CHART_VERSION}.tgz" "$OCI_REPOSITORY"
log "Creating annotated Helm release tag for the checked-out commit"
git tag -a "$CHART_VERSION" -m "Helm chart release $CHART_VERSION for AI Product Toolkit $APP_VERSION"
git push origin "refs/tags/${CHART_VERSION}"
log "Published ${OCI_REPOSITORY}/${CHART_NAME}:${CHART_VERSION}"

#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$*"; }
fail() { log "ERROR: $*" >&2; exit 1; }

if [[ $# -ne 0 ]]; then
  fail "Usage: ./gitea_release.sh"
fi
[[ -f .env ]] || fail ".env not found; copy .env.example and set the Gitea registry values."
[[ -f Dockerfile && -f pyproject.toml ]] || fail "Run this script from the AIPM repository root."
command -v docker >/dev/null || fail "docker is not installed or is not on PATH."
command -v python3 >/dev/null || fail "python3 is required to read pyproject.toml."

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
if [[ -n "${DOCKER_PASSWORD:-}" ]]; then
  printf '%s' "$DOCKER_PASSWORD" | docker login "$REGISTRY" --username "$DOCKER_USERNAME" --password-stdin
else
  log "DOCKER_PASSWORD is unset; using existing Docker registry credentials."
fi

if inspect_output=$(docker manifest inspect "${IMAGE_REPOSITORY}:${APP_VERSION}" 2>&1); then
  fail "Image ${IMAGE_REPOSITORY}:${APP_VERSION} already exists. Bump pyproject.toml before publishing."
elif [[ "$inspect_output" == *unauthorized* || "$inspect_output" == *denied* ]]; then
  fail "Could not inspect registry tag. Verify Docker registry credentials: $inspect_output"
fi

log "Building ${IMAGE_REPOSITORY}:${APP_VERSION}"
docker build --pull -t "${IMAGE_REPOSITORY}:${APP_VERSION}" -t "${IMAGE_REPOSITORY}:latest" .
docker push "${IMAGE_REPOSITORY}:${APP_VERSION}"
docker push "${IMAGE_REPOSITORY}:latest"
log "Published ${IMAGE_REPOSITORY}:${APP_VERSION} and :latest"

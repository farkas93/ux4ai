#!/usr/bin/env bash
set -euo pipefail

log() { printf '[%s] %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S UTC')" "$*"; }
fail() { log "ERROR: $*" >&2; exit 1; }

OVERWRITE=false
if [[ $# -eq 1 && "$1" == "--overwrite" ]]; then
  OVERWRITE=true
elif [[ $# -ne 0 ]]; then
  fail "Usage: ./gitea_release.sh [--overwrite]"
fi
[[ -f .env ]] || fail ".env not found; copy .env.example and set the Gitea registry values."
[[ -f Dockerfile && -f pyproject.toml ]] || fail "Run this script from the AIPM repository root."
command -v docker >/dev/null || fail "docker is not installed or is not on PATH."
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

log "Fetching GitHub release tags from origin"
git fetch --tags origin
if git rev-parse -q --verify "refs/tags/${APP_VERSION}" >/dev/null; then
  if [[ "$OVERWRITE" == true ]]; then
    git push origin ":refs/tags/${APP_VERSION}"
    git tag -d "$APP_VERSION"
  else
    fail "Git tag ${APP_VERSION} already exists. Use --overwrite to recreate it."
  fi
fi

REGISTRY="${DOCKER_REGISTRY%/}"
IMAGE_REPOSITORY="${REGISTRY}/${DOCKER_USERNAME}/aipm-toolkit"
if [[ -n "${DOCKER_PASSWORD:-}" ]]; then
  printf '%s' "$DOCKER_PASSWORD" | docker login "$REGISTRY" --username "$DOCKER_USERNAME" --password-stdin
else
  log "DOCKER_PASSWORD is unset; using existing Docker registry credentials."
fi

if inspect_output=$(docker manifest inspect "${IMAGE_REPOSITORY}:${APP_VERSION}" 2>&1); then
  if [[ "$OVERWRITE" != true ]]; then
    fail "Image ${IMAGE_REPOSITORY}:${APP_VERSION} already exists. Bump pyproject.toml or use --overwrite."
  fi
  log "Overwrite requested; registry may reject immutable image versions."
elif [[ "$inspect_output" == *unauthorized* || "$inspect_output" == *denied* ]]; then
  fail "Could not inspect registry tag. Verify Docker registry credentials: $inspect_output"
fi

log "Building ${IMAGE_REPOSITORY}:${APP_VERSION}"
docker build --pull -t "${IMAGE_REPOSITORY}:${APP_VERSION}" -t "${IMAGE_REPOSITORY}:latest" .
docker push "${IMAGE_REPOSITORY}:${APP_VERSION}"
docker push "${IMAGE_REPOSITORY}:latest"
log "Creating annotated release tag for the checked-out commit"
git tag -a "$APP_VERSION" -m "Release $APP_VERSION (Gitea image, GitHub source)"
git push origin "refs/tags/${APP_VERSION}"
log "Published ${IMAGE_REPOSITORY}:${APP_VERSION} and :latest"

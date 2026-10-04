# Build and publish AIPM to Gitea

These helpers mirror the `gitea_release.sh` and `gitea_helm_release.sh` workflow used by `chat-app` on `private-main`. They publish the AIPM image and Helm chart to a Gitea-compatible OCI/container registry.

## Configure once

Copy `.env.example` to `.env` and set:

- `DOCKER_REGISTRY`: registry host, optionally with port, e.g. `gitea.example.org` or `gitea.example.org:3000`.
- `DOCKER_USERNAME`: Gitea package owner.
- `HELM_OCI_NAMESPACE`: optional OCI namespace; defaults to `DOCKER_USERNAME`.
- `DOCKER_PASSWORD`: optional Gitea password/access token with package write permission; omit it if Docker and Helm are already logged in.

The helpers source `.env` as a shell file, so only use a trusted file. `.env` is git-ignored. Alternatively, run `docker login <registry>` and `helm registry login <registry>` before invoking a helper.

## Publish the application image

```bash
./gitea_release.sh
```

This reads the semantic application version from `pyproject.toml`, builds the single AIPM Dockerfile, and pushes both `aipm-toolkit:<version>` and `aipm-toolkit:latest` to the configured registry. PostgreSQL is not included in the app image.

## Package and publish the Helm chart

```bash
./gitea_helm_release.sh
```

This lints and renders `./helm`, packages it with `appVersion` from `pyproject.toml` and a UTC `YY.MM.DD-helm` chart version, then pushes the OCI chart. If a chart version already exists, set a new `HELM_CHART_VERSION` explicitly; registries commonly make published OCI versions immutable.

Both helpers fetch tags from `origin` and reject duplicate Git tags before publishing. After a successful artifact publish, they create an annotated tag on the checked-out commit and push that tag to `origin` (your GitHub repository). Image tags use the `pyproject.toml` version; Helm tags use the chart version, normally `YY.MM.DD-helm`. They do not switch branches or push your branch. Ensure the checked-out commit is the source you intend to release and is available on GitHub.

As in `chat-app`, `--overwrite` explicitly deletes an existing release tag on `origin` and locally before rebuilding/repackaging and retagging. It also permits an artifact overwrite attempt; your registry may reject immutable versions. A failed publish or tag push can leave an incomplete release, so inspect both the registry and GitHub before retrying.

```bash
./gitea_release.sh --overwrite
./gitea_helm_release.sh --overwrite
```

Install a published chart with the matching image repository and version, and a pre-created `aipm-secrets` Secret as documented in [Kubernetes deployment](KUBERNETES.md).

For example, after authenticating to the registry, install the chart version printed by `gitea_helm_release.sh`:

```bash
helm registry login "$DOCKER_REGISTRY" -u "$DOCKER_USERNAME"
helm upgrade --install aipm "oci://$DOCKER_REGISTRY/${HELM_OCI_NAMESPACE:-$DOCKER_USERNAME}/aipm-toolkit" \
  --version '<YY.MM.DD-helm>' \
  --set image.repository="$DOCKER_REGISTRY/$DOCKER_USERNAME/aipm-toolkit" \
  --set image.tag='<pyproject-version>'
```

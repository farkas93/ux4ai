# Kubernetes (LAN-first workshop)

The `k8s/` manifests provide a single-replica workshop deployment. The app is reachable from the LAN through a permanent NodePort. An instructor can optionally open a temporary, authenticated Gradio share link; closing that link does not alter LAN access. The app does not restart when the link is toggled. A pod restart closes the link, and the app returns to LAN-only mode.

## Build and prepare secrets

Build and push the image to a registry the cluster can pull from, then replace the example image in `k8s/app-deployment.yaml` and `k8s/migration-job.yaml`:

```bash
docker build -t registry.example.org/aipm-toolkit:workshop .
docker push registry.example.org/aipm-toolkit:workshop
```

Create the Secret out-of-band; never commit it. URL-encode reserved characters in the database password if necessary:

```bash
kubectl create secret generic aipm-secrets \
  --from-literal=POSTGRES_PASSWORD='<strong-db-password>' \
  --from-literal=AIPM_DATABASE_URL='postgresql+psycopg://aipm:<url-encoded-db-password>@aipm-postgres:5432/aipm' \
  --from-literal=AIPM_INSTRUCTOR_USERNAME='instructor' \
  --from-literal=AIPM_INSTRUCTOR_PASSWORD='<strong-instructor-password>'
```

For a managed PostgreSQL server, use its private hostname in `AIPM_DATABASE_URL` and omit the bundled `k8s/postgres.yaml` from the install. Protect the Secret with the cluster's normal secret encryption and access controls.

## Install or upgrade

The migration Job is deliberately separate from Kustomize so it completes before the app receives traffic. The app's `/readyz` remains unready until the database schema matches the image.

```bash
kubectl apply -f k8s/configmap.yaml -f k8s/postgres.yaml
kubectl rollout status statefulset/aipm-postgres --timeout=180s
kubectl delete job aipm-migrate --ignore-not-found
kubectl apply -f k8s/migration-job.yaml
kubectl wait --for=condition=complete job/aipm-migrate --timeout=300s
kubectl apply -k k8s/
kubectl rollout status deployment/aipm-app --timeout=180s
```

The migration Job also creates the initial instructor account if it does not exist; it will not overwrite an existing instructor password. On an upgrade, use the new image in the migration Job, rerun it, then roll out the app image. The bundled PostgreSQL StatefulSet requests an 8 GiB PVC; confirm the cluster has a default StorageClass and configure backups before a workshop.

## LAN access and optional public link

Open `http://<node-ip>:30786/auth/login` from the LAN. **Kubernetes NodePort does not restrict clients to your LAN.** Configure the node firewall and any upstream firewall/router to allow TCP `30786` only from your LAN CIDR. The provided LAN manifest uses HTTP and `AIPM_COOKIE_SECURE=false` so session cookies work on the NodePort. Use a trusted HTTPS terminator and set `AIPM_COOKIE_SECURE=true` if the LAN endpoint is served over HTTPS.

In the instructor area:

- **Open public link** starts the Gradio tunnel and displays its temporary `gradio.live` URL.
- **Close public link** stops the tunnel. The LAN NodePort remains available.
- Public visitors still reach the normal sign-in page; the tunnel does not bypass team/instructor authentication.
- The public mode is process-local and defaults closed after restart. The Deployment is intentionally single-replica so tunnel status is unambiguous.

Opening the public link requires outbound internet access from the app pod to Gradio's share API, the FRP endpoint advertised by that API, and (on first use) Gradio's FRPC binary CDN. If egress is blocked, LAN mode continues to work and the instructor panel reports that the public link could not be opened. Avoid enabling `GRADIO_SHARE=true` at process launch; the instructor controls the tunnel at runtime.

The tunnel manager uses Gradio's version-pinned FRP client integration. Re-test open/close and authentication whenever the pinned Gradio version changes. The link is temporary, not a stable course hostname.

The app mounts writable temporary storage at `/app/.gradio`: Gradio 5.44.1 saves
its share-server TLS certificate there. Keep this mount when using a read-only
root filesystem. The certificate and tunnel cache are regenerated after pod
replacement. If opening a link fails, inspect the `aipm` container logs: the
chained exception distinguishes certificate permissions from DNS, TLS, and API
errors. The proxy should forward `/manifest.json` to the app as well as `/app/`
and `/auth/`; FastAPI serves the root manifest referenced by Gradio's page.

`/healthz` checks process liveness. `/readyz` checks PostgreSQL connectivity and that Alembic is at the current image's migration head. The standalone app container does not need Kubernetes API credentials; the instructor panel only starts or stops its own Gradio tunnel.

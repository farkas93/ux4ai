# Classroom responsiveness: Helm and public Gradio access

Version 0.2.12 targets a class of 20 students working in separate projects on
PostgreSQL. The source-level concurrency tests do not establish latency through
your network or the public Gradio relay; rehearse on the deployed public URL.

## Runtime changes

- Authentication and readiness database work run in worker threads rather than
  blocking the async event loop. Password hashing/verification has four worker
  slots, including account provisioning and the standalone development login.
- Session expiry, revocation and account status are checked on every request.
  Activity timestamps are updated at most once per minute, with a conditional
  database update to handle simultaneous checks.
- Eight browser callback pipelines can run concurrently. The entire
  preprocess/callback/postprocess pipeline stays sequential within each browser,
  so later callbacks see earlier saves' updated `gr.State` values. The queue skips
  callbacks from a busy browser rather than letting them consume other students'
  worker slots. Direct API calls use the same per-browser serialization.
- The two-second Value Hypothesis autosave timer starts for dirty edits, stops
  after a successful save, and pauses while a project switch is pending. Failed
  saves remain dirty. Edits newer than a submitted save payload remain pending.

The scheduling adapter is specific to pinned Gradio 5.44.1. It does not support
batched callbacks or streamed generators; the workspace uses neither. Run the
queue and project-switch tests before changing that version or adding streaming.

## Helm settings

```yaml
app:
  uiConcurrencyLimit: 8
  passwordConcurrencyLimit: 4
  sessionTouchIntervalSeconds: 60
resources:
  requests:
    cpu: "2"
    memory: 1Gi
  limits:
    memory: 2Gi
```

The chart uses these defaults, and exposes them as `AIPM_UI_CONCURRENCY_LIMIT`,
`AIPM_PASSWORD_CONCURRENCY_LIMIT`, and `AIPM_SESSION_TOUCH_INTERVAL_SECONDS`.
Setting `uiConcurrencyLimit: 1` provides a serialized fallback on the new image.
A ConfigMap checksum triggers a pod replacement when runtime settings change.
Keep `replicaCount: 1` and one Uvicorn process: Gradio state and the public tunnel
belong to that process.

## Upgrade and preserve a rollback point

Use a new immutable image tag containing this patch, such as `0.2.12`, published
through your normal image-delivery process. Set the actual release and namespace:

```bash
RELEASE=aipm
NAMESPACE=default
IMAGE_TAG=0.2.12
helm history "$RELEASE" --namespace "$NAMESPACE"
helm get values "$RELEASE" --namespace "$NAMESPACE"
```

Record the last successful revision from `helm history`. Upgrade using the new
chart and retain the release's existing image repository, database, secrets and
network settings. On Helm 3.14 or later, `--reset-then-reuse-values` merges the new
chart defaults with your existing overrides; explicit settings below ensure an
older resources override does not retain the 1 GiB cap.

```bash
helm upgrade --install "$RELEASE" ./helm --namespace "$NAMESPACE" \
  --reset-then-reuse-values \
  --set-string image.tag="$IMAGE_TAG" \
  --set app.uiConcurrencyLimit=8 \
  --set app.passwordConcurrencyLimit=4 \
  --set app.sessionTouchIntervalSeconds=60 \
  --set-string resources.requests.cpu=2 \
  --set-string resources.requests.memory=1Gi \
  --set-string resources.limits.memory=2Gi \
  --wait --atomic --timeout 10m
kubectl get pods --namespace "$NAMESPACE" \
  --selector "app.kubernetes.io/instance=$RELEASE"
kubectl top pods --namespace "$NAMESPACE" \
  --selector "app.kubernetes.io/instance=$RELEASE" --containers
```

For a published OCI chart, replace `./helm` with its OCI URL and add that chart's
new `--version`. For older Helm, explicitly supply your existing values file
with `--reset-values -f your-values.yaml` instead of `--reset-then-reuse-values`.

Sign in through the NodePort, open the public link in the instructor panel, and
test that new URL. Upgrade replaces the pod and closes its previous share link;
the same applies to rollback. Database schema and stored project formats are
unchanged by this patch, so the preceding application image can read the data.

To roll back to the revision you recorded:

```bash
helm rollback "$RELEASE" <previous-successful-revision> \
  --namespace "$NAMESPACE" --wait --timeout 10m
```

Wait for readiness, open a new public link, and redistribute it. Browser-local
drafts and Gradio state are reset by pod replacement; saved PostgreSQL records
remain available.

## Public-link rehearsal

Use 20 separate authenticated browser sessions and disposable rehearsal projects.
Use the exact public Gradio URL students will receive, rather than port-forwarding
or testing `/healthz` alone.

1. Log all 20 sessions in together and let their workspaces finish loading.
2. Create or select one project per session. Type for several minutes; check
   autosave completes. Leave all sessions idle and confirm their setup timers
   stop producing `/queue/join` traffic.
3. While an autosave is in flight, edit again and switch projects. Exercise
   **Save & Switch**, **Discard & Switch**, and **Cancel**. Verify content stays
   associated with the correct project.
4. Save assessments, add backlog entries, set priority, and switch between
   projects. Reload every session and verify the last edits persisted.
5. Prepare downloads in all sessions together and open the PDFs.
6. Watch app CPU/memory, restart counts, errors and disconnects throughout. Check
   resources on the app container, not only the node's available memory.

Proposed workshop targets are no lost saves, no restarts/disconnects, most saves
within two seconds, and initial workspace loads within ten seconds. These are
acceptance targets, not measured deployment results. Tune concurrency downward
if memory or PostgreSQL contention grows; keep login/export bursts staggered if
the relay or network remains the bottleneck.

## Local regression checks

```bash
uv run --frozen --extra test pytest \
  tests/test_auth.py tests/test_web.py tests/test_ui_concurrency.py \
  tests/test_autosave.py tests/test_project_switching.py \
  tests/test_gradio_project_loading.py tests/test_workflow_integration.py
helm lint ./helm
helm template aipm ./helm
```

The queue test submits two callbacks for each of 20 sessions before any finish,
checks the eight-session concurrency bound, and verifies callbacks read the
state produced by their predecessors. It also verifies that one busy browser
does not starve another, and that failed direct calls release session gates.

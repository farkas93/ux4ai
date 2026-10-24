# Desktop and hosted web editions

Both editions use the existing Gradio UI, FastAPI callbacks, SQLAlchemy models,
and learning-report code. `aipm_toolkit.application.create_application` is the
shared composition point. The hosted entry remains `aipm_toolkit.server:app`.

## Desktop behavior

The installed app opens directly into a personal workspace. An internal local
team identity retains the current project ownership and revision checks. A
single-use launch capability sets an HttpOnly cookie; old launch sessions are
invalidated on restart. The local server binds a reserved socket on
`127.0.0.1:0`, rather than a LAN address or a hard-coded port. Host/origin checks
and private instance-control capabilities protect the loopback endpoints.

The hosted web edition retains its normal authentication and optional public
Gradio relay. Desktop mode removes those public controls and disables tunnel
creation at service level. Gradio analytics, Hub telemetry, SSR and startup
network calls are disabled before importing the UI. Opening external source
links is a user action; desktop startup and normal workshop work need no cloud
service or model download.

### Local data locations

| System | Profile root |
| --- | --- |
| Windows | `%LOCALAPPDATA%\AIProductToolkit` |
| macOS | `~/Library/Application Support/AIProductToolkit` |
| Linux | `$XDG_DATA_HOME/AIProductToolkit`, normally `~/.local/share/AIProductToolkit` |

The version-independent directory contains:

```text
workspace.sqlite3      all persistent application records
preferences.json       language and last selected project
imports/               retained reference-import source files
exports/               generated immutable download bundles
backups/               SQLite backup taken before a schema upgrade
cache/                 browser, upload, Gradio and temporary data
logs/                  bounded application logs
workspace.lock         OS-backed single-instance lock
instance.json          private live-instance metadata; removed on clean exit
```

SQLite uses foreign-key enforcement, WAL journaling and a busy timeout. The
launcher owns the profile lock during migration, UI use and shutdown. A second
launch focuses the existing window. `--data-dir <directory>` creates a separate
profile. Do not copy a live WAL database by copying only `workspace.sqlite3`;
close the app before copying a profile, or use SQLite's backup mechanism.
Sharing JSON/PDF/Markdown exports are learning reports, not complete database
backups. Uninstalling application binaries does not delete the profile.

The bundled product reference catalog is imported and published idempotently on
startup, so Compare to Product works offline. Installed/frozen resources include
the migrations, catalog, translations, Gradio frontend, and licensed DejaVu
regular/bold PDF fonts; resources do not depend on the launch working directory.
Linux also gets an application-local Fontconfig configuration with the bundled
fallback fonts and a cache under the profile, avoiding empty font configurations
on minimal systems.

### Saving and closing

Prepare downloads saves current editor values first and clears download links
if a save fails. It flushes visible priority slider pairs even if an earlier
asynchronous save cleared their dirty flag. Risk/evidence input events are
coalesced to the last complete pair, and all three export formats use the same
immutable document. Prepared files are separate per generation.

Closing the native window requests the same aggregate save operation and waits
for an acknowledgment before stopping the server. A save failure keeps the
window open and offers Cancel or explicit discard. Empty mount-time control
events do not count as unsaved work in a blank workspace. Force Quit/process
termination cannot preserve browser-local edits that have not been submitted;
already committed SQLite records remain available.

Report download links use a native Save dialog. Only generated files under the
profile's exports/cache locations are accepted by the desktop download endpoint.

## Development

Use the project manifest and lockfile; `requirements.txt` belongs to legacy scripts.

```bash
uv sync --frozen --extra desktop --extra packaging --extra test
uv run --frozen --extra desktop ai-product-toolkit
uv run --frozen --extra desktop ai-product-toolkit --data-dir /path/to/test-profile
```

The `server` extra supplies the PostgreSQL driver. Containers install it explicitly:

```bash
uv sync --frozen --extra server --extra test
uv run --frozen --extra server uvicorn aipm_toolkit.server:app --host 127.0.0.1 --port 7860
```

`--headless` is an automated-test runtime mode. It writes a launch URL and private
capability into the profile's live instance metadata; it is not a public server.
`--smoke-test` requires an explicit disposable profile, seeds a qualification
project, opens the actual native window, visits all six workflow pages, verifies
both Plotly graphs render, performs save-before-close, then exits.

## Native packaging

Build on a matching OS **and CPU architecture**, using the desktop and packaging
extras. PyInstaller includes Python and extension modules; one-folder packaging
is used to keep startup/debugging predictable and resources immutable.

```bash
uv sync --frozen --extra desktop --extra packaging --extra test
uv run --frozen --extra desktop --extra packaging python packaging/build_desktop.py --expected-arch x86_64
# On a native ARM64 host, use --expected-arch arm64.
```

Outputs are in `.artifacts/desktop-dist` and `.artifacts/releases`. The Windows
build needs Inno Setup (CI installs a checksum-pinned build tool). It downloads
an architecture-matched, fixed WebView2
runtime from the pinned Microsoft URLs and verifies the archive SHA-256 before
bundling it. It does not use an end-user bootstrap downloader or .NET/pythonnet.
macOS and Linux use bundled Qt WebEngine, with profile/cache paths inside app-data.

PyInstaller data includes Gradio's dynamically loaded assets, dependency version
files and Python sources. A frozen-only import hook suppresses Gradio's
developer `.pyi` generation; the ordinary installed web application is unaffected.
PostgreSQL drivers, test frameworks and alternative Qt bindings are excluded
from the desktop bundle.

### Six-target matrix

| Target | Native runner | Artifact | Baseline |
| --- | --- | --- | --- |
| Windows x64 | `windows-2022` | portable ZIP + per-user installer | modern Windows x64 |
| Windows ARM64 | `windows-11-arm` | portable ZIP + ARM64 installer | Windows 11 ARM64 |
| macOS Intel | `macos-15-intel` | `.app` in DMG | macOS 14+ |
| macOS Apple Silicon | `macos-15` | `.app` in DMG | macOS 14+ |
| Linux x64 | `ubuntu-22.04` | application TAR.GZ | glibc 2.34+ and desktop graphics stack |
| Linux ARM64 | `ubuntu-24.04-arm` | application TAR.GZ | glibc 2.39+ and desktop graphics stack |

Linux graphics/display drivers are OS components. Xvfb is used only for build
qualification; it is not an end-user requirement. The exact artifact baseline
must match its build environment (e.g. a development bundle built on Debian 12
has that environment's glibc baseline).

Linux build hosts need the complete Qt X11 and WebEngine runtime dependencies,
including the XCB cursor, ICCCM, image, keysyms and render utilities, and Opus.
The workflow installs these before dependency analysis so PyInstaller can collect
the redistributable libraries. Packaging checks the X11 plugin and WebEngine
library with `ldd` and reports missing dependencies before creating a bundle.

Native dependency gates:

- Pandas 2.3.3 has no published Windows ARM64 wheel. The ARM runner initializes
  the ARM64 MSVC environment and builds the locked source dependency. Windows
  steps use PowerShell to preserve the MSVC linker precedence; Git Bash's GNU
  `link.exe` is incompatible with that build. A failed native build prevents that
  target/release from publishing.
- macOS Intel may need a native source build of Argon2 bindings. Xcode's compiler
  provides the build toolchain; users do not compile packages at install time.
- The workflow uses managed CPython 3.12.15, including a native Windows ARM64
  runtime, and asserts the frozen executable's PE/ELF/Mach-O CPU header.

## CI qualification and publishing

`.github/workflows/desktop.yml` creates six native development artifacts for
relevant branch/PR changes. Each target runs the shared web/source regressions,
builds its native bundle, opens the real frozen window, and repeats the
create/save/export/restart tests against the frozen executable. Checksums accompany
the distribution files. Success on Linux does not establish another target's
qualification; each corresponding native job must pass.

For local Linux GUI qualification, provide the supported graphics libraries and
a display (or Xvfb). For example:

```bash
QT_QUICK_BACKEND=software QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu \
  xvfb-run -a uv run --frozen --extra desktop --extra packaging --extra test \
  python packaging/smoke_desktop.py --expected-arch x86_64 --profile /tmp/aipm-smoke
```

Publishing is an explicit workflow dispatch with `publish: true`, restricted to
the default branch and the `desktop-release` protected environment. Configure
that environment to permit the default branch only and supply:

- Windows: `WINDOWS_CERTIFICATE_PFX` (base64) and `WINDOWS_CERTIFICATE_PASSWORD`.
- macOS: `MACOS_CERTIFICATE_P12` (base64), `MACOS_CERTIFICATE_PASSWORD`,
  `MACOS_KEYCHAIN_PASSWORD`, `MACOS_SIGNING_IDENTITY`, `APPLE_ID`,
  `APPLE_TEAM_ID`, and `APPLE_APP_PASSWORD`.

Production builds sign Windows application/installer files and sign/notarize/
staple macOS DMGs. Missing signing inputs cause production publishing to fail.
Development artifacts are not publisher-signed releases. The protected CI job
creates the immutable `v<application-version>` release only after all six jobs
pass; agents do not create release tags. Use a fresh patch version for a new
release rather than overwriting an existing one.

"""Composition shared by the hosted server and the local desktop launcher."""


def create_application(desktop_runtime=None):
    # Delayed imports let desktop bootstrap set its profile and offline paths
    # before SQLAlchemy engines or Gradio's caches are initialized.
    import gradio as gr

    from .i18n import SUPPORTED_LANGUAGES, load_catalog
    from .ui.shell import build_app
    from .web import create_auth_app

    for language in SUPPORTED_LANGUAGES:
        load_catalog(language)
    blocks = build_app(desktop_runtime=desktop_runtime)
    api = create_auth_app(desktop_runtime=desktop_runtime)
    app = gr.mount_gradio_app(
        api, blocks, path="/app", ssr_mode=False if desktop_runtime else None,
        mcp_server=False if desktop_runtime else None,
        max_file_size="20mb",
    )
    app.state.workspace = blocks
    return app

from fastapi import FastAPI
from gradio import mount_gradio_app

from .app import app as gradio_app
from .web import create_auth_app

app: FastAPI = create_auth_app()
app = mount_gradio_app(app, gradio_app, path="/app")

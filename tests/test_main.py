"""App wiring: lifespan constructs services; routes resolve them via Depends."""
from fastapi.testclient import TestClient

from app.img2img import ComfyUI
from app.main import app, get_comfyui, get_ollama
from app.prompt_enhancer import Ollama


def test_lifespan_constructs_services():
    with TestClient(app):
        assert isinstance(app.state.ollama, Ollama)
        assert isinstance(app.state.comfyui, ComfyUI)
        # dependency providers hand back the same singleton instances
        assert get_ollama() is app.state.ollama
        assert get_comfyui() is app.state.comfyui


def test_health_responds():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

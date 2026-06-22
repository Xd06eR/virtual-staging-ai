"""Error handling for the Ollama wrapper (Q2: preserve the exception chain)."""
import ollama
import pytest

from app.prompt_enhancer import Ollama


def test_enhance_prompt_wraps_and_chains(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("ollama down")

    monkeypatch.setattr(ollama, "generate", boom)
    with pytest.raises(RuntimeError) as excinfo:
        Ollama().enhance_prompt("a cozy room")
    # original cause preserved for debugging
    assert isinstance(excinfo.value.__cause__, ConnectionError)

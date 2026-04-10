import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "python"))

from embeddings import _clear_model_cache, _get_cached_model


def test_get_cached_model_reuses_loaded_model():
    calls = []

    def loader(model_path: str):
        calls.append(model_path)
        return {"model_path": model_path}

    _clear_model_cache()

    first = _get_cached_model("model-a", loader=loader)
    second = _get_cached_model("model-a", loader=loader)

    assert first is second
    assert calls == ["model-a"]


def test_get_cached_model_is_scoped_by_model_path():
    calls = []

    def loader(model_path: str):
        calls.append(model_path)
        return {"model_path": model_path}

    _clear_model_cache()

    first = _get_cached_model("model-a", loader=loader)
    second = _get_cached_model("model-b", loader=loader)

    assert first is not second
    assert calls == ["model-a", "model-b"]

import sys
import time
import numpy as np
from typing import Callable
from model_manager import TIER0_MODEL, TIER1_MODEL, ensure_model
from protocol import format_progress

_MODEL_CACHE = {}


def generate_embeddings(params: dict, msg_id: str) -> dict:
    """Generate embeddings for a list of review texts."""
    texts = params.get("texts", [])
    tier = params.get("tier", 0)

    if not texts:
        return {"embeddings": [], "model": "none"}

    model_name = TIER0_MODEL if tier == 0 else TIER1_MODEL

    def on_progress(percent, message, stage=None, elapsed_ms=None):
        sys.stdout.write(format_progress(msg_id, percent, message, stage=stage, elapsed_ms=elapsed_ms) + "\n")
        sys.stdout.flush()

    on_progress(2, f"Loading model {model_name}...", stage="embedding", elapsed_ms=0)

    model_path = ensure_model(model_name)

    on_progress(4, "Initializing ML engine...", stage="embedding", elapsed_ms=0)
    embeddings = _embed_with_sentence_transformers(model_path, texts, on_progress)

    on_progress(100, "Embeddings complete", stage="embedding", elapsed_ms=0)
    return {
        "embeddings": embeddings.tolist(),
        "model": model_name,
        "dim": embeddings.shape[1]
    }


def _clear_model_cache() -> None:
    _MODEL_CACHE.clear()


def _load_sentence_transformer(model_path: str):
    import logging
    import os
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["TQDM_DISABLE"] = "1"
    # Suppress noisy library output (tqdm progress bars, safetensors LOAD REPORT)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("safetensors").setLevel(logging.WARNING)
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_path)


def _get_cached_model(model_path: str, loader: Callable[[str], object] | None = None):
    if model_path not in _MODEL_CACHE:
      load_model = loader or _load_sentence_transformer
      _MODEL_CACHE[model_path] = load_model(model_path)
    return _MODEL_CACHE[model_path]


def _embed_with_sentence_transformers(model_path: str, texts: list[str], on_progress: Callable) -> np.ndarray:
    cached = model_path in _MODEL_CACHE
    on_progress(
        6,
        "Reusing embedding model from memory..." if cached else "Loading embedding model into memory...",
        stage="embedding",
        elapsed_ms=0
    )
    model = _get_cached_model(model_path)
    batch_size = 64
    all_embeddings = []
    t_start = time.time()

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        emb = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
        all_embeddings.append(emb)
        processed = min(i + len(batch), len(texts))
        percent = min(95, int(10 + 85 * processed / len(texts)))
        elapsed_ms = int((time.time() - t_start) * 1000)
        on_progress(percent, f"Embedded {processed}/{len(texts)} reviews", stage="embedding", elapsed_ms=elapsed_ms)

    return np.vstack(all_embeddings)

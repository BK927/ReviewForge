import sys
import time
import numpy as np
from typing import Callable
from model_manager import TIER0_MODEL, TIER1_MODEL, ensure_model
from protocol import format_progress


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

    on_progress(5, f"Loading model {model_name}...", stage="embedding", elapsed_ms=0)

    model_path = ensure_model(model_name)
    embeddings = _embed_with_sentence_transformers(model_path, texts, on_progress)

    on_progress(100, "Embeddings complete", stage="embedding", elapsed_ms=0)
    return {
        "embeddings": embeddings.tolist(),
        "model": model_name,
        "dim": embeddings.shape[1]
    }


def _embed_with_sentence_transformers(model_path: str, texts: list[str], on_progress: Callable) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_path)
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

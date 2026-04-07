import sys
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

    def on_progress(percent, message):
        sys.stdout.write(format_progress(msg_id, percent, message) + "\n")
        sys.stdout.flush()

    on_progress(5, f"Loading model {model_name}...")

    model_path = ensure_model(model_name)
    embeddings = _embed_with_sentence_transformers(model_path, texts, on_progress)

    on_progress(100, "Embeddings complete")
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

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        emb = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
        all_embeddings.append(emb)
        percent = min(95, int(10 + 85 * (i + len(batch)) / len(texts)))
        on_progress(percent, f"Embedded {min(i + len(batch), len(texts))}/{len(texts)} reviews")

    return np.vstack(all_embeddings)

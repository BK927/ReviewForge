import os
from pathlib import Path


def get_models_dir() -> Path:
    base = Path(os.environ.get("REVIEWFORGE_MODELS_DIR", str(Path.home() / ".reviewforge" / "models")))
    base.mkdir(parents=True, exist_ok=True)
    return base


TIER0_MODEL = "intfloat/multilingual-e5-small"
TIER1_MODEL = "BAAI/bge-m3"


def ensure_model(model_name: str) -> str:
    """Download model if not cached. Returns local path."""
    from huggingface_hub import snapshot_download

    models_dir = get_models_dir()
    local_dir = models_dir / model_name.replace("/", "--")

    if local_dir.exists() and any(local_dir.iterdir()):
        return str(local_dir)

    snapshot_download(
        repo_id=model_name,
        local_dir=str(local_dir),
        ignore_patterns=["*.msgpack", "*.h5", "*.ot", "flax_*", "tf_*"]
    )
    return str(local_dir)


def get_onnx_path(model_name: str) -> str | None:
    """Find int8 ONNX file if available."""
    model_dir = ensure_model(model_name)
    onnx_dir = Path(model_dir) / "onnx"
    if onnx_dir.exists():
        for f in onnx_dir.glob("*int8*onnx"):
            return str(f)
        for f in onnx_dir.glob("*.onnx"):
            return str(f)

    for f in Path(model_dir).glob("*int8*.onnx"):
        return str(f)
    for f in Path(model_dir).glob("*.onnx"):
        return str(f)

    return None
